"""P2-03b: bounded CSV/JSON file-content preview, local synthetic data ONLY.

The caller streams file bytes directly to a dev-only endpoint; no multipart
spool, file path, database insert, or external provider is involved. Values
are never asserted to be real business records. No capability is activated.
"""
from __future__ import annotations

import csv
from hashlib import sha256
from io import StringIO
import json
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from app.authn import TenantSession, get_tenant_session, require_role
from app.synthetic_inventory import ALLOWED_ROLES, _require_isolated_local

router = APIRouter(prefix="/v1/domain-integrations/sandbox", tags=["phase02-local-file-preview"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]

MAX_BYTES = 16384
MAX_ROWS = 20
COLUMNS = (
    "sku", "label", "on_hand_units", "reorder_threshold_units", "target_units"
)
SKU = re.compile(r"DEMO-[A-Z0-9-]{3,32}\Z")
LABEL = re.compile(r"Synthetic [A-Za-z0-9 -]{1,50}\Z")
INT = re.compile(r"(?:0|[1-9][0-9]{0,6})\Z")
MAX_UNITS = 1_000_000


def invalid(message: str = "Invalid synthetic inventory file") -> None:
    raise HTTPException(status_code=422, detail=message)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON key")
        result[name] = value
    return result


def _rows_from_json(raw: str) -> list:
    try:
        doc = json.loads(raw, object_pairs_hook=_unique_object,
                         parse_constant=lambda _: invalid())
    except (ValueError, TypeError, RecursionError):
        invalid()
    if (type(doc) is not dict
        or set(doc) != {"schema_version", "classification", "items"}
        or type(doc["schema_version"]) is not int
        or doc["schema_version"] != 1
        or doc["classification"] != "SYNTHETIC_DEMO_ONLY"
        or type(doc["items"]) is not list):
        invalid()
    return doc["items"]


def _rows_from_csv(raw: str) -> list:
    try:
        reader = csv.reader(StringIO(raw, newline=""), strict=True)
        header = next(reader, None)
        if header != list(COLUMNS):
            invalid("Invalid CSV columns")
        rows = []
        for row in reader:
            if len(row) != len(COLUMNS):
                invalid("Invalid CSV row width")
            rows.append(dict(zip(COLUMNS, row)))
            if len(rows) > MAX_ROWS:
                invalid("Too many synthetic inventory rows")
        return rows
    except (csv.Error, UnicodeError):
        invalid()


def _coerce_units(value: object, *, csv_mode: bool) -> int:
    if csv_mode:
        if type(value) is not str or not INT.fullmatch(value):
            invalid()
        count = int(value)
    else:
        if type(value) is not int:
            invalid()
        count = value
    if not 0 <= count <= MAX_UNITS:
        invalid()
    return count


def parse_synthetic_inventory_bytes(data: bytes, fmt: str, organization_id: UUID) -> dict:
    """Pure validation and bounded analysis; never reads a tenant-owned record."""
    if type(organization_id) is not UUID or type(data) is not bytes:
        invalid()
    if not data or len(data) > MAX_BYTES or b"\x00" in data:
        invalid()
    if fmt not in ("csv", "json"):
        invalid("Unsupported synthetic inventory format")
    try:
        raw = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        invalid()
    records = _rows_from_csv(raw) if fmt == "csv" else _rows_from_json(raw)
    if not 1 <= len(records) <= MAX_ROWS:
        invalid("Synthetic inventory row count out of range")

    seen = set()
    items = []
    for entry in records:
        if type(entry) is not dict or set(entry) != set(COLUMNS):
            invalid()
        sku = entry["sku"]
        label = entry["label"]
        if (type(sku) is not str or not SKU.fullmatch(sku)
            or sku in seen
            or type(label) is not str or not LABEL.fullmatch(label)):
            invalid()
        seen.add(sku)
        stock, threshold, target = [
            _coerce_units(entry[name], csv_mode=(fmt == "csv"))
            for name in COLUMNS[2:]
        ]
        if target < threshold:
            invalid()
        low = stock < threshold
        items.append({
            "sku": sku, "label": label,
            "on_hand_units": stock, "reorder_threshold_units": threshold,
            "target_units": target, "below_threshold": low,
            "suggested_restock_units": max(0, target - stock) if low else 0,
        })

    partition = sha256(
        ("metaautomate-synthetic-inventory-v1:" + str(organization_id)).encode("ascii")
    ).hexdigest()[:24]
    return {
        "mode": "LOCAL_SYNTHETIC_FILE_PREVIEW",
        "product": "metaautomate",
        "operation_id": "business.inventory.stock-preview.v1",
        "format": fmt,
        "synthetic_declaration_required": True,
        "actual_business_data": False,
        "simulation_only": True,
        "capability_state": "draft",
        "connector_state": "unbound",
        "execution_available": False,
        "persisted": False,
        "database_write_performed": False,
        "external_request_performed": False,
        "tenant_demo_partition": partition,
        "content_sha256": sha256(data).hexdigest(),
        "totals": {
            "sku_count": len(items),
            "below_threshold_count": sum(item["below_threshold"] for item in items),
            "units_on_hand": sum(item["on_hand_units"] for item in items),
            "suggested_restock_units": sum(item["suggested_restock_units"] for item in items),
        },
        "items": items,
    }


@router.post("/inventory/import/{fmt}")
async def local_synthetic_inventory_import(fmt: str, request: Request, session: Session):
    """Accept raw bytes from a local CSV/JSON *demo* file, never multipart uploads."""
    _require_isolated_local(request)
    require_role(session, ALLOWED_ROLES)
    if fmt not in ("csv", "json"):
        raise HTTPException(status_code=404, detail="Unknown synthetic import format")
    if request.query_params:
        invalid("Import does not accept query parameters")
    if request.headers.get("x-metaautomate-demo-data") != "SYNTHETIC_ONLY":
        invalid("Explicit synthetic-data declaration required")
    if (request.headers.get("content-encoding", "identity").lower() != "identity"
        or request.headers.get("transfer-encoding") not in (None, "identity", "chunked")):
        invalid("Unsupported content encoding")
    for header in ("x-tenant-id", "x-organization-id", "x-connector-url", "x-data-source",
                   "x-filename", "x-file-path", "x-provider-key"):
        if header in request.headers:
            invalid("Client authority metadata prohibited")
    content_type = request.headers.get("content-type", "").lower()
    expected = "text/csv" if fmt == "csv" else "application/json"
    if content_type not in {expected, expected + "; charset=utf-8"}:
        raise HTTPException(status_code=415, detail="Use raw UTF-8 CSV or JSON content")
    size_hint = request.headers.get("content-length")
    if size_hint:
        if not size_hint.isascii() or not size_hint.isdecimal():
            invalid("Malformed content length")
        if int(size_hint) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Synthetic file too large")

    # Streaming cap applies even if Content-Length is missing or misleading;
    # no client filename/path is ever opened and no upload lands in a temp file.
    buffer = bytearray()
    async for chunk in request.stream():
        if len(buffer) + len(chunk) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Synthetic file too large")
        buffer.extend(chunk)
    return parse_synthetic_inventory_bytes(bytes(buffer), fmt, session.principal.organization_id)
