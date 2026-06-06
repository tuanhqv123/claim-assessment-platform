-- pgvector store for policy-document RAG (Challenge 11 + 15).
-- Embeddings (fastembed bge-small, 384-dim) are stored in Postgres and searched
-- with pgvector cosine distance, so the vector store lives in Supabase rather
-- than a local cache file.

create extension if not exists vector;

create table if not exists policy_chunks (
  id           bigserial primary key,
  tenant_id    uuid references tenants(id) on delete cascade,
  policy_id    text not null,            -- business policy id, e.g. POL-001
  content_hash text not null,            -- sha256 of the source document text
  section      text,                     -- nearest heading for citation context
  chunk_text   text not null,
  embedding    vector(384) not null,
  created_at   timestamptz not null default now()
);

create index if not exists policy_chunks_policy_idx on policy_chunks (policy_id);

-- Cosine similarity search within one policy. query_embedding is passed as text
-- ("[0.1,0.2,...]") and cast to vector so it works cleanly as a PostgREST RPC.
create or replace function match_policy_chunks(
  query_embedding text,
  p_policy_id text,
  match_count int default 4
)
returns table (section text, chunk_text text, score float)
language sql
stable
as $$
  select c.section,
         c.chunk_text,
         1 - (c.embedding <=> query_embedding::vector) as score
  from policy_chunks c
  where c.policy_id = p_policy_id
  order by c.embedding <=> query_embedding::vector
  limit match_count;
$$;
