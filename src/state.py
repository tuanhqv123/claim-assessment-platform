# claim-assessment-agent/src/state.py
from __future__ import annotations

import operator
from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# --- Enums ---

class PolicyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LAPSED = "LAPSED"
    GRACE_PERIOD = "GRACE_PERIOD"
    TERMINATED = "TERMINATED"


class ClaimType(str, Enum):
    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"
    DENTAL = "DENTAL"
    MATERNITY = "MATERNITY"


class DocumentStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    MISSING = "MISSING"
    TYPE_MISMATCH = "TYPE_MISMATCH"


class Recommendation(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"


# --- Pydantic Models ---

class SubBenefit(BaseModel):
    name: str
    limit_per_visit: float | None = None
    limit_per_day: float | None = None
    limit_per_event: float | None = None
    limit_per_year: float | None = None
    visits_per_year: int | None = None
    max_days: int | None = None


class Benefit(BaseModel):
    type: ClaimType
    annual_limit: float
    sub_benefits: list[SubBenefit]
    waiting_period_days: int = 0


class Exclusion(BaseModel):
    clause: str
    description: str
    keywords: list[str] = Field(default_factory=list)


class CopayRule(BaseModel):
    percentage: float = 0.0
    max_per_visit: float | None = None


class Deductible(BaseModel):
    annual: float = 0.0
    per_visit: float = 0.0


class PolicyData(BaseModel):
    policy_id: str
    status: PolicyStatus
    effective_date: date
    expiry_date: date
    policyholder_name: str
    policyholder_type: str
    member_ids: list[str]
    benefits: list[Benefit]
    copay: dict[str, CopayRule]
    deductible: Deductible
    waiting_periods: dict[str, int]
    exclusions: list[Exclusion]
    network_hospitals: list[str] = Field(default_factory=list)
    currency: str = "THB"


class ClaimData(BaseModel):
    claim_id: str
    policy_id: str
    member_id: str
    claim_type: ClaimType
    sub_benefit: str
    diagnosis_code: str
    diagnosis_description: str
    procedure_codes: list[str]
    amount: float
    claim_date: date
    provider: str
    submitted_document_ids: list[str]


class DocumentReview(BaseModel):
    document_id: str
    expected_type: str | None = None
    actual_type: str
    status: DocumentStatus
    issues: list[str] = Field(default_factory=list)


class MedicalNecessityResult(BaseModel):
    diagnosis_code: str
    diagnosis_description: str
    procedure_codes: list[str]
    is_medically_necessary: bool
    reasoning: str
    warnings: list[str] = Field(default_factory=list)


class BenefitCalculation(BaseModel):
    submitted_amount: float
    deductible_applied: float
    after_deductible: float
    copay_percentage: float
    copay_amount: float
    insurer_amount: float
    sub_limit_cap: float | None = None
    covered_amount: float
    member_pays: float
    decision: str
    reason: str
    remaining_annual_limit: float
    remaining_deductible: float


class ToolCallEntry(BaseModel):
    tool_name: str
    inputs: dict
    outputs: dict


# --- LangGraph State ---

class ClaimAssessmentState(TypedDict):
    # Input (set once at start)
    claim: dict
    # Accumulated by nodes
    policy: dict | None
    policy_active: bool
    policy_rejection_reason: str | None
    document_reviews: Annotated[list, operator.add]
    required_documents: list[str]
    missing_documents: list[str]
    medical_necessity: dict | None
    benefit_calculation: dict | None
    # Decision
    recommendation: str | None
    recommendation_reason: str | None
    # Output
    report: dict | None
    tool_call_log: Annotated[list, operator.add]
