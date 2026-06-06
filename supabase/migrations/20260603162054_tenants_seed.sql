-- ============================================================================
-- Seed: 3 sample tenants + their active config (v1).  Challenge 15.
-- Idempotent: safe to re-run (on conflict do nothing / update).
-- Fixed UUIDs so policies/claims/users can reference tenants deterministically.
-- ============================================================================

insert into tenants (id, slug, name) values
  ('a0000000-0000-0000-0000-000000000001', 'safeguard',  'SafeGuard Insurance'),
  ('a0000000-0000-0000-0000-000000000002', 'healthfirst','HealthFirst'),
  ('a0000000-0000-0000-0000-000000000003', 'govhealth',  'GovHealth')
on conflict (id) do update set slug = excluded.slug, name = excluded.name;

-- ---- Tenant A: SafeGuard (Corporate) ----
insert into tenant_configs (tenant_id, version, config, is_active) values
('a0000000-0000-0000-0000-000000000001', 1, '{
  "branding": { "company_name": "SafeGuard Insurance", "logo_url": null, "primary_color": "#0B5FFF", "secondary_color": "#10243E" },
  "claim_types": ["OUTPATIENT", "INPATIENT", "DENTAL"],
  "documents": {
    "OUTPATIENT": { "required": ["medical_receipt"], "optional": ["prescription", "referral_letter"] },
    "INPATIENT":  { "required": ["medical_receipt", "discharge_summary", "itemized_bill"], "optional": ["prescription"] },
    "DENTAL":     { "required": ["dental_receipt"], "optional": ["treatment_plan"] }
  },
  "auto_approval_threshold": 20000,
  "approval_tiers": [
    { "min": 0,      "max": 20000,  "role": "auto" },
    { "min": 20000,  "max": 100000, "role": "assessor" },
    { "min": 100000, "max": 500000, "role": "team_lead" },
    { "min": 500000, "max": null,   "role": "director" }
  ],
  "notifications": {
    "claim_submitted": { "channels": ["email"] },
    "approved":        { "channels": ["email"] },
    "rejected":        { "channels": ["email"] },
    "payment_sent":    { "channels": ["email"] }
  },
  "sla": { "OUTPATIENT": 5, "INPATIENT": 10, "default": 7 },
  "custom_fields": [
    { "key": "employee_id", "label": "Employee ID", "type": "text", "required": true }
  ]
}'::jsonb, true)
on conflict (tenant_id, version) do update set config = excluded.config;

-- ---- Tenant B: HealthFirst (Retail) ----
insert into tenant_configs (tenant_id, version, config, is_active) values
('a0000000-0000-0000-0000-000000000002', 1, '{
  "branding": { "company_name": "HealthFirst", "logo_url": null, "primary_color": "#16A34A", "secondary_color": "#064E3B" },
  "claim_types": ["OUTPATIENT", "INPATIENT", "DENTAL", "MATERNITY", "OPTICAL"],
  "documents": {
    "OUTPATIENT": { "required": ["medical_receipt"], "optional": ["prescription", "referral_letter"] },
    "INPATIENT":  { "required": ["medical_receipt", "discharge_summary", "itemized_bill"], "optional": ["prescription"] },
    "DENTAL":     { "required": ["dental_receipt"], "optional": ["treatment_plan"] },
    "MATERNITY":  { "required": ["medical_receipt", "discharge_summary"], "optional": ["prenatal_records"] },
    "OPTICAL":    { "required": ["optical_receipt"], "optional": ["prescription"] }
  },
  "auto_approval_threshold": 5000,
  "approval_tiers": [
    { "min": 0,      "max": 5000,   "role": "auto" },
    { "min": 5000,   "max": 100000, "role": "assessor" },
    { "min": 100000, "max": null,   "role": "manager" }
  ],
  "notifications": {
    "claim_submitted": { "channels": ["email", "sms"] },
    "approved":        { "channels": ["email", "sms"] },
    "rejected":        { "channels": ["email", "sms"] },
    "payment_sent":    { "channels": ["email", "sms"] }
  },
  "sla": { "default": 7 },
  "custom_fields": []
}'::jsonb, true)
on conflict (tenant_id, version) do update set config = excluded.config;

-- ---- Tenant C: GovHealth (Government) ----
insert into tenant_configs (tenant_id, version, config, is_active) values
('a0000000-0000-0000-0000-000000000003', 1, '{
  "branding": { "company_name": "GovHealth", "logo_url": null, "primary_color": "#B91C1C", "secondary_color": "#3F1D1D" },
  "claim_types": ["OUTPATIENT", "INPATIENT"],
  "documents": {
    "OUTPATIENT": { "required": ["medical_receipt"], "optional": ["prescription", "referral_letter"] },
    "INPATIENT":  { "required": ["medical_receipt", "discharge_summary", "itemized_bill"], "optional": ["prescription"] }
  },
  "auto_approval_threshold": 0,
  "approval_tiers": [
    { "min": 0, "max": null, "role": "committee" }
  ],
  "notifications": {
    "claim_submitted": { "channels": ["email", "webhook"] },
    "approved":        { "channels": ["email", "webhook"] },
    "rejected":        { "channels": ["email", "webhook"] },
    "payment_sent":    { "channels": ["email", "webhook"] }
  },
  "sla": { "default": 15 },
  "custom_fields": [
    { "key": "department",  "label": "Department",  "type": "text", "required": true },
    { "key": "budget_code", "label": "Budget Code", "type": "text", "required": true }
  ]
}'::jsonb, true)
on conflict (tenant_id, version) do update set config = excluded.config;
