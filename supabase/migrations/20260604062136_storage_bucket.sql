-- ============================================================================
-- Storage bucket for uploaded claim documents.
-- Public read, 5 MB per-object cap, PNG/PDF only.
-- ============================================================================

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'claim-documents',
  'claim-documents',
  true,
  5242880,                                   -- 5 MB
  array['image/png', 'application/pdf']
)
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Allow the anon role (our publishable key, used by the backend) to upload to
-- and read from this bucket. (Reads also work via the public object URL.)
do $$ begin
  create policy "claim_docs_anon_insert" on storage.objects
    for insert to anon with check (bucket_id = 'claim-documents');
exception when duplicate_object then null; end $$;

do $$ begin
  create policy "claim_docs_anon_select" on storage.objects
    for select to anon using (bucket_id = 'claim-documents');
exception when duplicate_object then null; end $$;
