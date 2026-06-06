import pytest
from src.nodes.calculate_benefit import BenefitCalculator


@pytest.fixture
def calculator(tmp_path):
    return BenefitCalculator()


@pytest.fixture
def policy_outpatient():
    return {
        "benefits": [
            {
                "type": "OUTPATIENT",
                "annual_limit": 100000,
                "sub_benefits": [
                    {"name": "Doctor Visit", "limit_per_visit": 3000, "visits_per_year": 30}
                ],
                "waiting_period_days": 30,
            }
        ],
        "copay": {"OUTPATIENT": {"percentage": 20, "max_per_visit": 500}},
        "deductible": {"annual": 0, "per_visit": 0},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 30, "pre_existing_days": 365},
        "exclusions": [
            {"clause": "T&C 8.2", "description": "Cosmetic surgery", "keywords": ["cosmetic"]}
        ],
    }


def test_normal_coverage_with_copay(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=2500,
        claim_date="2024-03-15",
        diagnosis_description="Acute respiratory infection",
    )
    assert result["covered_amount"] == 2000
    assert result["copay_amount"] == 500
    assert result["member_pays"] == 500
    assert result["decision"] == "COVERED"


def test_amount_exceeds_sub_limit(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=5000,
        claim_date="2024-03-15",
        diagnosis_description="Acute respiratory infection",
    )
    # 5000 → sub-limit cap 3000 (eligible) → copay 20% of 3000 = 600 BUT max_copay 500 → covered 2500
    # Wait — let me trace: eligible=min(5000,3000)=3000, copay=3000*0.20=600, max_copay=500, so copay=500, insurer=2500
    assert result["covered_amount"] == 2500
    assert result["member_pays"] == 2500


def test_waiting_period_denial(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=2500,
        claim_date="2024-01-15",
        diagnosis_description="Acute respiratory infection",
    )
    assert result["covered_amount"] == 0
    assert result["decision"] == "DENIED"
    assert "waiting period" in result["reason"].lower()


def test_exclusion_denial(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=2500,
        claim_date="2024-03-15",
        diagnosis_description="Cosmetic rhinoplasty procedure",
    )
    assert result["covered_amount"] == 0
    assert result["decision"] == "DENIED"
    assert "T&C 8.2" in result["reason"]


def test_with_annual_deductible():
    calc = BenefitCalculator()
    policy = {
        "benefits": [
            {
                "type": "OUTPATIENT",
                "annual_limit": 50000,
                "sub_benefits": [
                    {"name": "Doctor Visit", "limit_per_visit": 5000, "visits_per_year": 20}
                ],
                "waiting_period_days": 0,
            }
        ],
        "copay": {"OUTPATIENT": {"percentage": 0}},
        "deductible": {"annual": 2000, "per_visit": 0},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 0, "pre_existing_days": 365},
        "exclusions": [],
    }
    result = calc.calculate(
        policy=policy,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=5000,
        claim_date="2024-03-15",
        diagnosis_description="Checkup",
    )
    # 5000 - 2000 deductible = 3000, sub-limit 5000 (not hit), no copay → covered 3000
    assert result["deductible_applied"] == 2000
    assert result["covered_amount"] == 3000
    assert result["member_pays"] == 2000


def test_annual_limit_exhaustion():
    calc = BenefitCalculator()
    policy = {
        "benefits": [
            {
                "type": "OUTPATIENT",
                "annual_limit": 3000,
                "sub_benefits": [
                    {"name": "Doctor Visit", "limit_per_visit": 5000, "visits_per_year": 30}
                ],
                "waiting_period_days": 0,
            }
        ],
        "copay": {"OUTPATIENT": {"percentage": 0}},
        "deductible": {"annual": 0, "per_visit": 0},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 0, "pre_existing_days": 365},
        "exclusions": [],
    }
    result = calc.calculate(
        policy=policy,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=5000,
        claim_date="2024-03-15",
        diagnosis_description="Visit",
    )
    # No deductible, no copay, sub-limit 5000, but annual limit 3000
    assert result["covered_amount"] == 3000
    assert result["remaining_annual_limit"] == 0


def test_claim_type_not_in_policy():
    calc = BenefitCalculator()
    policy = {
        "benefits": [
            {"type": "OUTPATIENT", "annual_limit": 100000, "sub_benefits": [], "waiting_period_days": 0}
        ],
        "copay": {},
        "deductible": {"annual": 0, "per_visit": 0},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 0, "pre_existing_days": 365},
        "exclusions": [],
    }
    result = calc.calculate(
        policy=policy,
        claim_type="DENTAL",
        sub_benefit_name="Basic Dental",
        amount=5000,
        claim_date="2024-03-15",
        diagnosis_description="Dental cleaning",
    )
    assert result["covered_amount"] == 0
    assert result["decision"] == "DENIED"
    assert "not covered" in result["reason"].lower()


def test_exact_waiting_period_boundary(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=2500,
        claim_date="2024-01-31",
        diagnosis_description="Flu",
    )
    # Day 30 exactly — should pass (30 days elapsed >= 30 day waiting)
    assert result["decision"] == "COVERED"


def test_exact_sub_limit_amount(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=3000,
        claim_date="2024-03-15",
        diagnosis_description="Visit",
    )
    # 3000 exactly at sub-limit → eligible=3000, copay=min(600,500)=500, covered=2500
    assert result["covered_amount"] == 2500
    assert result["copay_amount"] == 500


def test_zero_amount(calculator, policy_outpatient):
    result = calculator.calculate(
        policy=policy_outpatient,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=0,
        claim_date="2024-03-15",
        diagnosis_description="Visit",
    )
    assert result["covered_amount"] == 0


def test_amount_fully_consumed_by_deductible():
    calc = BenefitCalculator()
    policy = {
        "benefits": [
            {
                "type": "OUTPATIENT",
                "annual_limit": 50000,
                "sub_benefits": [{"name": "Doctor Visit", "limit_per_visit": 5000}],
                "waiting_period_days": 0,
            }
        ],
        "copay": {"OUTPATIENT": {"percentage": 0}},
        "deductible": {"annual": 10000, "per_visit": 0},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 0, "pre_existing_days": 365},
        "exclusions": [],
    }
    result = calc.calculate(
        policy=policy,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=5000,
        claim_date="2024-03-15",
        diagnosis_description="Visit",
    )
    # 5000 < 10000 deductible → entire amount consumed
    assert result["covered_amount"] == 0
    assert result["decision"] == "DENIED"
    assert result["deductible_applied"] == 5000


def test_per_visit_deductible():
    calc = BenefitCalculator()
    policy = {
        "benefits": [
            {
                "type": "OUTPATIENT",
                "annual_limit": 100000,
                "sub_benefits": [{"name": "Doctor Visit", "limit_per_visit": 5000}],
                "waiting_period_days": 0,
            }
        ],
        "copay": {"OUTPATIENT": {"percentage": 0}},
        "deductible": {"annual": 0, "per_visit": 500},
        "effective_date": "2024-01-01",
        "waiting_periods": {"general_days": 0, "pre_existing_days": 365},
        "exclusions": [],
    }
    result = calc.calculate(
        policy=policy,
        claim_type="OUTPATIENT",
        sub_benefit_name="Doctor Visit",
        amount=3000,
        claim_date="2024-03-15",
        diagnosis_description="Visit",
    )
    # 3000 - 500 per_visit deductible = 2500, sub-limit 5000 (not hit), no copay
    assert result["deductible_applied"] == 500
    assert result["covered_amount"] == 2500
    assert result["member_pays"] == 500
