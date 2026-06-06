"""Thin Supabase REST (PostgREST) client built on httpx.

Talks to ``{SUPABASE_URL}/rest/v1`` with the publishable (or service-role) key.
No RLS is assumed; tenant-scoping is enforced by the application layer.

Each helper returns parsed JSON (a list for selects, a dict/list for writes
with ``return=representation``). On a non-2xx response a ``SupabaseError`` is
raised carrying the status code and the PostgREST error body, so callers can
surface a clear message (e.g. "service_role key required" on 401/403).
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
# Prefer service-role if present (full write access, bypasses RLS), else the
# publishable/anon key. The contract uses the publishable key by design.
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
)

REST_URL = f"{SUPABASE_URL}/rest/v1"


class SupabaseError(Exception):
    """A non-2xx response from PostgREST."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Supabase REST error {status_code}: {body}")


def _headers(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Profile": "public",
        "Accept-Profile": "public",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _client() -> httpx.Client:
    return httpx.Client(base_url=REST_URL, timeout=30.0)


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.status_code >= 300:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise SupabaseError(resp.status_code, body)


def _parse(resp: httpx.Response) -> Any:
    if resp.status_code == 204 or not resp.content:
        return []
    try:
        return resp.json()
    except Exception:
        return resp.text


def select(
    table: str,
    *,
    columns: str = "*",
    filters: Optional[dict[str, str]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict]:
    """SELECT rows from ``table``.

    ``filters`` maps a column to a PostgREST operator string, e.g.
    ``{"tenant_id": "eq.<uuid>", "state": "eq.SUBMITTED"}``.
    """
    params: dict[str, Any] = {"select": columns}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = str(limit)
    with _client() as client:
        resp = client.get(f"/{table}", params=params, headers=_headers())
    _raise_for_status(resp)
    return _parse(resp)


def insert(table: str, rows: dict | list[dict]) -> list[dict]:
    """INSERT one row (dict) or many (list); returns the inserted rows."""
    with _client() as client:
        resp = client.post(
            f"/{table}",
            json=rows,
            headers=_headers({"Prefer": "return=representation"}),
        )
    _raise_for_status(resp)
    return _parse(resp)


def update(table: str, filters: dict[str, str], values: dict) -> list[dict]:
    """UPDATE rows matching ``filters`` (PostgREST operator strings)."""
    with _client() as client:
        resp = client.patch(
            f"/{table}",
            params=filters,
            json=values,
            headers=_headers({"Prefer": "return=representation"}),
        )
    _raise_for_status(resp)
    return _parse(resp)


def delete(table: str, filters: dict[str, str]) -> list[dict]:
    """DELETE rows matching ``filters`` (PostgREST operator strings)."""
    with _client() as client:
        resp = client.request(
            "DELETE",
            f"/{table}",
            params=filters,
            headers=_headers({"Prefer": "return=representation"}),
        )
    _raise_for_status(resp)
    return _parse(resp)


def rpc(fn: str, params: dict) -> Any:
    """Call a Postgres function via PostgREST (`POST /rpc/<fn>`)."""
    with _client() as client:
        resp = client.post(f"/rpc/{fn}", json=params, headers=_headers())
    _raise_for_status(resp)
    return _parse(resp)


def upsert(
    table: str,
    rows: dict | list[dict],
    *,
    on_conflict: Optional[str] = None,
) -> list[dict]:
    """UPSERT rows. ``on_conflict`` names the unique column(s) to merge on."""
    params: dict[str, Any] = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    with _client() as client:
        resp = client.post(
            f"/{table}",
            params=params,
            json=rows,
            headers=_headers(
                {"Prefer": "resolution=merge-duplicates,return=representation"}
            ),
        )
    _raise_for_status(resp)
    return _parse(resp)


def select_one(
    table: str,
    *,
    columns: str = "*",
    filters: Optional[dict[str, str]] = None,
) -> Optional[dict]:
    """SELECT a single row (or None)."""
    rows = select(table, columns=columns, filters=filters, limit=1)
    return rows[0] if rows else None


def storage_upload(bucket: str, path: str, content: bytes, content_type: str) -> str:
    """Upload bytes to a Supabase Storage bucket; return the public object URL."""
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    resp = httpx.post(
        url,
        headers=_headers({"Content-Type": content_type, "x-upsert": "true"}),
        content=content,
        timeout=60.0,
    )
    _raise_for_status(resp)
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def check_write_access() -> tuple[bool, Optional[str]]:
    """Probe that INSERT works with the current key (no RLS).

    Inserts then deletes a throwaway tenant. Returns ``(ok, error_message)``.
    On a 401/403 the message flags that a SUPABASE_SERVICE_ROLE_KEY is needed.
    """
    import uuid as _uuid

    probe_id = str(_uuid.uuid4())
    slug = f"__probe_{probe_id[:8]}"
    try:
        insert("tenants", {"id": probe_id, "slug": slug, "name": "probe"})
    except SupabaseError as exc:
        if exc.status_code in (401, 403):
            return (
                False,
                "INSERT rejected by Supabase (RLS/permissions). A "
                "SUPABASE_SERVICE_ROLE_KEY is required for writes with the "
                f"current key. PostgREST said: {exc.body}",
            )
        return False, f"Unexpected Supabase error on write probe: {exc.body}"
    # Clean up the probe row.
    try:
        with _client() as client:
            client.delete(
                "/tenants",
                params={"id": f"eq.{probe_id}"},
                headers=_headers(),
            )
    except Exception:
        pass
    return True, None
