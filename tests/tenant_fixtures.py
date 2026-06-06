"""Seeded tenant configuration fixtures.

These dicts mirror the EXACT JSON shape seeded in the DB so the runtime can be
exercised without any network/database access.
"""

SAFEGUARD = {
    "branding": {
        "company_name": "SafeGuard Insurance",
        "logo_url": None,
        "primary_color": "#0B5FFF",
        "secondary_color": "#10243E",
    },
    "claim_types": ["OUTPATIENT", "INPATIENT", "DENTAL"],
    "documents": {
        "OUTPATIENT": {
            "required": ["medical_receipt"],
            "optional": ["prescription", "referral_letter"],
        },
        "INPATIENT": {
            "required": ["medical_receipt", "discharge_summary", "itemized_bill"],
            "optional": ["prescription"],
        },
        "DENTAL": {
            "required": ["dental_receipt"],
            "optional": ["treatment_plan"],
        },
    },
    "auto_approval_threshold": 20000,
    "approval_tiers": [
        {"min": 0, "max": 20000, "role": "auto"},
        {"min": 20000, "max": 100000, "role": "assessor"},
        {"min": 100000, "max": 500000, "role": "team_lead"},
        {"min": 500000, "max": None, "role": "director"},
    ],
    "notifications": {
        "claim_submitted": {"channels": ["email"]},
        "approved": {"channels": ["email"]},
        "rejected": {"channels": ["email"]},
        "payment_sent": {"channels": ["email"]},
    },
    "sla": {"OUTPATIENT": 5, "INPATIENT": 10, "default": 7},
    "custom_fields": [
        {"key": "employee_id", "label": "Employee ID", "type": "text", "required": True},
    ],
}

HEALTHFIRST = {
    "branding": {
        "company_name": "HealthFirst",
        "logo_url": None,
        "primary_color": "#1FA463",
        "secondary_color": "#0B3D2E",
    },
    "claim_types": ["OUTPATIENT", "INPATIENT", "DENTAL", "MATERNITY", "OPTICAL"],
    "documents": {
        "OUTPATIENT": {
            "required": ["medical_receipt"],
            "optional": ["prescription", "referral_letter"],
        },
        "INPATIENT": {
            "required": ["medical_receipt", "discharge_summary", "itemized_bill"],
            "optional": ["prescription"],
        },
        "DENTAL": {
            "required": ["dental_receipt"],
            "optional": ["treatment_plan"],
        },
        "MATERNITY": {
            "required": ["medical_receipt", "discharge_summary"],
            "optional": ["prenatal_records"],
        },
        "OPTICAL": {
            "required": ["optical_receipt"],
            "optional": ["prescription"],
        },
    },
    "auto_approval_threshold": 5000,
    "approval_tiers": [
        {"min": 0, "max": 5000, "role": "auto"},
        {"min": 5000, "max": 100000, "role": "assessor"},
        {"min": 100000, "max": None, "role": "manager"},
    ],
    "notifications": {
        "claim_submitted": {"channels": ["email", "sms"]},
        "approved": {"channels": ["email", "sms"]},
        "rejected": {"channels": ["email", "sms"]},
        "payment_sent": {"channels": ["email", "sms"]},
    },
    "sla": {"default": 7},
    "custom_fields": [],
}

GOVHEALTH = {
    "branding": {
        "company_name": "GovHealth",
        "logo_url": None,
        "primary_color": "#7A1F2B",
        "secondary_color": "#2E0B10",
    },
    "claim_types": ["OUTPATIENT", "INPATIENT"],
    "documents": {
        "OUTPATIENT": {
            "required": ["medical_receipt"],
            "optional": ["prescription", "referral_letter"],
        },
        "INPATIENT": {
            "required": ["medical_receipt", "discharge_summary", "itemized_bill"],
            "optional": ["prescription"],
        },
    },
    "auto_approval_threshold": 0,
    "approval_tiers": [
        {"min": 0, "max": None, "role": "committee"},
    ],
    "notifications": {
        "claim_submitted": {"channels": ["email", "webhook"]},
        "approved": {"channels": ["email", "webhook"]},
        "rejected": {"channels": ["email", "webhook"]},
        "payment_sent": {"channels": ["email", "webhook"]},
    },
    "sla": {"default": 15},
    "custom_fields": [
        {"key": "department", "label": "Department", "type": "text", "required": True},
        {"key": "budget_code", "label": "Budget Code", "type": "text", "required": True},
    ],
}

TENANTS = {
    "SafeGuard": SAFEGUARD,
    "HealthFirst": HEALTHFIRST,
    "GovHealth": GOVHEALTH,
}
