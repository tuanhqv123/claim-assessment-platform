"""Render a readable policy document from structured policy data.

Real insurers upload a signed policy PDF; until one is uploaded we render a
clause-structured document from the policy's own numbers so the RAG corpus is
always consistent with the schedule of benefits. When an admin uploads a real
document, its extracted text is stored in ``data['terms_document']`` and used
instead of this rendered fallback.
"""
from __future__ import annotations


def _money(v) -> str:
    try:
        return f"{int(v):,} THB"
    except (TypeError, ValueError):
        return str(v)


def _benefit_section(b: dict) -> str:
    btype = b.get("type", "BENEFIT")
    lines = [
        f"{btype} BENEFIT",
        f"The annual limit for {btype.lower()} benefits is {_money(b.get('annual_limit'))}.",
    ]
    for sb in b.get("sub_benefits", []) or []:
        parts = [f"{sb.get('name')}:"]
        if sb.get("limit_per_visit") is not None:
            parts.append(f"up to {_money(sb['limit_per_visit'])} per visit")
        if sb.get("limit_per_day") is not None:
            parts.append(f"up to {_money(sb['limit_per_day'])} per day")
        if sb.get("limit_per_event") is not None:
            parts.append(f"up to {_money(sb['limit_per_event'])} per event")
        if sb.get("limit_per_year") is not None:
            parts.append(f"up to {_money(sb['limit_per_year'])} per policy year")
        if sb.get("visits_per_year") is not None:
            parts.append(f"limited to {sb['visits_per_year']} visits per policy year")
        if sb.get("max_days") is not None:
            parts.append(f"for a maximum of {sb['max_days']} days")
        lines.append(" ".join(parts).rstrip(",") + ".")
    return "\n".join(lines)


def render_policy_document(policy: dict) -> str:
    """Produce a clause-structured policy document (one string) from policy data."""
    pid = policy.get("policy_id", "")
    holder = policy.get("policyholder_name", "the Policyholder")
    htype = (policy.get("policyholder_type") or "").title()
    currency = policy.get("currency", "THB")

    out: list[str] = []
    out.append(f"HEALTH INSURANCE POLICY — {pid}")
    out.append(f"Policyholder: {holder} ({htype} Plan). All amounts are in {currency}.")

    # 1. Coverage overview
    covered = ", ".join(b.get("type", "").lower() for b in policy.get("benefits", []))
    out.append(
        "1. COVERAGE OVERVIEW\n"
        f"This policy provides {covered} benefits to enrolled members named in the "
        "schedule. Coverage is subject to the annual limits, per-visit limits, "
        "co-payments, deductibles and conditions set out in this document."
    )

    # 2. Definitions — the qualitative anchor RAG most often needs.
    out.append(
        "2. DEFINITIONS\n"
        '"Medically Necessary" means a service or supply that is required to '
        "identify or treat an illness or injury, is consistent with the diagnosis, "
        "is provided in accordance with generally accepted medical standards, and is "
        "not primarily for the convenience of the member or the provider. "
        "Experimental, investigational or unproven treatments are not considered "
        "medically necessary and are not covered."
    )

    # 3. Eligibility & waiting periods
    wp = policy.get("waiting_periods") or {}
    general = wp.get("general_days", 30)
    pre_ex = wp.get("pre_existing_days", 365)
    out.append(
        "3. ELIGIBILITY AND WAITING PERIODS\n"
        f"A general waiting period of {general} days from a member's effective date "
        "applies to all benefits. Conditions that existed before enrolment "
        f"(pre-existing conditions) are subject to a waiting period of {pre_ex} days. "
        "Treatment received during an applicable waiting period is not reimbursable."
    )

    # 4. Exclusions — emit the heading, then each clause as its own paragraph so
    #    the chunker indexes (and can cite) each exclusion separately.
    out.append(
        "4. EXCLUSIONS\nThe following are not covered under any benefit:"
    )
    for ex in policy.get("exclusions", []) or []:
        clause = ex.get("clause", "")
        desc = ex.get("description", "")
        kw = ex.get("keywords") or []
        kw_str = f" This includes {', '.join(kw)}." if kw else ""
        out.append(f"Exclusion {clause} — {desc}.{kw_str}")

    # 5..N. Benefit schedules
    for b in policy.get("benefits", []) or []:
        out.append(_benefit_section(b))

    # Co-payment & deductible
    copay = policy.get("copay") or {}
    if copay:
        cp_lines = ["CO-PAYMENT"]
        for btype, c in copay.items():
            pct = c.get("percentage", 0)
            extra = ""
            if c.get("max_per_visit") is not None:
                extra = f", capped at {_money(c['max_per_visit'])} per visit"
            cp_lines.append(
                f"For {btype.lower()} claims the member pays {pct}% of the eligible "
                f"amount as co-payment{extra}."
            )
        out.append("\n".join(cp_lines))
    ded = policy.get("deductible") or {}
    if ded.get("annual") or ded.get("per_visit"):
        out.append(
            "DEDUCTIBLE\n"
            f"An annual deductible of {_money(ded.get('annual', 0))} and a per-visit "
            f"deductible of {_money(ded.get('per_visit', 0))} apply before benefits "
            "are payable."
        )

    # Network hospitals
    network = policy.get("network_hospitals") or []
    if network:
        out.append(
            "NETWORK HOSPITALS\n"
            "Treatment at the following network hospitals is covered without "
            f"pre-authorization: {', '.join(network)}. Treatment outside the network "
            "may require prior approval."
        )

    # Claims procedure
    out.append(
        "CLAIMS PROCEDURE\n"
        "Claims must be submitted within 90 days of the date of treatment, "
        "accompanied by an itemized medical receipt. Inpatient claims also require a "
        "discharge summary and an itemized hospital bill. Claims missing required "
        "documents are placed on hold pending further information."
    )

    return "\n\n".join(out)
