-- ============================================================================
-- Foundation schema: multi-tenant claims platform
-- Challenges 08 (documents/OCR), 11 (assessment), 14 (workflow), 15 (multi-tenant)
-- No RLS by design: tenant-scoping enforced in the app middleware layer.
-- ============================================================================

-- ---------- Enums ----------

-- Claim types (15 adds OPTICAL on top of the 11 base set)
create type claim_type as enum (
  'OUTPATIENT', 'INPATIENT', 'DENTAL', 'MATERNITY', 'OPTICAL'
);

-- App roles: union of workflow roles (14) and approval-tier roles (15)
create type app_role as enum (
  'document_clerk', 'assessor', 'team_lead', 'manager',
  'director', 'committee', 'finance', 'admin'
);

-- Workflow states (14)
create type claim_state as enum (
  'SUBMITTED', 'DOCUMENTS_VERIFIED', 'UNDER_ASSESSMENT', 'PENDING_INFO',
  'APPROVED', 'REJECTED', 'PAYMENT_INITIATED', 'CLOSED'
);

-- Agent recommendation (11)
create type recommendation as enum (
  'APPROVE', 'REJECT', 'REQUEST_MORE_INFO'
);

-- Per-document verification status (11)
create type document_status as enum (
  'COMPLETE', 'INCOMPLETE', 'MISSING', 'TYPE_MISMATCH'
);

-- ---------- Shared trigger helpers ----------

create or replace function set_updated_at() returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Append-only guard for the audit trail (14: immutable, cannot be modified/deleted)
create or replace function prevent_mutation() returns trigger as $$
begin
  raise exception 'append-only table: % is not allowed on %', tg_op, tg_table_name;
end;
$$ language plpgsql;

-- ---------- Tenants (15) ----------

create table tenants (
  id          uuid primary key default gen_random_uuid(),
  slug        text not null unique,
  name        text not null,
  created_at  timestamptz not null default now()
);

-- Versioned tenant configuration (15: history + rollback).
-- Every save inserts a new version row; exactly one is active per tenant.
create table tenant_configs (
  id          uuid primary key default gen_random_uuid(),
  tenant_id   uuid not null references tenants(id) on delete cascade,
  version     int  not null,
  config      jsonb not null,   -- branding, claim_types, required/optional docs,
                                -- auto_approval_threshold, approval_tiers,
                                -- notifications, sla, custom_fields
  is_active   boolean not null default true,
  created_by  uuid,             -- profiles/auth user who saved this version
  created_at  timestamptz not null default now(),
  unique (tenant_id, version)
);
-- At most one active config per tenant
create unique index tenant_configs_one_active
  on tenant_configs(tenant_id) where is_active;

-- ---------- Users / roles (auth) ----------
-- Linked to Supabase Auth. Real login; role+tenant checked by app middleware.

create table profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  tenant_id   uuid references tenants(id) on delete set null,
  email       text,
  full_name   text,
  role        app_role not null default 'assessor',
  created_at  timestamptz not null default now()
);
create index profiles_tenant_idx on profiles(tenant_id);

-- ---------- Policies (11) ----------
-- Full policy document kept as jsonb (reuses data/policies/*.json shape).

create table policies (
  id            uuid primary key default gen_random_uuid(),
  tenant_id     uuid not null references tenants(id) on delete cascade,
  policy_number text not null,            -- e.g. POL-001
  data          jsonb not null,           -- status, dates, members, benefits,
                                          -- copay, deductible, exclusions, ...
  created_at    timestamptz not null default now(),
  unique (tenant_id, policy_number)
);

-- ---------- Claims ----------

create table claims (
  id                   uuid primary key default gen_random_uuid(),
  tenant_id            uuid not null references tenants(id) on delete cascade,
  claim_number         text not null,                 -- e.g. CLM-001
  policy_id            uuid references policies(id) on delete set null,
  member_id            text,
  claim_type           claim_type not null,
  sub_benefit          text,
  diagnosis_code       text,
  diagnosis_description text,
  procedure_codes      text[] not null default '{}',
  amount               numeric(14,2) not null default 0,
  claim_date           date,
  provider             text,
  custom_fields        jsonb not null default '{}',    -- 15: tenant custom fields
  state                claim_state not null default 'SUBMITTED',
  info_request_count   int not null default 0,         -- 14: cycle detection
  sla_deadline         date,                           -- 15: derived from SLA
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  unique (tenant_id, claim_number)
);
create index claims_state_idx on claims(tenant_id, state);
create trigger claims_set_updated_at
  before update on claims
  for each row execute function set_updated_at();

-- ---------- Documents (08) ----------

create table documents (
  id             uuid primary key default gen_random_uuid(),
  tenant_id      uuid not null references tenants(id) on delete cascade,
  claim_id       uuid references claims(id) on delete cascade,
  storage_path   text,                       -- Supabase Storage object path
  file_name      text,
  document_type  text,                        -- classified: receipt / discharge_summary
                                              -- / lab_report / prescription / medical_receipt...
  status         document_status not null default 'INCOMPLETE',
  ocr_result     jsonb,                       -- 08: {document_type, confidence, fields, validation_errors}
  confidence     numeric(4,3),                -- overall classification confidence 0..1
  issues         text[] not null default '{}',
  created_at     timestamptz not null default now()
);
create index documents_claim_idx on documents(claim_id);

-- ---------- Assessments (11) ----------
-- One row per agent run; latest row = current assessment for the claim.

create table assessments (
  id                    uuid primary key default gen_random_uuid(),
  tenant_id             uuid not null references tenants(id) on delete cascade,
  claim_id              uuid not null references claims(id) on delete cascade,
  recommendation        recommendation,
  recommendation_reason text,
  report                jsonb,            -- 6-section structured report
  tool_call_log         jsonb,            -- full tool-call trace
  guard_flags           jsonb not null default '{}',  -- deterministic guard results
  created_at            timestamptz not null default now()
);
create index assessments_claim_idx on assessments(claim_id, created_at desc);

-- ---------- Claim transitions / audit trail (14, immutable) ----------

create table claim_transitions (
  id                 bigint generated always as identity primary key,
  tenant_id          uuid not null references tenants(id) on delete cascade,
  claim_id           uuid not null references claims(id) on delete cascade,
  from_state         claim_state,                 -- null for the initial SUBMITTED entry
  to_state           claim_state not null,
  triggered_by       uuid,                        -- acting user id
  triggered_by_role  app_role,
  reason             text,
  notes              text,
  side_effects       jsonb not null default '[]', -- mock side effects that fired
  created_at         timestamptz not null default now()
);
create index claim_transitions_claim_idx on claim_transitions(claim_id, id);

-- Enforce append-only immutability on the audit trail
create trigger claim_transitions_no_update
  before update on claim_transitions
  for each row execute function prevent_mutation();
create trigger claim_transitions_no_delete
  before delete on claim_transitions
  for each row execute function prevent_mutation();
