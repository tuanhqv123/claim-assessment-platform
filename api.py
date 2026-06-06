from __future__ import annotations

import json
import mimetypes
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

from src import db
from src.agent import assess_claim_stream
from src.assessment import run_assessment
from src.guard import apply_guards
from src.stores.document_store import DocumentStore
from src.stores.policy_store import PolicyStore
from src.document_types import match_required_documents
from src.ocr.pipeline import extract_document, extract_document_stream
from src.tenant.config_schema import validate_config
from src.tenant.diff import diff_configs
from src.tenant.runtime import process_claim
from src.workflow.engine import WorkflowEngine, WorkflowError

app = FastAPI(title="Claim Assessment API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per upload
STORAGE_BUCKET = "claim-documents"


def _public_doc_url(storage_path: str | None) -> str | None:
    """Public URL for a stored document. Bucket object paths -> public URL;
    already-a-URL passes through; legacy local 'uploads/...' paths -> None."""
    if not storage_path:
        return None
    if storage_path.startswith("http"):
        return storage_path
    if storage_path.startswith("uploads"):
        return None
    return f"{db.SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{storage_path}"

# One workflow engine for the process; it reads config/workflow.json by default.
_engine = WorkflowEngine()


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _jsonable(value: Any) -> Any:
    """Make dates/datetimes JSON/Supabase-serializable."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def get_active_config(tenant_id: str) -> dict:
    row = db.select_one(
        "tenant_configs",
        filters={"tenant_id": f"eq.{tenant_id}", "is_active": "eq.true"},
    )
    if not row:
        raise HTTPException(404, f"No active config for tenant {tenant_id}")
    return row["config"]


def get_tenant_or_404(tenant_id: str) -> dict:
    row = db.select_one("tenants", filters={"id": f"eq.{tenant_id}"})
    if not row:
        raise HTTPException(404, f"Tenant {tenant_id} not found")
    return row


def get_claim_or_404(claim_id: str) -> dict:
    row = db.select_one("claims", filters={"id": f"eq.{claim_id}"})
    if not row:
        raise HTTPException(404, f"Claim {claim_id} not found")
    return row


def _next_claim_number(tenant_id: str) -> str:
    n = len(
        db.select(
            "claims", columns="id", filters={"tenant_id": f"eq.{tenant_id}"}
        )
    )
    return f"CLM-{n + 1:04d}"


# --------------------------------------------------------------------------- #
# Existing endpoints (kept as-is)
# --------------------------------------------------------------------------- #
class ClaimRequest(BaseModel):
    claim_id: str
    policy_id: str
    member_id: str
    claim_type: str
    sub_benefit: str
    diagnosis_code: str
    diagnosis_description: str
    procedure_codes: list[str]
    amount: float
    claim_date: str
    provider: str
    submitted_document_ids: list[str]


@app.get("/api/claims/examples")
def list_examples():
    claims_dir = Path("data/claims")
    examples = []
    for f in sorted(claims_dir.glob("*.json")):
        examples.append(json.loads(f.read_text()))
    return examples


@app.post("/api/assess")
def assess_claim_endpoint(req: ClaimRequest):
    claim = req.model_dump()

    def event_stream():
        for event in assess_claim_stream(claim):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# --------------------------------------------------------------------------- #
# Multi-tenant config (Challenge 15)
# --------------------------------------------------------------------------- #
@app.get("/api/tenants")
def list_tenants():
    tenants = db.select("tenants", order="created_at.asc")
    out = []
    for t in tenants:
        cfg_row = db.select_one(
            "tenant_configs",
            filters={"tenant_id": f"eq.{t['id']}", "is_active": "eq.true"},
        )
        config = cfg_row["config"] if cfg_row else {}
        out.append(
            {
                "id": t["id"],
                "slug": t["slug"],
                "name": t["name"],
                "config_summary": {
                    "claim_types": config.get("claim_types", []),
                    "auto_approval_threshold": config.get(
                        "auto_approval_threshold"
                    ),
                },
            }
        )
    return out


class TenantCreate(BaseModel):
    slug: str
    name: str
    config: dict


@app.post("/api/tenants")
def create_tenant(body: TenantCreate):
    ok, errors = validate_config(body.config)
    if not ok:
        raise HTTPException(422, detail={"errors": errors})
    tenant = db.insert(
        "tenants", {"slug": body.slug, "name": body.name}
    )[0]
    db.insert(
        "tenant_configs",
        {
            "tenant_id": tenant["id"],
            "version": 1,
            "config": body.config,
            "is_active": True,
        },
    )
    return {"id": tenant["id"], "slug": tenant["slug"], "name": tenant["name"]}


@app.get("/api/tenants/{tenant_id}/config")
def get_tenant_config(tenant_id: str):
    get_tenant_or_404(tenant_id)
    row = db.select_one(
        "tenant_configs",
        filters={"tenant_id": f"eq.{tenant_id}", "is_active": "eq.true"},
    )
    if not row:
        raise HTTPException(404, f"No active config for tenant {tenant_id}")
    return {
        "tenant_id": tenant_id,
        "version": row["version"],
        "config": row["config"],
    }


@app.get("/api/tenants/{tenant_id}/config/versions")
def list_config_versions(tenant_id: str):
    get_tenant_or_404(tenant_id)
    rows = db.select(
        "tenant_configs",
        columns="version,is_active,created_at",
        filters={"tenant_id": f"eq.{tenant_id}"},
        order="version.desc",
    )
    return rows


class ConfigSave(BaseModel):
    config: dict


@app.post("/api/tenants/{tenant_id}/config")
def save_tenant_config(tenant_id: str, body: ConfigSave):
    get_tenant_or_404(tenant_id)
    ok, errors = validate_config(body.config)
    if not ok:
        raise HTTPException(422, detail={"errors": errors})

    versions = db.select(
        "tenant_configs",
        columns="version",
        filters={"tenant_id": f"eq.{tenant_id}"},
        order="version.desc",
        limit=1,
    )
    next_version = (versions[0]["version"] + 1) if versions else 1

    # Deactivate the current active config first (partial unique index allows
    # only one active row per tenant).
    db.update(
        "tenant_configs",
        {"tenant_id": f"eq.{tenant_id}", "is_active": "eq.true"},
        {"is_active": False},
    )
    row = db.insert(
        "tenant_configs",
        {
            "tenant_id": tenant_id,
            "version": next_version,
            "config": body.config,
            "is_active": True,
        },
    )[0]
    return {
        "tenant_id": tenant_id,
        "version": row["version"],
        "config": row["config"],
    }


class Rollback(BaseModel):
    version: int


@app.post("/api/tenants/{tenant_id}/config/rollback")
def rollback_config(tenant_id: str, body: Rollback):
    get_tenant_or_404(tenant_id)
    src_row = db.select_one(
        "tenant_configs",
        filters={
            "tenant_id": f"eq.{tenant_id}",
            "version": f"eq.{body.version}",
        },
    )
    if not src_row:
        raise HTTPException(404, f"Version {body.version} not found")

    versions = db.select(
        "tenant_configs",
        columns="version",
        filters={"tenant_id": f"eq.{tenant_id}"},
        order="version.desc",
        limit=1,
    )
    next_version = (versions[0]["version"] + 1) if versions else 1

    db.update(
        "tenant_configs",
        {"tenant_id": f"eq.{tenant_id}", "is_active": "eq.true"},
        {"is_active": False},
    )
    row = db.insert(
        "tenant_configs",
        {
            "tenant_id": tenant_id,
            "version": next_version,
            "config": src_row["config"],
            "is_active": True,
        },
    )[0]
    return {
        "tenant_id": tenant_id,
        "version": row["version"],
        "config": row["config"],
        "rolled_back_from": body.version,
    }


class PreviewBody(BaseModel):
    claim: dict


@app.post("/api/tenants/{tenant_id}/preview")
def preview_claim(tenant_id: str, body: PreviewBody):
    config = get_active_config(tenant_id)
    try:
        result = process_claim(config, body.claim, date.today())
    except ValueError as exc:
        raise HTTPException(422, detail={"errors": [str(exc)]})
    return _jsonable(result)


@app.get("/api/config/diff")
def config_diff(a: str = Query(...), b: str = Query(...)):
    config_a = get_active_config(a)
    config_b = get_active_config(b)
    return diff_configs(config_a, config_b)


# --------------------------------------------------------------------------- #
# Claims + documents (Challenge 08 + intake)
# --------------------------------------------------------------------------- #
class ClaimCreate(BaseModel):
    tenant_id: str
    claim_number: Optional[str] = None
    policy_number: str
    member_id: str
    claim_type: str
    sub_benefit: Optional[str] = None
    diagnosis_code: Optional[str] = None
    diagnosis_description: Optional[str] = None
    procedure_codes: list[str] = []
    amount: float = 0
    claim_date: Optional[str] = None
    provider: Optional[str] = None
    custom_fields: dict = {}
    submitted_document_ids: list[str] = []


@app.post("/api/claims")
def create_claim(body: ClaimCreate):
    config = get_active_config(body.tenant_id)

    claim_date = body.claim_date or date.today().isoformat()
    submission_date = date.fromisoformat(claim_date)

    # Validate claim_type enabled + custom fields via the tenant runtime.
    try:
        processed = process_claim(
            config,
            {
                "claim_type": body.claim_type,
                "amount": body.amount,
                "custom_fields": body.custom_fields,
            },
            submission_date,
        )
    except ValueError as exc:
        raise HTTPException(422, detail={"errors": [str(exc)]})

    if not processed["custom_fields"]["valid"]:
        raise HTTPException(
            422, detail={"errors": processed["custom_fields"]["errors"]}
        )

    # Resolve policy uuid from policy_number within the tenant.
    policy = db.select_one(
        "policies",
        filters={
            "tenant_id": f"eq.{body.tenant_id}",
            "policy_number": f"eq.{body.policy_number}",
        },
    )

    claim_number = body.claim_number or _next_claim_number(body.tenant_id)

    sla_deadline = processed["sla_deadline"]
    if isinstance(sla_deadline, date):
        sla_deadline = sla_deadline.isoformat()

    claim_row = db.insert(
        "claims",
        {
            "tenant_id": body.tenant_id,
            "claim_number": claim_number,
            "policy_id": policy["id"] if policy else None,
            "member_id": body.member_id,
            "claim_type": body.claim_type,
            "sub_benefit": body.sub_benefit,
            "diagnosis_code": body.diagnosis_code,
            "diagnosis_description": body.diagnosis_description,
            "procedure_codes": body.procedure_codes,
            "amount": body.amount,
            "claim_date": claim_date,
            "provider": body.provider,
            "custom_fields": body.custom_fields,
            "state": "SUBMITTED",
            "sla_deadline": sla_deadline,
        },
    )[0]

    # Initial transition row (from_state null -> SUBMITTED).
    db.insert(
        "claim_transitions",
        {
            "tenant_id": body.tenant_id,
            "claim_id": claim_row["id"],
            "from_state": None,
            "to_state": "SUBMITTED",
            "reason": "claim submitted",
            "side_effects": [],
        },
    )

    claim_row["approval_routing"] = processed["approval_routing"]
    claim_row["required_documents"] = processed["required_documents"]
    return claim_row


@app.post("/api/ocr/extract")
async def ocr_extract(file: UploadFile = File(...)):
    tmp_path = UPLOADS_DIR / f"_preview_{uuid.uuid4().hex}_{file.filename}"
    with tmp_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        result = extract_document(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
    return result


@app.post("/api/ocr/extract/stream")
async def ocr_extract_stream(file: UploadFile = File(...)):
    """SSE stream of the OCR pipeline: emits one event per stage as it completes
    (ocr -> structure -> validate -> done) so the UI can show progress live."""
    tmp_path = UPLOADS_DIR / f"_preview_{uuid.uuid4().hex}_{file.filename}"
    with tmp_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    def event_stream():
        try:
            for ev in extract_document_stream(tmp_path):
                yield f"data: {json.dumps(ev, default=str)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'event': 'error', 'message': str(exc)})}\n\n"
        finally:
            try:
                tmp_path.unlink()
            except OSError:
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/claims/{claim_id}/documents")
async def upload_document(claim_id: str, file: UploadFile = File(...)):
    claim = get_claim_or_404(claim_id)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            detail={"errors": [f"File exceeds the 5 MB limit ({len(content) // 1024} KB)."]},
        )

    object_path = f"{claim_id}/{uuid.uuid4().hex}_{file.filename}"
    content_type = (
        file.content_type
        or mimetypes.guess_type(file.filename or "")[0]
        or "image/png"
    )

    # Store the file in Supabase Storage (public bucket).
    try:
        file_url = db.storage_upload(STORAGE_BUCKET, object_path, content, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, detail={"errors": [f"Storage upload failed: {exc}"]})

    # OCR from a local temp copy (the pipeline needs a file path).
    tmp_path = UPLOADS_DIR / f"_doc_{uuid.uuid4().hex}_{file.filename}"
    with tmp_path.open("wb") as out:
        out.write(content)
    try:
        ocr_result = extract_document(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    confidence = ocr_result.get("confidence")
    document_type = ocr_result.get("document_type")
    validation_errors = ocr_result.get("validation_errors") or []
    status = "COMPLETE" if not validation_errors else "INCOMPLETE"

    row = db.insert(
        "documents",
        {
            "tenant_id": claim["tenant_id"],
            "claim_id": claim_id,
            "storage_path": object_path,
            "file_name": file.filename,
            "document_type": document_type,
            "status": status,
            "ocr_result": ocr_result,
            "confidence": confidence,
            "issues": validation_errors,
        },
    )[0]
    row["file_url"] = file_url
    return row


class DocCheckBody(BaseModel):
    tenant_id: str
    claim_type: str
    uploaded_types: list[str] = []


@app.post("/api/documents/check")
def check_documents(body: DocCheckBody):
    """Match uploaded OCR doc types against a claim type's required/optional docs.

    Lets the member UI show a live ✓/✗ checklist of what is still needed.
    """
    config = get_active_config(body.tenant_id)
    docs_cfg = (config.get("documents") or {}).get(body.claim_type) or {}
    required = docs_cfg.get("required") or []
    optional = docs_cfg.get("optional") or []
    match = match_required_documents(required, optional, body.uploaded_types)
    return {
        "claim_type": body.claim_type,
        "required": required,
        "optional": optional,
        "satisfied": match["satisfied"],
        "missing": match["missing"],
        "mismatches": match["mismatches"],
        "complete": len(match["missing"]) == 0,
    }


@app.get("/api/claims")
def list_claims(
    tenant_id: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
):
    filters: dict[str, str] = {}
    if tenant_id:
        filters["tenant_id"] = f"eq.{tenant_id}"
    if state:
        filters["state"] = f"eq.{state}"
    rows = db.select(
        "claims",
        columns="id,claim_number,tenant_id,claim_type,amount,state,member_id,created_at",
        filters=filters or None,
        order="created_at.desc",
    )
    return rows


@app.get("/api/stats")
def get_stats():
    """Aggregate counts for the dashboard."""
    claims = db.select(
        "claims",
        columns="id,claim_number,tenant_id,claim_type,amount,state,member_id,created_at",
        order="created_at.desc",
    )
    tenants = db.select("tenants", columns="id,slug,name")
    tenant_name = {t["id"]: t["name"] for t in tenants}

    by_state: dict[str, int] = {}
    by_tenant: dict[str, dict] = {}
    total_amount = 0.0
    for c in claims:
        st = c.get("state") or "UNKNOWN"
        by_state[st] = by_state.get(st, 0) + 1
        tid = c.get("tenant_id")
        bt = by_tenant.setdefault(
            tid, {"tenant_id": tid, "name": tenant_name.get(tid, tid), "count": 0}
        )
        bt["count"] += 1
        try:
            total_amount += float(c.get("amount") or 0)
        except (TypeError, ValueError):
            pass

    docs = db.select("documents", columns="id")
    return {
        "total_claims": len(claims),
        "total_documents": len(docs),
        "total_tenants": len(tenants),
        "total_amount": total_amount,
        "by_state": by_state,
        "by_tenant": list(by_tenant.values()),
        "recent": claims[:8],
    }


@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str):
    claim = get_claim_or_404(claim_id)

    documents = db.select(
        "documents",
        filters={"claim_id": f"eq.{claim_id}"},
        order="created_at.asc",
    )
    for d in documents:
        d["file_url"] = _public_doc_url(d.get("storage_path"))
    assessments = db.select(
        "assessments",
        filters={"claim_id": f"eq.{claim_id}"},
        order="created_at.desc",
        limit=1,
    )
    transitions = db.select(
        "claim_transitions",
        filters={"claim_id": f"eq.{claim_id}"},
        order="id.asc",
    )
    available = _engine.available_transitions(claim["state"])

    return {
        "claim": claim,
        "documents": documents,
        "assessment": assessments[0] if assessments else None,
        "transitions": transitions,
        "available_transitions": available,
    }


# --------------------------------------------------------------------------- #
# Assessment (Challenge 11)
# --------------------------------------------------------------------------- #
def _claim_to_agent_dict(claim: dict, documents: list[dict]) -> dict:
    """Map a DB claim row + its documents into the agent's expected shape."""
    policy_number = None
    if claim.get("policy_id"):
        policy = db.select_one(
            "policies", filters={"id": f"eq.{claim['policy_id']}"}
        )
        if policy:
            policy_number = policy["policy_number"]

    doc_ids = [d.get("file_name") or d["id"] for d in documents]

    return {
        "claim_id": claim["claim_number"],
        "policy_id": policy_number or "",
        "member_id": claim.get("member_id") or "",
        "claim_type": claim["claim_type"],
        "sub_benefit": claim.get("sub_benefit") or "",
        "diagnosis_code": claim.get("diagnosis_code") or "",
        "diagnosis_description": claim.get("diagnosis_description") or "",
        "procedure_codes": claim.get("procedure_codes") or [],
        "amount": float(claim.get("amount") or 0),
        "claim_date": claim.get("claim_date") or "",
        "provider": claim.get("provider") or "",
        "submitted_document_ids": doc_ids,
    }


def _policy_store_for(claim: dict) -> Optional[PolicyStore]:
    """Build a PolicyStore from the claim's DB policy so the agent assesses
    against live policy data (and its uploaded document) — not the demo files."""
    if not claim.get("policy_id"):
        return None
    row = db.select_one("policies", filters={"id": f"eq.{claim['policy_id']}"})
    if not row:
        return None
    data = row.get("data") or {}
    pid = data.get("policy_id") or row.get("policy_number")
    if not pid:
        return None
    return PolicyStore(policies={pid: data})


@app.post("/api/claims/{claim_id}/assess")
def assess_claim(claim_id: str):
    claim = get_claim_or_404(claim_id)
    documents = db.select(
        "documents", filters={"claim_id": f"eq.{claim_id}"}
    )
    agent_claim = _claim_to_agent_dict(claim, documents)

    # Build an in-memory document store from the claim's REAL uploaded documents
    # (keyed the same as submitted_document_ids) so the agent's verifyDocument
    # resolves them instead of the legacy file-backed demo store.
    doc_map: dict[str, dict] = {}
    for d in documents:
        key = d.get("file_name") or d["id"]
        doc_map[key] = {
            "document_id": key,
            "document_type": d.get("document_type") or "unknown",
            "status": d.get("status") or "INCOMPLETE",
            "issues": d.get("issues") or [],
        }
    doc_store = DocumentStore(documents=doc_map) if doc_map else None
    policy_store = _policy_store_for(claim)

    result = run_assessment(
        agent_claim, doc_store=doc_store, policy_store=policy_store
    )

    row = db.insert(
        "assessments",
        {
            "tenant_id": claim["tenant_id"],
            "claim_id": claim_id,
            "recommendation": result.get("recommendation"),
            "recommendation_reason": result.get("recommendation_reason"),
            "report": result.get("report"),
            "tool_call_log": result.get("tool_call_log"),
            "guard_flags": result.get("guard_flags") or {},
        },
    )[0]
    return {
        "recommendation": row["recommendation"],
        "recommendation_reason": row["recommendation_reason"],
        "report": row["report"],
        "tool_call_log": row["tool_call_log"],
        "guard_flags": row["guard_flags"],
    }


def _agent_context(claim_id: str):
    """Resolve (claim, agent_claim, doc_store, policy_store) for a DB claim."""
    claim = get_claim_or_404(claim_id)
    documents = db.select("documents", filters={"claim_id": f"eq.{claim_id}"})
    agent_claim = _claim_to_agent_dict(claim, documents)
    doc_map: dict[str, dict] = {}
    for d in documents:
        key = d.get("file_name") or d["id"]
        doc_map[key] = {
            "document_id": key,
            "document_type": d.get("document_type") or "unknown",
            "status": d.get("status") or "INCOMPLETE",
            "issues": d.get("issues") or [],
        }
    doc_store = DocumentStore(documents=doc_map) if doc_map else None
    policy_store = _policy_store_for(claim)
    return claim, agent_claim, doc_store, policy_store


@app.post("/api/claims/{claim_id}/assess/stream")
def assess_claim_stream_endpoint(claim_id: str):
    """SSE stream of the assessment: emits each tool call (lookupPolicy ->
    verifyDocument -> checkMedicalNecessity -> calculateBenefit) live, then a
    final guarded result (also persisted). Lets the UI show reasoning step by
    step instead of reloading."""
    claim, agent_claim, doc_store, policy_store = _agent_context(claim_id)

    def event_stream():
        final: dict = {}
        try:
            for ev in assess_claim_stream(
                agent_claim, doc_store=doc_store, policy_store=policy_store
            ):
                if ev.get("type") == "step":
                    yield "data: " + json.dumps(
                        {"event": "step", "tool": ev.get("node"), "data": ev.get("data")},
                        default=str,
                    ) + "\n\n"
                elif ev.get("type") == "done":
                    final = ev.get("final_result") or {}
            guarded = apply_guards(agent_claim, final)
            row = db.insert(
                "assessments",
                {
                    "tenant_id": claim["tenant_id"],
                    "claim_id": claim_id,
                    "recommendation": guarded.get("recommendation"),
                    "recommendation_reason": guarded.get("recommendation_reason"),
                    "report": guarded.get("report"),
                    "tool_call_log": guarded.get("tool_call_log"),
                    "guard_flags": guarded.get("guard_flags") or {},
                },
            )[0]
            yield "data: " + json.dumps(
                {
                    "event": "done",
                    "result": {
                        "recommendation": row["recommendation"],
                        "recommendation_reason": row["recommendation_reason"],
                        "report": row["report"],
                        "tool_call_log": row["tool_call_log"],
                        "guard_flags": row["guard_flags"],
                    },
                },
                default=str,
            ) + "\n\n"
        except Exception as exc:  # noqa: BLE001
            yield "data: " + json.dumps({"event": "error", "message": str(exc)}) + "\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- #
# Policies & members (admin) — Challenge 15 / RAG corpus
# --------------------------------------------------------------------------- #
POLICY_BUCKET = "claim-documents"  # reuse the existing storage bucket


def get_policy_or_404(policy_id: str) -> dict:
    row = db.select_one("policies", filters={"id": f"eq.{policy_id}"})
    if not row:
        raise HTTPException(404, f"Policy {policy_id} not found")
    return row


def _reindex_policy(row: dict) -> int:
    """(Re)build the RAG index for a policy row. Returns chunk count."""
    from src.rag import service

    data = row.get("data") or {}
    pid = data.get("policy_id") or row.get("policy_number")
    return (
        service.ensure_indexed(pid, data, tenant_id=row.get("tenant_id"))
        if pid
        else 0
    )


def _policy_summary(row: dict) -> dict:
    data = row.get("data") or {}
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "policy_number": row.get("policy_number"),
        "policyholder_name": data.get("policyholder_name"),
        "policyholder_type": data.get("policyholder_type"),
        "status": data.get("status"),
        "effective_date": data.get("effective_date"),
        "expiry_date": data.get("expiry_date"),
        "benefits": [
            {"type": b.get("type"), "annual_limit": b.get("annual_limit")}
            for b in data.get("benefits", []) or []
        ],
        "member_count": len(data.get("member_ids", []) or []),
        "member_ids": data.get("member_ids", []) or [],
        "has_document": bool((data.get("terms_document") or "").strip()),
    }


def _extract_policy_text(filename: str, content_type: str, content: bytes) -> str:
    """Get layout-aware text from an uploaded policy file.

    Text/markdown files are decoded directly. Images and PDFs go through the
    dots.ocr layout reader (PDFs are rasterized page by page), preserving
    headings, tables and section boundaries so the RAG corpus keeps the
    document's real structure and context.
    """
    name = (filename or "").lower()
    if name.endswith((".txt", ".md")) or (content_type or "").startswith("text/"):
        return content.decode("utf-8", errors="replace")
    tmp_path = UPLOADS_DIR / f"_policy_{uuid.uuid4().hex}_{filename}"
    tmp_path.write_bytes(content)
    try:
        from src.ocr.document_text import extract_document_text

        return extract_document_text(tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


@app.get("/api/tenants/{tenant_id}/policies")
def list_policies(tenant_id: str):
    get_tenant_or_404(tenant_id)
    rows = db.select(
        "policies",
        filters={"tenant_id": f"eq.{tenant_id}"},
        order="policy_number.asc",
    )
    return [_policy_summary(r) for r in rows]


@app.get("/api/policies/{policy_id}")
def get_policy(policy_id: str):
    from src.rag import service

    row = get_policy_or_404(policy_id)
    data = row.get("data") or {}
    pid = data.get("policy_id") or row.get("policy_number")
    document_text = service.document_text_for(data)
    clause_count = (
        service.ensure_indexed(pid, data, tenant_id=row.get("tenant_id"))
        if pid
        else 0
    )
    return {
        **_policy_summary(row),
        "data": data,
        "member_ids": data.get("member_ids", []) or [],
        "exclusions": data.get("exclusions", []) or [],
        "document_text": document_text,
        "document_uploaded": bool((data.get("terms_document") or "").strip()),
        "document_url": data.get("terms_document_url"),
        "clause_count": clause_count,
    }


class PolicyCreate(BaseModel):
    policy_number: str
    data: dict


@app.post("/api/tenants/{tenant_id}/policies")
def create_policy(tenant_id: str, body: PolicyCreate):
    get_tenant_or_404(tenant_id)
    data = dict(body.data or {})
    data.setdefault("policy_id", body.policy_number)
    data.setdefault("status", "ACTIVE")
    data.setdefault("member_ids", [])
    row = db.insert(
        "policies",
        {"tenant_id": tenant_id, "policy_number": body.policy_number, "data": data},
    )[0]
    _reindex_policy(row)
    return _policy_summary(row)


class PolicyUpdate(BaseModel):
    data: dict


@app.put("/api/policies/{policy_id}")
def update_policy(policy_id: str, body: PolicyUpdate):
    row = get_policy_or_404(policy_id)
    merged = {**(row.get("data") or {}), **(body.data or {})}
    updated = db.update("policies", {"id": f"eq.{policy_id}"}, {"data": merged})[0]
    _reindex_policy(updated)
    return _policy_summary(updated)


@app.delete("/api/policies/{policy_id}")
def delete_policy(policy_id: str):
    get_policy_or_404(policy_id)
    db.delete("policies", {"id": f"eq.{policy_id}"})
    return {"deleted": policy_id}


@app.post("/api/policies/{policy_id}/document")
async def upload_policy_document(policy_id: str, file: UploadFile = File(...)):
    """Admin uploads the signed policy document. We store the file, extract its
    text (the RAG corpus) and re-index it for semantic clause retrieval."""
    row = get_policy_or_404(policy_id)
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            413,
            detail={"errors": [f"File exceeds the 5 MB limit ({len(content) // 1024} KB)."]},
        )

    object_path = f"policies/{policy_id}/{uuid.uuid4().hex}_{file.filename}"
    content_type = (
        file.content_type
        or mimetypes.guess_type(file.filename or "")[0]
        or "application/octet-stream"
    )
    # Best-effort store of the original file: the bucket only allows image/pdf
    # mimes, so plain-text uploads keep their extracted text but no file URL.
    document_url = None
    try:
        db.storage_upload(POLICY_BUCKET, object_path, content, content_type)
        document_url = _public_doc_url(object_path)
    except db.SupabaseError:
        document_url = None

    text = _extract_policy_text(file.filename or "", content_type, content)
    data = {**(row.get("data") or {})}
    data["terms_document"] = text
    data["terms_document_url"] = document_url
    data["terms_document_name"] = file.filename
    updated = db.update("policies", {"id": f"eq.{policy_id}"}, {"data": data})[0]
    chunks = _reindex_policy(updated)
    return {
        **_policy_summary(updated),
        "document_url": document_url,
        "document_chars": len(text),
        "clause_count": chunks,
    }


class MemberBody(BaseModel):
    member_id: str


@app.post("/api/policies/{policy_id}/members")
def add_member(policy_id: str, body: MemberBody):
    row = get_policy_or_404(policy_id)
    data = {**(row.get("data") or {})}
    members = list(data.get("member_ids", []) or [])
    mid = body.member_id.strip()
    if not mid:
        raise HTTPException(400, detail={"error": "member_id is required"})
    if mid in members:
        raise HTTPException(409, detail={"error": f"{mid} is already a member"})
    members.append(mid)
    data["member_ids"] = members
    db.update("policies", {"id": f"eq.{policy_id}"}, {"data": data})
    return {"member_ids": members}


@app.delete("/api/policies/{policy_id}/members/{member_id}")
def remove_member(policy_id: str, member_id: str):
    row = get_policy_or_404(policy_id)
    data = {**(row.get("data") or {})}
    members = [m for m in (data.get("member_ids", []) or []) if m != member_id]
    data["member_ids"] = members
    db.update("policies", {"id": f"eq.{policy_id}"}, {"data": data})
    return {"member_ids": members}


# --------------------------------------------------------------------------- #
# Members directory (insured persons, per tenant)
# --------------------------------------------------------------------------- #
# A lightweight people-directory. Distinct from the policy roster above (which
# is just member-id tags on a policy) and from `profiles` (staff accounts).
def get_member_or_404(member_id: str) -> dict:
    row = db.select_one("members", filters={"id": f"eq.{member_id}"})
    if not row:
        raise HTTPException(404, f"Member {member_id} not found")
    return row


def _member_summary(row: dict) -> dict:
    return {
        "id": row["id"],
        "tenant_id": row["tenant_id"],
        "member_code": row.get("member_code"),
        "full_name": row.get("full_name"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "status": row.get("status"),
        "note": row.get("note"),
    }


class MemberCreate(BaseModel):
    member_code: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: str = "ACTIVE"
    note: Optional[str] = None


class MemberUpdate(BaseModel):
    member_code: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None


@app.get("/api/tenants/{tenant_id}/members")
def list_members(tenant_id: str):
    get_tenant_or_404(tenant_id)
    rows = db.select(
        "members",
        filters={"tenant_id": f"eq.{tenant_id}"},
        order="member_code.asc",
    )
    return [_member_summary(r) for r in rows]


@app.post("/api/tenants/{tenant_id}/members")
def create_member(tenant_id: str, body: MemberCreate):
    get_tenant_or_404(tenant_id)
    code = body.member_code.strip()
    name = body.full_name.strip()
    if not code or not name:
        raise HTTPException(400, detail={"error": "member_code and full_name are required"})
    existing = db.select(
        "members",
        columns="id",
        filters={"tenant_id": f"eq.{tenant_id}", "member_code": f"eq.{code}"},
        limit=1,
    )
    if existing:
        raise HTTPException(409, detail={"error": f"Member code {code} already exists for this tenant"})
    row = db.insert(
        "members",
        {
            "tenant_id": tenant_id,
            "member_code": code,
            "full_name": name,
            "email": body.email,
            "phone": body.phone,
            "status": body.status or "ACTIVE",
            "note": body.note,
        },
    )[0]
    return _member_summary(row)


@app.get("/api/members/{member_id}")
def get_member(member_id: str):
    return _member_summary(get_member_or_404(member_id))


@app.put("/api/members/{member_id}")
def update_member(member_id: str, body: MemberUpdate):
    row = get_member_or_404(member_id)
    values = {k: v for k, v in body.model_dump().items() if v is not None}
    if "member_code" in values:
        code = values["member_code"].strip()
        clash = db.select(
            "members",
            columns="id",
            filters={
                "tenant_id": f"eq.{row['tenant_id']}",
                "member_code": f"eq.{code}",
                "id": f"neq.{member_id}",
            },
            limit=1,
        )
        if clash:
            raise HTTPException(409, detail={"error": f"Member code {code} already exists for this tenant"})
        values["member_code"] = code
    if not values:
        return _member_summary(row)
    updated = db.update("members", {"id": f"eq.{member_id}"}, values)[0]
    return _member_summary(updated)


@app.delete("/api/members/{member_id}")
def delete_member(member_id: str):
    get_member_or_404(member_id)
    db.delete("members", {"id": f"eq.{member_id}"})
    return {"deleted": member_id}


# --------------------------------------------------------------------------- #
# Workflow (Challenge 14)
# --------------------------------------------------------------------------- #
def _hydrate_engine_claim(claim: dict):
    """Build an engine Claim handle seeded with the DB state + cycle count."""
    handle = _engine.new_claim(claim["id"], state=claim["state"])
    record = _engine._record(claim["id"])
    record.info_request_count = claim.get("info_request_count") or 0
    return handle


@app.get("/api/claims/{claim_id}/transitions")
def get_transitions(claim_id: str):
    claim = get_claim_or_404(claim_id)
    audit = db.select(
        "claim_transitions",
        filters={"claim_id": f"eq.{claim_id}"},
        order="id.asc",
    )
    return {
        "current_state": claim["state"],
        "audit": audit,
        "available": _engine.available_transitions(claim["state"]),
    }


class TransitionBody(BaseModel):
    to_state: str
    reason: Optional[str] = None
    notes: Optional[str] = None
    context: dict = {}


def _precondition_context(claim: dict, reason: Optional[str]) -> dict:
    """Derive the workflow precondition facts from the claim's REAL state.

    Preconditions like ``all_required_documents_present`` are facts about the
    claim, not free-form input the caller should assert. We compute them here so
    a transition is allowed exactly when its real-world condition holds (e.g.
    documents actually present, an assessment actually exists), instead of
    relying on the UI to hand us a context dict it has no way to populate.
    """
    claim_id = claim["id"]

    # Documents present? Compare uploaded OCR types against the claim type's
    # required docs from the tenant config. No required docs => nothing missing.
    documents = db.select("documents", filters={"claim_id": f"eq.{claim_id}"})
    all_docs_present = True
    try:
        config = get_active_config(claim["tenant_id"])
        docs_cfg = (config.get("documents") or {}).get(claim["claim_type"]) or {}
        required = docs_cfg.get("required") or []
        optional = docs_cfg.get("optional") or []
        uploaded_types = [d.get("document_type") for d in documents if d.get("document_type")]
        match = match_required_documents(required, optional, uploaded_types)
        all_docs_present = not match.get("missing")
    except HTTPException:
        pass  # no active config -> treat as nothing required

    # Assessment done? amount_within_limit follows the guarded recommendation
    # (APPROVE means the agent/guard cleared it against the policy limit).
    _assessments = db.select(
        "assessments",
        filters={"claim_id": f"eq.{claim_id}"},
        order="created_at.desc",
        limit=1,
    )
    assessment = _assessments[0] if _assessments else None
    recommendation = (assessment or {}).get("recommendation")

    has_reason = bool(reason and reason.strip())
    return {
        "all_required_documents_present": all_docs_present,
        "assessor_assigned": True,
        "assessment_complete": assessment is not None,
        "amount_within_limit": recommendation == "APPROVE",
        "rejection_reason_provided": has_reason,
        "missing_info_description_provided": has_reason,
        "new_info_received": bool(documents),
        # Operational acknowledgements: an authorized actor triggering the step
        # IS the acknowledgement in this demo (real systems wire these to the
        # payment gateway / appeal timer).
        "payment_request_created": True,
        "payment_confirmed": True,
        "appeal_period_expired_or_acknowledged": True,
        "escalation_resolved": True,
    }


@app.post("/api/claims/{claim_id}/transition")
def do_transition(
    claim_id: str,
    body: TransitionBody,
    x_role: Optional[str] = Header(default=None, alias="X-Role"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
):
    claim = get_claim_or_404(claim_id)

    if not x_role:
        raise HTTPException(400, detail={"error": "X-Role header is required"})

    # Compute precondition facts from real state; let an explicit caller context
    # override (e.g. a manager forcing an approval).
    context = {**_precondition_context(claim, body.reason), **(body.context or {})}

    handle = _hydrate_engine_claim(claim)
    try:
        _engine.transition(
            handle,
            to_state=body.to_state,
            actor_role=x_role,
            context=context,
            actor_id=x_user_id,
            reason=body.reason,
            notes=body.notes,
        )
    except WorkflowError as exc:
        raise HTTPException(400, detail={"error": str(exc)})

    audit_entry = _engine.audit_trail(handle)[-1]
    new_state = handle.state
    record = _engine._record(claim_id)

    # Persist new state + cycle count on the claim.
    db.update(
        "claims",
        {"id": f"eq.{claim_id}"},
        {
            "state": new_state,
            "info_request_count": record.info_request_count,
        },
    )

    triggered_by = audit_entry["triggered_by"]
    transition_row = db.insert(
        "claim_transitions",
        {
            "tenant_id": claim["tenant_id"],
            "claim_id": claim_id,
            "from_state": audit_entry["from_state"],
            "to_state": audit_entry["to_state"],
            "triggered_by": triggered_by.get("id"),
            "triggered_by_role": triggered_by.get("role"),
            "reason": audit_entry.get("reason"),
            "notes": audit_entry.get("notes"),
            "side_effects": audit_entry.get("side_effects", []),
        },
    )[0]

    return {"state": new_state, "audit_entry": transition_row}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
