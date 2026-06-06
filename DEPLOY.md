# Deploy — single public port

The whole stack runs behind **one exposed port**. A Caddy reverse proxy is the
only service that publishes a port; it routes:

- `/api/*` → FastAPI backend (assessment agent, OCR, RAG, workflow)
- everything else → Next.js frontend

The backend and frontend talk over the internal Docker network and are **not**
reachable from outside.

```
            host:${HTTP_PORT}              (the only open port)
                  │
               ┌──┴───┐
               │ caddy│  :80
               └──┬───┘
        /api/* ┌──┴──┐ /*
          ┌────┘     └────┐
     ┌────┴────┐     ┌────┴───┐
     │ backend │     │  web   │
     │  :8000  │     │ :3000  │
     └─────────┘     └────────┘
```

## Prerequisites

- Docker + Docker Compose v2
- **GPU build only:** NVIDIA driver + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  on the host (so the container can see the CUDA GPU)
- A populated `./.env` (LLM, OCR, Supabase creds — already present in this repo)

## Run

```bash
# from claim-assessment-agent/
HTTP_PORT=8080 docker compose up -d --build
```

Open `http://<server>:8080`. That's it — one port.

To change the public port, set `HTTP_PORT` (e.g. `HTTP_PORT=80 docker compose up -d`).

## GPU vs CPU embeddings

The only local model is the **bge-small-en-v1.5** embedder (384-dim) used for
policy-clause RAG. The LLM and OCR are remote endpoints (see `.env`).

- **GPU (default):** `backend` builds from `Dockerfile.gpu` (CUDA 12.4 + cuDNN 9,
  `fastembed-gpu`). The embedder runs on `CUDAExecutionProvider` and falls back
  to CPU if CUDA can't load (`EMBED_PROVIDERS` env). The compose file reserves
  one NVIDIA GPU for the backend.
- **CPU:** in `docker-compose.yml` set the backend `dockerfile:` to `Dockerfile`
  and delete the backend `deploy.resources` GPU block. No toolkit needed.

> Note: the embedding workload here is small (a handful of policy docs + one
> query per assessment), so the GPU is nice-to-have, not a bottleneck. CPU works
> fine if the GPU path gives any trouble.

## Env vars

| Var | Where | Purpose |
|-----|-------|---------|
| `HTTP_PORT` | compose | host port for Caddy (default 8080) |
| `OPENAI_*` | `.env` | LLM endpoint for the agent / report / OCR structuring |
| `OCR_*` | `.env` | dots.ocr vLLM endpoint |
| `SUPABASE_*` | `.env` | Postgres + pgvector + storage |
| `EMBED_PROVIDERS` | image (GPU) | ONNX execution providers, e.g. `CUDAExecutionProvider,CPUExecutionProvider` |

`NEXT_PUBLIC_API_URL` is baked **empty** into the web image so the browser calls
same-origin `/api/...` paths through Caddy — no per-deploy frontend rebuild for a
new hostname.

## Ops

```bash
docker compose logs -f backend   # agent / OCR / RAG logs
docker compose logs -f caddy     # routing
docker compose ps
docker compose down              # stop (add -v to drop caddy volumes)
```

## Notes

- Schema/migrations live in Supabase (hosted). Apply new ones with
  `supabase db push` from your machine — not part of the container build.
- The backend image pre-downloads the bge-small model at build time, so first
  request is fast and runtime needs no HuggingFace access.
