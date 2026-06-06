-- Seed sample policies for the 3 demo tenants.
-- Safe to re-run: uses ON CONFLICT (tenant_id, policy_number) DO UPDATE.
-- Covers OUTPATIENT / INPATIENT / DENTAL benefit structures used by the
-- assessment agent (lookupPolicy + calculateBenefit) and guard layer.

insert into policies (tenant_id, policy_number, data)
values
  -- ── SafeGuard ── POL-001: OUTPATIENT only, mid-tier limits ─────────────────
  ('a0000000-0000-0000-0000-000000000001', 'POL-001', '{
    "policy_id":     "POL-001",
    "policy_number": "POL-001",
    "policy_name":   "SafeGuard Outpatient Basic",
    "status":        "ACTIVE",
    "effective_date":"2024-01-01",
    "expiry_date":   "2026-12-31",
    "member_ids":    ["MBR-001","MBR-002","MBR-003"],
    "benefits": [
      {
        "type": "OUTPATIENT",
        "annual_limit": 100000,
        "waiting_period_days": 0,
        "sub_benefits": [
          {"name": "Doctor Visit",       "limit_per_visit": 3000, "visits_per_year": 30},
          {"name": "Prescribed Medicine","limit_per_visit": 3000},
          {"name": "Diagnostic Tests",   "limit_per_year":  20000}
        ]
      }
    ],
    "deductible": {"annual": 0, "per_visit": 0},
    "copay_percent": 0,
    "exclusions": [
      {
        "clause": "Clause 8.1 — Cosmetic procedures",
        "description": "Cosmetic and aesthetic procedures are excluded.",
        "keywords": ["cosmetic", "aesthetic", "rhinoplasty", "liposuction"]
      },
      {
        "clause": "Clause 8.2 — Pre-existing (waiting period)",
        "description": "Pre-existing conditions diagnosed before policy start are excluded for 12 months.",
        "keywords": []
      }
    ]
  }'::jsonb),

  -- ── SafeGuard ── POL-002: INPATIENT only, high limits ──────────────────────
  ('a0000000-0000-0000-0000-000000000001', 'POL-002', '{
    "policy_id":     "POL-002",
    "policy_number": "POL-002",
    "policy_name":   "SafeGuard Inpatient Plus",
    "status":        "ACTIVE",
    "effective_date":"2024-01-01",
    "expiry_date":   "2026-12-31",
    "member_ids":    ["MBR-010"],
    "benefits": [
      {
        "type": "INPATIENT",
        "annual_limit": 500000,
        "waiting_period_days": 30,
        "sub_benefits": [
          {"name": "Surgery",            "limit_per_event": 200000},
          {"name": "Room and Board",     "limit_per_day":    5000,  "days_per_year": 60},
          {"name": "ICU",                "limit_per_day":   10000,  "days_per_year": 30},
          {"name": "Nursing",            "limit_per_day":    2000,  "days_per_year": 60},
          {"name": "Prescribed Medicine","limit_per_event": 20000}
        ]
      }
    ],
    "deductible": {"annual": 5000, "per_visit": 0},
    "copay_percent": 10,
    "exclusions": [
      {
        "clause": "Clause 9.1 — Experimental treatments",
        "description": "Experimental or investigational treatments are not covered.",
        "keywords": ["experimental", "investigational", "unproven"]
      }
    ]
  }'::jsonb),

  -- ── SafeGuard ── POL-003: OUTPATIENT + INPATIENT + DENTAL, comprehensive ───
  ('a0000000-0000-0000-0000-000000000001', 'POL-003', '{
    "policy_id":     "POL-003",
    "policy_number": "POL-003",
    "policy_name":   "SafeGuard Comprehensive",
    "status":        "ACTIVE",
    "effective_date":"2024-01-01",
    "expiry_date":   "2026-12-31",
    "member_ids":    ["MBR-020","MBR-021","MBR-022"],
    "benefits": [
      {
        "type": "OUTPATIENT",
        "annual_limit": 80000,
        "waiting_period_days": 0,
        "sub_benefits": [
          {"name": "Doctor Visit",       "limit_per_visit": 2500, "visits_per_year": 20},
          {"name": "Prescribed Medicine","limit_per_visit": 2000},
          {"name": "Diagnostic Tests",   "limit_per_year": 15000}
        ]
      },
      {
        "type": "INPATIENT",
        "annual_limit": 300000,
        "waiting_period_days": 30,
        "sub_benefits": [
          {"name": "Surgery",            "limit_per_event": 150000},
          {"name": "Room and Board",     "limit_per_day":    3500,  "days_per_year": 45},
          {"name": "Prescribed Medicine","limit_per_event":  15000}
        ]
      },
      {
        "type": "DENTAL",
        "annual_limit": 20000,
        "waiting_period_days": 90,
        "sub_benefits": [
          {"name": "Dental Check-up",    "limit_per_visit": 1500, "visits_per_year": 2},
          {"name": "Dental Filling",     "limit_per_visit": 3000},
          {"name": "Root Canal",         "limit_per_event": 8000},
          {"name": "Dental Extraction",  "limit_per_visit": 2000}
        ]
      }
    ],
    "deductible": {"annual": 0, "per_visit": 0},
    "copay_percent": 0,
    "exclusions": [
      {
        "clause": "Clause 8.1 — Cosmetic procedures",
        "description": "Cosmetic and aesthetic procedures are excluded.",
        "keywords": ["cosmetic", "aesthetic", "rhinoplasty", "liposuction"]
      }
    ]
  }'::jsonb)

on conflict (tenant_id, policy_number)
do update set data = excluded.data;
