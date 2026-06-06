"""Config version / rollback model.

A `config_versions` list is an append-only history. Each entry looks like:
    {"version": 1, "config": {...}}

Rollback never mutates history: it appends a NEW version whose config equals
the target version's config.
"""

from __future__ import annotations

import copy
from typing import Optional


def next_version(existing_versions: list[dict]) -> int:
    """Return the next monotonically-increasing version number.

    Empty history => version 1.
    """
    if not existing_versions:
        return 1
    return max(v["version"] for v in existing_versions) + 1


def _find_version(config_versions: list[dict], target_version: int) -> Optional[dict]:
    for entry in config_versions:
        if entry["version"] == target_version:
            return entry
    return None


def rollback(config_versions: list[dict], target_version: int) -> dict:
    """Create a NEW version whose config equals the target version's config.

    Returns the new version dict (does not mutate `config_versions`). Raises
    ValueError if the target version doesn't exist.
    """
    target = _find_version(config_versions, target_version)
    if target is None:
        raise ValueError(f"version {target_version} not found in history")

    return {
        "version": next_version(config_versions),
        "config": copy.deepcopy(target["config"]),
        "rolled_back_from": target_version,
    }
