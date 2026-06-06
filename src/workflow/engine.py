"""Config-driven claims workflow state machine engine.

Nothing about the transition graph is hardcoded here: states, transitions,
preconditions, side effects, authorized roles and the cycle policy all come
from ``config/workflow.json`` (or any dict passed to the constructor). Adding
a new state or transition is therefore a config-only change.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


# --------------------------------------------------------------------------- #
# Errors — all specific, never generic.
# --------------------------------------------------------------------------- #
class WorkflowError(Exception):
    """Base class for all workflow errors."""


class InvalidTransitionError(WorkflowError):
    """Raised when the requested target state is not reachable from current."""


class PreconditionError(WorkflowError):
    """Raised when a named precondition is not satisfied in the context."""


class AuthorizationError(WorkflowError):
    """Raised when the actor's role is not authorized for the transition."""


class CycleLimitError(WorkflowError):
    """Raised when the information-request loop exceeds its allowed cycles."""


# --------------------------------------------------------------------------- #
# Default config location.
# --------------------------------------------------------------------------- #
DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "workflow.json"
)


@dataclass
class _ClaimRecord:
    """Engine-private canonical record for a claim.

    This is the single source of truth for a claim's state, info-request count
    and audit trail. It is never handed out to callers, so history cannot be
    rewritten and state cannot be set externally to bypass the machine.
    """

    id: str
    state: str
    info_request_count: int = 0
    audit: list[dict[str, Any]] = field(default_factory=list)


class Claim:
    """A read-only handle to a claim moving through the workflow.

    All mutable canonical state (``state``, ``info_request_count`` and the
    audit trail) lives inside the engine in a private ``_ClaimRecord``. This
    handle exposes ``state`` / ``info_request_count`` as read-only properties
    that delegate to the engine's record, so callers cannot mutate history or
    force an arbitrary state to bypass the state machine.
    """

    __slots__ = ("_id", "_engine")

    def __init__(self, claim_id: str, engine: "WorkflowEngine") -> None:
        self._id = claim_id
        self._engine = engine

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> str:
        return self._engine._record(self._id).state

    @property
    def info_request_count(self) -> int:
        return self._engine._record(self._id).info_request_count

    def __repr__(self) -> str:
        return f"Claim(id={self._id!r}, state={self.state!r})"


class WorkflowEngine:
    """State machine driven entirely by a JSON/dict config."""

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        config_path: Optional[str | Path] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        if config is None:
            path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
            with open(path, "r", encoding="utf-8") as fh:
                config = json.load(fh)

        self._config = copy.deepcopy(config)
        self.states: list[str] = list(self._config["states"])
        self.initial_state: str = self._config.get(
            "initial_state", self.states[0]
        )
        # Index transitions by (from, to) for O(1) lookup.
        self._transitions: dict[tuple[str, str], dict[str, Any]] = {}
        self._by_source: dict[str, list[dict[str, Any]]] = {}
        for t in self._config["transitions"]:
            key = (t["from"], t["to"])
            self._transitions[key] = t
            self._by_source.setdefault(t["from"], []).append(t)

        self._cycle = self._config.get("cycle")
        # Injectable clock for deterministic timestamps in tests.
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        # Engine-private canonical store keyed by claim id. Callers only ever
        # hold a read-only Claim handle, never this record.
        self._records: dict[str, _ClaimRecord] = {}

    # ------------------------------------------------------------------ #
    # Claim factory.
    # ------------------------------------------------------------------ #
    def new_claim(self, claim_id: str, state: Optional[str] = None) -> Claim:
        self._records[claim_id] = _ClaimRecord(
            id=claim_id, state=state or self.initial_state
        )
        return Claim(claim_id, self)

    def _record(self, claim_id: str) -> _ClaimRecord:
        rec = self._records.get(claim_id)
        if rec is None:
            raise KeyError(f"Unknown claim id: {claim_id}")
        return rec

    # ------------------------------------------------------------------ #
    # Introspection.
    # ------------------------------------------------------------------ #
    def available_transitions(self, state: str) -> list[dict[str, Any]]:
        """Return the transitions reachable from ``state``."""
        out: list[dict[str, Any]] = []
        for t in self._by_source.get(state, []):
            out.append(
                {
                    "to": t["to"],
                    "role": t["role"],
                    "preconditions": list(t.get("preconditions", [])),
                }
            )
        return out

    def _valid_targets(self, state: str) -> list[str]:
        return [t["to"] for t in self._by_source.get(state, [])]

    # ------------------------------------------------------------------ #
    # The transition.
    # ------------------------------------------------------------------ #
    def transition(
        self,
        claim: Claim,
        to_state: str,
        actor_role: str,
        context: Optional[dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
        notes: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> Claim:
        """Attempt to move ``claim`` to ``to_state``.

        Order of checks: validity -> role authorization -> cycle limit ->
        preconditions -> commit. Authorization is checked before preconditions
        so an unauthorized actor always gets an ``AuthorizationError`` and never
        learns which precondition would have failed (no info leak). A blocked
        transition (auth/cycle/precondition failure) runs NO side effects and
        writes NO audit entry.
        """
        context = context or {}
        record = self._record(claim.id)
        from_state = record.state

        # 1) Valid transition?
        transition = self._transitions.get((from_state, to_state))
        if transition is None:
            valid = self._valid_targets(from_state)
            valid_str = ", ".join(valid) if valid else "(none — terminal state)"
            raise InvalidTransitionError(
                f"Invalid transition: cannot go from {from_state} to "
                f"{to_state}. Valid targets: {valid_str}"
            )

        # 2) Role authorization — checked BEFORE preconditions so an
        #    unauthorized actor cannot probe precondition state.
        required_role = transition["role"]
        if actor_role != required_role:
            raise AuthorizationError(
                f"Unauthorized: transition {from_state} -> {to_state} requires "
                f"role '{required_role}' but actor has role '{actor_role}'."
            )

        # 3) Cycle detection — block re-entering assessment after too many
        #    information requests.
        self._check_cycle(record, from_state, to_state)

        # 4) Preconditions.
        for precondition in transition.get("preconditions", []):
            if not self._precondition_met(precondition, context):
                raise PreconditionError(
                    f"Precondition not met for {from_state} -> {to_state}: "
                    f"'{precondition}' is required but not satisfied in context."
                )

        # --- All checks passed: commit. ---
        side_effects = self._run_side_effects(
            transition.get("side_effects", []), record, from_state, to_state
        )

        # Count an information request when the claim enters PENDING_INFO.
        if self._cycle and to_state == self._cycle["count_on_entry_to"]:
            record.info_request_count += 1

        record.state = to_state

        timestamp = (now or self._clock()).isoformat()
        entry = {
            "timestamp": timestamp,
            "from_state": from_state,
            "to_state": to_state,
            "triggered_by": {"id": actor_id, "role": actor_role},
            "reason": reason,
            "notes": notes,
            "side_effects": side_effects,
        }
        record.audit.append(entry)
        return claim

    @staticmethod
    def _precondition_met(precondition: str, context: dict[str, Any]) -> bool:
        """A precondition is met iff the key is present AND truthy.

        A MISSING key fails (the fact was never asserted). A present value is
        evaluated for truthiness, which keeps boolean configs working while
        allowing future non-boolean preconditions to pass on a present, truthy
        value rather than being rejected outright.
        """
        if precondition not in context:
            return False
        return bool(context[precondition])

    # ------------------------------------------------------------------ #
    # Cycle policy.
    # ------------------------------------------------------------------ #
    def _check_cycle(
        self, record: _ClaimRecord, from_state: str, to_state: str
    ) -> None:
        if not self._cycle:
            return
        # Only guard re-entry into the assessment state from the loop's
        # feeder state (the info-request loop), not the first normal entry.
        if to_state != self._cycle["guard_state"]:
            return
        if from_state != self._cycle["loop_from_state"]:
            return
        # info_request_count reflects how many PENDING_INFO requests happened.
        # The loop is allowed up to max_cycles times; the (max+1)th info
        # request, when it tries to return to assessment, is blocked.
        if record.info_request_count > self._cycle["max_cycles"]:
            raise CycleLimitError(self._cycle["error_message"])

    # ------------------------------------------------------------------ #
    # Side effects (mocked as log strings).
    # ------------------------------------------------------------------ #
    def _run_side_effects(
        self,
        names: list[str],
        record: _ClaimRecord,
        from_state: str,
        to_state: str,
    ) -> list[str]:
        logs: list[str] = []
        for name in names:
            logs.append(
                f"[side-effect] {name} executed for claim {record.id} "
                f"({from_state} -> {to_state})"
            )
        return logs

    # ------------------------------------------------------------------ #
    # Immutable audit trail access.
    # ------------------------------------------------------------------ #
    def audit_trail(self, claim: Claim | str) -> list[dict[str, Any]]:
        """Return a deep copy of the full audit history (read-only).

        Accepts either a ``Claim`` instance or a claim id string. The returned
        list is a deep copy of the engine-private trail, so callers cannot
        mutate the append-only history.
        """
        claim_id = claim.id if isinstance(claim, Claim) else claim
        return copy.deepcopy(self._record(claim_id).audit)
