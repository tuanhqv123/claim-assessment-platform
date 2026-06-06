"""Pydantic models + validation for a tenant configuration."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


def _default_branding() -> dict:
    return {"company_name": "Insurance Co.", "logo_url": None, "primary_color": None, "secondary_color": None}


class Branding(BaseModel):
    company_name: str = "Insurance Co."
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None


class DocumentRequirements(BaseModel):
    required: List[str] = Field(default_factory=list)
    optional: List[str] = Field(default_factory=list)


class ApprovalTier(BaseModel):
    min: float
    max: Optional[float] = None  # None => unbounded (open-ended top tier)
    role: str


class NotificationRule(BaseModel):
    channels: List[str] = Field(default_factory=list)


def _default_notification_rule() -> NotificationRule:
    return NotificationRule(channels=["email"])


class Notifications(BaseModel):
    claim_submitted: NotificationRule = Field(default_factory=_default_notification_rule)
    approved: NotificationRule = Field(default_factory=_default_notification_rule)
    rejected: NotificationRule = Field(default_factory=_default_notification_rule)
    payment_sent: NotificationRule = Field(default_factory=_default_notification_rule)


class CustomField(BaseModel):
    key: str
    label: str
    type: str = "text"
    required: bool = False


class TenantConfig(BaseModel):
    branding: Branding = Field(default_factory=Branding)
    claim_types: List[str]
    documents: dict[str, DocumentRequirements]
    auto_approval_threshold: float
    approval_tiers: List[ApprovalTier]
    notifications: Notifications = Field(default_factory=Notifications)
    sla: dict[str, int]
    custom_fields: List[CustomField] = Field(default_factory=list)

    @field_validator("auto_approval_threshold")
    @classmethod
    def _threshold_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("auto_approval_threshold must be >= 0")
        return v

    @field_validator("claim_types")
    @classmethod
    def _at_least_one_claim_type(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("at least one claim type must be enabled")
        return v

    @field_validator("sla")
    @classmethod
    def _sla_values_positive(cls, v: dict[str, int]) -> dict[str, int]:
        for key, val in v.items():
            if val <= 0:
                raise ValueError(f"sla['{key}'] must be positive, got {val}")
        return v

    @model_validator(mode="after")
    def _validate_tiers(self) -> "TenantConfig":
        tiers = self.approval_tiers
        if not tiers:
            raise ValueError("approval_tiers must not be empty")
        # Sort by min to evaluate contiguity / sanity deterministically.
        ordered = sorted(tiers, key=lambda t: t.min)
        prev_max: Optional[float] = None
        for i, tier in enumerate(ordered):
            if tier.max is not None and tier.max <= tier.min:
                raise ValueError(
                    f"approval_tier role '{tier.role}': max ({tier.max}) "
                    f"must be greater than min ({tier.min})"
                )
            if i == 0:
                if tier.min != 0:
                    raise ValueError("approval_tiers must start at min == 0")
            else:
                if tier.min != prev_max:
                    raise ValueError(
                        "approval_tiers must be contiguous; gap/overlap between "
                        f"max {prev_max} and next min {tier.min}"
                    )
            if tier.max is None and i != len(ordered) - 1:
                raise ValueError("only the highest approval_tier may be unbounded (max=null)")
            prev_max = tier.max
        if ordered[-1].max is not None:
            raise ValueError("the highest approval_tier must be unbounded (max=null)")
        return self

    @model_validator(mode="after")
    def _validate_auto_tier_alignment(self) -> "TenantConfig":
        # If an "auto"-role tier exists, its upper bound must coincide with the
        # auto_approval_threshold; otherwise an amount in
        # (threshold, auto_tier.max) routes to role "auto" while NOT being
        # auto-approved — a phantom band.
        auto_tiers = [t for t in self.approval_tiers if t.role == "auto"]
        for tier in auto_tiers:
            if tier.max is None:
                raise ValueError(
                    "the 'auto' approval_tier must be bounded (max must not be null)"
                )
            if tier.max != self.auto_approval_threshold:
                raise ValueError(
                    f"auto_approval_threshold ({self.auto_approval_threshold}) must "
                    f"equal the 'auto' approval_tier's max ({tier.max})"
                )
        return self

    @model_validator(mode="after")
    def _validate_sla_coverage(self) -> "TenantConfig":
        # Every enabled claim_type must resolve to an SLA: either sla.default
        # exists, or each enabled type has its own SLA entry. Otherwise the
        # runtime's hard-coded 7-day fallback could silently apply.
        if "default" not in self.sla:
            missing = [ct for ct in self.claim_types if ct not in self.sla]
            if missing:
                raise ValueError(
                    "sla must define a 'default' or an entry for every enabled "
                    f"claim_type; missing SLA for: {missing}"
                )
        return self

    @model_validator(mode="after")
    def _validate_documents_coverage(self) -> "TenantConfig":
        # Every enabled claim_type must have a documents config entry.
        missing = [ct for ct in self.claim_types if ct not in self.documents]
        if missing:
            raise ValueError(
                "documents must define an entry for every enabled claim_type; "
                f"missing documents for: {missing}"
            )
        return self


def validate_config(config: dict) -> tuple[bool, List[str]]:
    """Validate a raw tenant-config dict.

    Returns (ok, errors). On success errors is empty; on failure ok is False and
    errors contains human-readable messages (one per validation problem).
    """
    try:
        TenantConfig.model_validate(config)
        return True, []
    except ValidationError as exc:
        errors: List[str] = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"]) or "<root>"
            errors.append(f"{loc}: {err['msg']}")
        return False, errors
