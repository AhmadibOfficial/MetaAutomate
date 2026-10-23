"""P2-061 optional loopback-only, authenticated inventory data lab API.

Disabled by default and prohibited in OIDC/production mode. Reuses app.authn
PostgreSQL-authenticated principals, role policy and browser cookie/CSRF checks.
Storage is a separate local SQLite AES-GCM lab, not PostgreSQL tenant RLS.
"""
from __future__ import annotations

import ipaddress
import os
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.authn import TenantSession, get_tenant_session
from app.secure_inventory_lab import (
    DataLabError, SecureInventoryLab, MAX_BYTES,
)

router = APIRouter(prefix="/v1/data-lab", tags=["local-secure-data-lab"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]


def _lab(request: Request) -> SecureInventoryLab:
    if (os.environ.get("MAT_DATA_LAB_ENABLED") != "1" or
            os.environ.get("MAT_DATA_LAB_ACK") != "LOCAL_REHEARSAL_ONLY" or
            os.environ.get("WORKSPACE_AUTH_MODE", "dev_key") != "dev_key"):
        raise HTTPException(status_code=404, detail="Local data lab unavailable")
    origin = os.environ.get("WORKSPACE_ORIGIN", "http://127.0.0.1:8000").rstrip("/")
    if origin not in ("http://127.0.0.1:8000", "http://localhost:8000"):
        raise HTTPException(status_code=403, detail="Local-only data lab environment required")
    remote = request.client.host if request.client else ""
    try:
        if not ipaddress.ip_address(remote).is_loopback:
            raise HTTPException(status_code=403, detail="Only local development clients allowed")
    except ValueError:
        raise HTTPException(status_code=403, detail="Untrusted client address") from None
    if request.headers.get("host", "") not in ("127.0.0.1:8000", "localhost:8000"):
        raise HTTPException(status_code=403, detail="Unexpected local Host")
    if any(h in request.headers for h in (
        "x-tenant-id", "x-organization-id", "x-tenant-ref", "x-provider-credential",
    )):
        raise HTTPException(status_code=403, detail="Untrusted authority metadata prohibited")
    try:
        return SecureInventoryLab.from_environment()
    except (DataLabError, OSError):
        raise HTTPException(status_code=503, detail="Local data lab unavailable") from None


def _handle(error: DataLabError) -> HTTPException:
    reason = str(error)
    if "required role" in reason or "tenant member" in reason:
        return HTTPException(status_code=403, detail="Insufficient workspace permissions")
    if "not found" in reason or "retention expired" in reason:
        return HTTPException(status_code=404, detail="Document not found in authorized workspace")
    if "integrity" in reason or "cannot be verified" in reason or "altered" in reason:
        return HTTPException(status_code=409, detail="Protected data integrity verification failed")
    if "quota" in reason:
        return HTTPException(status_code=429, detail=reason)
    return HTTPException(status_code=422, detail=reason)


@router.get("/inventory")
def list_inventory(request: Request, session: Session):
    lab = _lab(request)
    try:
        items = lab.list_documents(session.principal)
    except DataLabError as error:
        raise _handle(error) from None
    return {"items": items, "encrypted": True, "release_ready": False,
            "data_class": "OWNER_AUTHORIZED_INVENTORY_ONLY"}


@router.post("/inventory", status_code=201)
async def import_inventory(
    request: Request, session: Session,
    retention_days: Annotated[int, Query(ge=1, le=30)] = 7,
    data_claim: Annotated[str | None, Header(alias="X-Inventory-Data-Claim")] = None,
):
    lab = _lab(request)
    if data_claim != "OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA":
        raise HTTPException(status_code=403, detail="Owner-authorized non-personal inventory declaration required")
    if request.headers.get("content-type", "").lower() not in (
        "text/csv", "text/csv; charset=utf-8"
    ):
        raise HTTPException(status_code=415, detail="Only raw UTF-8 CSV accepted")
    size_hint = request.headers.get("content-length", "")
    if size_hint and (not size_hint.isdecimal() or int(size_hint) > MAX_BYTES):
        raise HTTPException(status_code=413, detail="Inventory CSV too large")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Inventory CSV too large")
        raw.extend(chunk)
    try:
        return lab.import_csv(session.principal, bytes(raw),
                              retention_days=retention_days, consent_claim=data_claim)
    except DataLabError as error:
        raise _handle(error) from None


@router.get("/inventory/{document_id}")
def get_inventory(document_id: UUID, request: Request, session: Session):
    lab = _lab(request)
    try:
        return lab.get_document(session.principal, document_id)
    except DataLabError as error:
        raise _handle(error) from None


@router.delete("/inventory/{document_id}")
def remove_inventory(document_id: UUID, request: Request, session: Session):
    lab = _lab(request)
    try:
        return lab.delete_document(session.principal, document_id)
    except DataLabError as error:
        raise _handle(error) from None


@router.post("/inventory/purge-expired")
def purge_expired(request: Request, session: Session):
    lab = _lab(request)
    try:
        return lab.purge_expired(session.principal)
    except DataLabError as error:
        raise _handle(error) from None


@router.get("/audit")
def audit_summary(request: Request, session: Session):
    lab = _lab(request)
    try:
        return lab.verify_audit(session.principal)
    except DataLabError as error:
        raise _handle(error) from None
