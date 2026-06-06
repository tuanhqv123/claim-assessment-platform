-- Members directory (insured persons) per tenant.
-- A lightweight people-directory: name + contact + status, scoped to a tenant.
-- Policy assignment stays in policies.data.member_ids (assessment reads that),
-- so this table does NOT reference policies and does not change adjudication.

create table if not exists members (
  id           uuid primary key default gen_random_uuid(),
  tenant_id    uuid not null references tenants(id) on delete cascade,
  member_code  text not null,                    -- e.g. MBR-001
  full_name    text not null,
  email        text,
  phone        text,
  status       text not null default 'ACTIVE',   -- ACTIVE | INACTIVE
  note         text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  unique (tenant_id, member_code)
);

create index if not exists members_tenant_idx on members(tenant_id);

create trigger members_set_updated_at
  before update on members
  for each row execute function set_updated_at();

-- Backfill the directory from member ids already embedded in policies, so the
-- new page isn't empty on day one. Placeholder names; admins can edit later.
insert into members (tenant_id, member_code, full_name, status)
select p.tenant_id,
       mid as member_code,
       'Member ' || mid as full_name,
       'ACTIVE'
from policies p,
     lateral jsonb_array_elements_text(coalesce(p.data->'member_ids', '[]'::jsonb)) as mid
on conflict (tenant_id, member_code) do nothing;
