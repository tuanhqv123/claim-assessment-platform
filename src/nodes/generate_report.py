from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from src.config import require_env
from src.prompts.report_prompt import REPORT_SYSTEM_PROMPT

load_dotenv()


class DocumentReviewItem(BaseModel):
    document_id: str
    type: str
    status: str
    issues: str


class PolicyVerification(BaseModel):
    policy_active: bool
    member_covered: bool
    claim_type_covered: bool
    coverage_period_valid: bool
    details: str


class MedicalNecessitySection(BaseModel):
    is_appropriate: bool
    reasoning: str
    warnings: list[str]


class BenefitCalculationSection(BaseModel):
    submitted_amount: str
    covered_amount: str
    copay_amount: str
    member_pays: str
    remaining_limit: str
    breakdown: str


class RecommendationSection(BaseModel):
    decision: str
    reasoning: str
    next_steps: str


class PolicyCitation(BaseModel):
    clause: str
    relevance: str


class AssessmentReport(BaseModel):
    document_review: list[DocumentReviewItem]
    policy_verification: PolicyVerification
    medical_necessity: MedicalNecessitySection
    benefit_calculation: BenefitCalculationSection
    recommendation: RecommendationSection
    policy_citations: list[PolicyCitation]


_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        )
    return _client


def generate_report_node(state: dict) -> dict:
    client = _get_client()
    model = require_env("OPENAI_MODEL")

    context = _build_context(state)

    use_strict = os.getenv("OPENAI_BASE_URL") is None
    if use_strict:
        try:
            report = _call_with_strict_schema(client, model, context)
        except Exception:
            report = _call_with_json_mode_fallback(client, model, context)
    else:
        report = _call_with_json_mode_fallback(client, model, context)

    return {"report": report}


def _call_with_strict_schema(client: OpenAI, model: str, context: str) -> dict:
    response = client.beta.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        response_format=AssessmentReport,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Structured output returned None")
    return parsed.model_dump()


def _call_with_json_mode_fallback(client: OpenAI, model: str, context: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": REPORT_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        response_format={"type": "json_object"},
    )
    report_text = response.choices[0].message.content
    try:
        return json.loads(_strip_markdown_fences(report_text))
    except json.JSONDecodeError:
        return {"raw_text": report_text, "parse_error": True}


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _build_context(state: dict) -> str:
    sections = []

    sections.append("## Claim Data")
    sections.append(json.dumps(state.get("claim", {}), indent=2, default=str))

    sections.append("\n## Policy Data")
    policy = state.get("policy")
    if policy:
        sections.append(json.dumps(policy, indent=2, default=str))
    else:
        sections.append("Policy not found")

    sections.append("\n## Document Reviews")
    sections.append(json.dumps(state.get("document_reviews", []), indent=2))

    sections.append("\n## Missing Documents")
    sections.append(json.dumps(state.get("missing_documents", []), indent=2))

    sections.append("\n## Medical Necessity Check")
    sections.append(json.dumps(state.get("medical_necessity"), indent=2))

    sections.append("\n## Benefit Calculation")
    sections.append(json.dumps(state.get("benefit_calculation"), indent=2, default=str))

    sections.append("\n## Recommendation Decision")
    sections.append(f"Decision: {state.get('recommendation', 'UNKNOWN')}")
    sections.append(f"Reason: {state.get('recommendation_reason', 'N/A')}")

    return "\n".join(sections)
