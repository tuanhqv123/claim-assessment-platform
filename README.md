# Claim Assessment AI Platform

A multi-tenant health-insurance **claims platform** built around an LLM **claim-assessment agent**. A member uploads a receipt, OCR extracts it, a state-machine drives the claim lifecycle, and an AI agent — backed by **RAG over the policy document** and a **deterministic guard layer** — produces an auditable APPROVE / REJECT / REQUEST_MORE_INFO recommendation that a human assessor finalizes.

> **Challenge:** This started as **Papaya AI Challenge 11 — Claim Assessment AI Agent** (the adjudication step) and was deliberately expanded into an integrated platform that also covers challenges **08**, **14**, and **15**.

---

## 1. Which parts of the brief are implemented

| Challenge | Scope | Where |
|-----------|-------|-------|
| **11 — Claim Assessment Agent** *(core)* | Tool-calling LLM agent: policy lookup, document verification, medical-necessity check, benefit calculation → recommendation + cited report. Deterministic **guard layer** backstops money/limits/eligibility. | `src/agent.py`, `src/guard.py`, `src/assessment.py`, `src/nodes/` |
| **08 — Upload + OCR** | Member uploads receipt/PDF → **layout-aware OCR** (dots.ocr) → structured fields + confidence + validation errors → drives the document checklist. | `src/ocr/`, `POST /api/ocr/extract`, `POST /api/claims/{id}/documents` |
| **14 — Claims Workflow** | State machine (SUBMITTED → DOCUMENTS_VERIFIED → UNDER_ASSESSMENT → …), preconditions computed from real claim state, role-based transitions, immutable **audit trail**, cycle detection. | `src/workflow/`, `config/workflow.json`, `claim_transitions` table |
| **15 — Multi-Tenant Config** | Per-insurer (tenant) config: claim types, approval thresholds, required documents, custom fields, SLA; versioning + diff + preview; same claim → different behavior per tenant. | `src/tenant/`, `/admin` config tab, `tenant_configs` |

Out of scope: fraud (10), cross-border law (12), partner SDK (13).

---

## 2. Features

- **Member portal** — pick insurer, upload documents (auto-OCR + prefill), submit a claim; **policy & member chosen from dropdowns** (member list filtered to those enrolled in the selected policy).
- **OCR pipeline** — dots.ocr layout mode (headings/tables/reading order preserved) + a structuring LLM pass → typed fields, per-field confidence, validation errors (e.g. receipt total mismatch). PDFs rasterized page-by-page via poppler.
- **Assessment agent** — OpenAI-compatible tool-calling loop with 5 tools (`lookupPolicy`, `verifyDocument`, `checkMedicalNecessity`, `calculateBenefit`, `retrievePolicyClauses`). Every recommendation cites specific policy clauses.
- **RAG over policy documents** — the insurer uploads the policy document; it is OCR'd, chunked by section, embedded locally (**fastembed / bge-small**) and stored in **Supabase pgvector**. The agent retrieves clauses (exclusions, "medically necessary", conditions) at assessment time.
- **Deterministic guard layer** — overrides the LLM when it must: missing required docs → REQUEST_MORE_INFO; over-limit/denied → REJECT; **member not enrolled in the policy → REJECT** (eligibility backstop), regardless of what the LLM concluded.
- **Workflow + audit** — lifecycle state machine with role checks and an immutable transition log.
- **Multi-tenant admin** — manage tenants, **policies** (CRUD + upload policy document + member roster), a **members directory**, and tenant configuration (versioned, with diff/preview).
- **Assessor queue** — review the agent's report, override, and finalize; full streaming (SSE) of the assessment reasoning.

---

## 3. Architecture

### System

```
                       ┌──────────────────────────────┐
                       │  Frontend — Next.js (Vercel)  │
                       │  member · assessor · admin    │
                       └───────────────┬──────────────┘
                                       │ HTTPS  /api/*
                                       ▼
                       ┌──────────────────────────────┐
                       │   Backend — FastAPI (api.py)  │
                       ├──────────────────────────────┤
   upload ─OCR──────►  │  OCR pipeline (dots.ocr)      │ ──► dots.ocr (vLLM, vision)
                       │  Workflow engine (state+audit)│
   assess ──────────►  │  Assessment agent + Guard     │ ──► LLM (OpenAI-compatible)
                       │  RAG service (retrieve)       │ ──► fastembed (bge, local/GPU)
                       │  Tenant runtime / config      │
                       └───────────────┬──────────────┘
                                       │ PostgREST / RPC / Storage
                                       ▼
                       ┌──────────────────────────────┐
                       │  Supabase: Postgres + pgvector│
                       │  tenants · policies · claims  │
                       │  documents · assessments      │
                       │  members · policy_chunks      │
                       │  claim_transitions (audit)    │
                       └──────────────────────────────┘
```

### Layers (backend)

| Layer | Responsibility | Modules |
|-------|----------------|---------|
| **API** | HTTP/SSE endpoints, request/response shaping, CORS | `api.py` |
| **Domain / orchestration** | Run the agent then apply guards; thread DB-backed stores | `src/assessment.py` |
| **Agent** | Tool-calling LLM loop + tool implementations | `src/agent.py`, `src/nodes/` |
| **Guard** | Deterministic safety overrides (docs, limits, **eligibility**) | `src/guard.py` |
| **RAG** | Chunk → embed → store → retrieve policy clauses | `src/rag/` (`embedder`, `chunker`, `store`, `service`, `policy_document`) |
| **OCR** | Layout OCR + structuring + validation | `src/ocr/` (`dots_client`, `document_text`, `structurer`, `pipeline`, `validation`) |
| **Workflow** | State machine, preconditions, audit, cycle detection | `src/workflow/` |
| **Tenant** | Config schema, validation, diff, runtime `processClaim` | `src/tenant/` |
| **Data access** | Supabase REST / RPC / Storage; config | `src/db.py`, `src/config.py`, `src/stores/` |

### End-to-end flow

```
Member uploads receipt ─► OCR (08) ─► fields + confidence ─► create claim
        │                                                        │
        ▼                                                        ▼
   documents table                              Workflow (14): SUBMITTED → DOCUMENTS_VERIFIED
                                                                 │ → UNDER_ASSESSMENT
                                                                 ▼
                              Assessment agent (11): lookupPolicy · verifyDocument ·
                              checkMedicalNecessity · calculateBenefit · retrievePolicyClauses (RAG)
                                                                 │
                                                Guard layer: docs / limits / eligibility backstop
                                                                 │
                                       recommendation + cited report  ─►  Assessor finalizes (audit)
```
Required documents, approval tiers and custom fields all come from the **tenant config (15)**, so the *same* claim is processed differently per insurer.

---

## 4. Tech stack

- **Backend:** Python 3.12, FastAPI, OpenAI-compatible LLM client, **fastembed** (bge-small-en-v1.5, ONNX — CPU or CUDA), **dots.ocr** (vision OCR via vLLM), poppler (`pdftoppm`).
- **Frontend:** Next.js 16 (App Router), React 19, Ant Design 6, TypeScript.
- **Data:** Supabase — Postgres + **pgvector** + Storage.
- **Infra:** Docker / Docker Compose, Caddy (single-port reverse proxy), Vercel (frontend).

---

## 5. Repository layout

```
api.py                      FastAPI app (all endpoints)
src/
  agent.py  assessment.py   tool-calling agent + orchestration
  guard.py                  deterministic guard layer (incl. eligibility backstop)
  config.py  db.py          env (require_env) + Supabase access
  ocr/                      layout OCR + structuring + validation
  rag/                      chunk / embed / pgvector store / retrieve
  workflow/                 state machine + audit
  tenant/                   multi-tenant config schema / runtime
  nodes/  stores/           agent tool internals + data stores
config/workflow.json        workflow state machine definition
supabase/migrations/        Postgres + pgvector schema (incl. medical_codes,
                            policies, members — all reference/data lives in DB)
web/                        Next.js frontend (member / assessor / admin)
Dockerfile(.gpu)            backend images (CPU / CUDA)
docker-compose*.yml         single-port stack / backend-only deploy
DEPLOY.md                   deployment guide
```

---

## 6. Setup (local)

### Prerequisites
- Python 3.12, Node 20+, poppler (`pdftoppm`), a Supabase project, and reachable LLM + OCR endpoints.

### a. Configure secrets
```bash
cp .env.example .env        # then fill in the values below
```
| Var | Purpose |
|-----|---------|
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | LLM (agent, report, OCR structuring) |
| `OCR_BASE_URL` / `OCR_MODEL` | dots.ocr endpoint |
| `SUPABASE_URL` / `SUPABASE_PUBLISHABLE_KEY` (or service-role) | DB + pgvector + storage |
| `EMBED_PROVIDERS` *(optional)* | e.g. `CUDAExecutionProvider,CPUExecutionProvider` to run embeddings on GPU |

> Nothing is hardcoded in source — every endpoint/model/key is read from the environment via `src/config.py:require_env`.

### b. Database
```bash
supabase link --project-ref <ref>
supabase db push            # applies supabase/migrations/*
```

### c. Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-server.txt        # use requirements-server-gpu.txt for CUDA
uvicorn api:app --host 0.0.0.0 --port 8000
```

### d. Frontend
```bash
cd web
npm install
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev                 # http://localhost:3000
```

Open `http://localhost:3000` → **Member** (submit a claim), **Assessor** (review/finalize), **Admin** (tenants, policies, members, config).

---

## 7. Deployment

See **[DEPLOY.md](DEPLOY.md)**. Two supported shapes:

- **Single public port** — `docker compose up -d` runs backend + frontend behind one Caddy port (`/api/*` → FastAPI, else → Next.js). GPU (`Dockerfile.gpu`) or CPU (`Dockerfile`).
- **Split** — frontend on **Vercel** (`NEXT_PUBLIC_API_URL` = backend URL), backend via `docker-compose.backend.yml` (GPU box). HTTPS without a domain is possible via a Cloudflare tunnel.

---

## 8. Key design decisions

- **Deterministic guard over the LLM** — money, limits and *enrollment* are compliance-critical, so they are guaranteed in code (`guard.py` + the eligibility backstop in `assessment.py`), not left to LLM probability. The LLM writes the *reasoning*; the guard owns the *verdict's hard constraints*.
- **RAG only where it helps** — numbers/limits are structured lookups; long prose (exclusions, definitions) is retrieved semantically from the actual policy document.
- **Real-world framing** — the insurer *uploads the policy document* (the rules) ↔ the member *uploads the receipt* (the evidence); assessment = matching evidence to rules.
- **Secrets only in env** — no IPs/models/keys in source; `.env` is git-ignored.
