from __future__ import annotations

from datetime import date, datetime


class BenefitCalculator:
    def __init__(self):
        self._used_annual_limit: dict[str, float] = {}
        self._used_deductible: float = 0.0

    def calculate(
        self,
        policy: dict,
        claim_type: str,
        sub_benefit_name: str,
        amount: float,
        claim_date: str,
        diagnosis_description: str,
    ) -> dict:
        claim_dt = _parse_date(claim_date)
        effective_dt = _parse_date(policy["effective_date"])

        # 1. Find matching benefit
        benefit = None
        for b in policy["benefits"]:
            if b["type"] == claim_type:
                benefit = b
                break

        if benefit is None:
            return _denied(amount, f"Claim type {claim_type} is not covered under this policy")

        # 2. Check waiting period
        days_since_start = (claim_dt - effective_dt).days
        waiting = benefit.get("waiting_period_days", 0)
        if days_since_start < waiting:
            return _denied(
                amount,
                f"Claim is within the {waiting}-day waiting period "
                f"(policy effective {policy['effective_date']}, claim date {claim_date}, "
                f"{days_since_start} days elapsed)",
            )

        # 3. Check exclusions
        for excl in policy.get("exclusions", []):
            for keyword in excl.get("keywords", []):
                if keyword.lower() in diagnosis_description.lower():
                    return _denied(
                        amount,
                        f"Excluded under {excl['clause']}: {excl['description']}",
                    )

        # 4. Apply deductible (annual + per-visit)
        deductible_config = policy.get("deductible", {})
        annual_deductible = deductible_config.get("annual", 0)
        per_visit_deductible = deductible_config.get("per_visit", 0)
        remaining_annual_ded = max(0, annual_deductible - self._used_deductible)
        annual_ded_applied = min(amount, remaining_annual_ded)
        per_visit_ded_applied = min(amount - annual_ded_applied, per_visit_deductible)
        deductible_applied = annual_ded_applied + per_visit_ded_applied
        after_deductible = amount - deductible_applied
        self._used_deductible += annual_ded_applied

        if after_deductible <= 0:
            return {
                **_denied(amount, "Entire amount consumed by deductible"),
                "deductible_applied": deductible_applied,
                "remaining_deductible": max(0, annual_deductible - self._used_deductible),
            }

        # 5. Apply sub-limit (cap eligible amount BEFORE copay)
        sub_limit_cap = None
        for sb in benefit.get("sub_benefits", []):
            if sb["name"] == sub_benefit_name:
                if sb.get("limit_per_visit"):
                    sub_limit_cap = sb["limit_per_visit"]
                elif sb.get("limit_per_day"):
                    sub_limit_cap = sb["limit_per_day"]
                elif sb.get("limit_per_event"):
                    sub_limit_cap = sb["limit_per_event"]
                elif sb.get("limit_per_year"):
                    sub_limit_cap = sb["limit_per_year"]
                break

        eligible_amount = after_deductible
        if sub_limit_cap is not None:
            eligible_amount = min(after_deductible, sub_limit_cap)

        # 6. Apply copay (on eligible amount after sub-limit)
        copay_config = policy.get("copay", {}).get(claim_type, {})
        copay_pct = copay_config.get("percentage", 0) / 100
        copay_amount = eligible_amount * copay_pct
        max_copay = copay_config.get("max_per_visit")
        if max_copay is not None:
            copay_amount = min(copay_amount, max_copay)
        insurer_amount = eligible_amount - copay_amount

        # 7. Apply annual limit
        annual_limit = benefit["annual_limit"]
        used = self._used_annual_limit.get(claim_type, 0)
        remaining_annual = annual_limit - used
        covered_amount = min(insurer_amount, remaining_annual)
        self._used_annual_limit[claim_type] = used + covered_amount

        member_pays = amount - covered_amount
        new_remaining = remaining_annual - covered_amount

        decision = "COVERED" if covered_amount > 0 else "DENIED"
        reason_parts = []
        if deductible_applied > 0:
            reason_parts.append(f"Deductible applied: {deductible_applied:.0f} THB")
        if copay_amount > 0:
            reason_parts.append(f"Copay {copay_pct*100:.0f}%: {copay_amount:.0f} THB")
        if sub_limit_cap is not None and after_deductible > sub_limit_cap:
            reason_parts.append(f"Sub-limit cap: {sub_limit_cap:.0f} THB")
        if covered_amount < insurer_amount and new_remaining == 0:
            reason_parts.append("Annual limit reached")
        reason = ". ".join(reason_parts) if reason_parts else "Fully covered"

        return {
            "submitted_amount": amount,
            "deductible_applied": deductible_applied,
            "after_deductible": after_deductible,
            "copay_percentage": copay_pct * 100,
            "copay_amount": copay_amount,
            "insurer_amount": insurer_amount,
            "sub_limit_cap": sub_limit_cap,
            "covered_amount": covered_amount,
            "member_pays": member_pays,
            "decision": decision,
            "reason": reason,
            "remaining_annual_limit": new_remaining,
            "remaining_deductible": max(0, annual_deductible - self._used_deductible),
        }


def calculate_benefit_node(state: dict) -> dict:
    claim = state["claim"]
    policy = state["policy"]

    calculator = BenefitCalculator()

    sub_benefit_name = claim.get("sub_benefit") or _find_sub_benefit(policy, claim["claim_type"])

    result = calculator.calculate(
        policy=policy,
        claim_type=claim["claim_type"],
        sub_benefit_name=sub_benefit_name,
        amount=claim["amount"],
        claim_date=claim["claim_date"],
        diagnosis_description=claim.get("diagnosis_description", ""),
    )

    log_entry = {
        "tool_name": "calculateBenefit",
        "inputs": {
            "policy_id": claim["policy_id"],
            "claim_type": claim["claim_type"],
            "sub_benefit": sub_benefit_name,
            "amount": claim["amount"],
        },
        "outputs": result,
    }

    return {
        "benefit_calculation": result,
        "tool_call_log": [log_entry],
    }


def _find_sub_benefit(policy: dict, claim_type: str) -> str:
    """Fallback: return first sub-benefit name for claim type."""
    for b in policy.get("benefits", []):
        if b["type"] == claim_type and b.get("sub_benefits"):
            return b["sub_benefits"][0]["name"]
    return "Unknown"


def _denied(amount: float, reason: str) -> dict:
    return {
        "submitted_amount": amount,
        "deductible_applied": 0,
        "after_deductible": 0,
        "copay_percentage": 0,
        "copay_amount": 0,
        "insurer_amount": 0,
        "sub_limit_cap": None,
        "covered_amount": 0,
        "member_pays": amount,
        "decision": "DENIED",
        "reason": reason,
        "remaining_annual_limit": 0,
        "remaining_deductible": 0,
    }


def _parse_date(d) -> date:
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()
