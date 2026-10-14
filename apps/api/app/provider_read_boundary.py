"""P2-03c: strict OFFLINE adapter-boundary data parser for synthetic inventory.

NOT a provider connector: no URL, network, credentials, HTTP route, database,
customer records or trusted source identity. The server may later use these
validation rules only after independently reviewed provider and tenant auth.
Passing a DEMO tenant UUID does not authenticate a user or grant read scope.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from uuid import UUID

MAX_BODY_BYTES = 8192
MAX_ITEMS = 25
MAX_UNITS = 1_000_000
PROVIDER_ID = "DEMO-INVENTORY-PROVIDER"
SCHEMA = "metaautomate.inventory-preview.fixture.v1"
SKU = re.compile(r"DEMO-SKU-[A-Z0-9-]{2,32}\Z")
ALLOWED_KEYS = frozenset({"schema", "provider", "tenant_marker", "items"})
ITEM_KEYS = frozenset({"sku", "available_units"})
CONTENT_TYPE = "application/json"


class ReadBoundaryDenied(ValueError):
    """Reject a synthetic feed without disclosing identities or content."""


def _reject(*_ignored: object) -> None:
    raise ReadBoundaryDenied("Offline inventory fixture rejected")


def demo_marker(tenant_id: UUID) -> str:
    if type(tenant_id) is not UUID:
        _reject()
    return "DEMO-TENANT-" + sha256(
        b"metaautomate:p2:inventory-fixture:" + tenant_id.bytes
    ).hexdigest()[:16].upper()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _reject()
        result[key] = value
    return result


@dataclass(frozen=True)
class DemoInventoryItem:
    sku: str
    available_units: int


@dataclass(frozen=True)
class OfflineInventoryPreview:
    tenant_marker: str
    items: tuple[DemoInventoryItem, ...]
    source: str = "UNTRUSTED_DEMO_FIXTURE"
    decision: str = "DENY"
    tenancy_authenticated: bool = False
    read_scope_verified: bool = False
    customer_consent_verified: bool = False
    provider_identity_verified: bool = False
    network_request_performed: bool = False
    customer_data_read: bool = False
    execution_authorized: bool = False
    persisted: bool = False


def parse_demo_inventory_fixture(
    *, tenant_id: UUID, body: bytes, content_type: str,
) -> OfflineInventoryPreview:
    """Validate invented bytes without interpreting them as provider access.

    Does not trust the supplied tenant UUID or authenticate the bytes.
    The only accepted schema explicitly declares itself a DEMO fixture.
    """
    marker = demo_marker(tenant_id)
    if (type(body) is not bytes or not 1 <= len(body) <= MAX_BODY_BYTES
            or type(content_type) is not str or content_type != CONTENT_TYPE):
        _reject()
    try:
        data = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=_reject,
        )
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _reject()
    if (type(data) is not dict or data.keys() != ALLOWED_KEYS
            or type(data["schema"]) is not str or data["schema"] != SCHEMA
            or type(data["provider"]) is not str
            or data["provider"] != PROVIDER_ID
            or type(data["tenant_marker"]) is not str
            or data["tenant_marker"] != marker
            or type(data["items"]) is not list
            or len(data["items"]) > MAX_ITEMS):
        _reject()

    items: list[DemoInventoryItem] = []
    seen: set[str] = set()
    for item in data["items"]:
        if (type(item) is not dict or item.keys() != ITEM_KEYS
                or type(item["sku"]) is not str
                or SKU.fullmatch(item["sku"]) is None
                or item["sku"] in seen
                or type(item["available_units"]) is not int
                or not 0 <= item["available_units"] <= MAX_UNITS):
            _reject()
        seen.add(item["sku"])
        items.append(DemoInventoryItem(item["sku"], item["available_units"]))
    return OfflineInventoryPreview(marker, tuple(items))


def demo_inventory_fixture(
    tenant_id: UUID, items: tuple[tuple[str, int], ...],
) -> bytes:
    """Create invented fixture bytes only, not fetch or import provider data."""
    marker = demo_marker(tenant_id)
    if type(items) is not tuple:
        _reject()
    payload = {
        "schema": SCHEMA, "provider": PROVIDER_ID,
        "tenant_marker": marker,
        "items": [
            {"sku": sku, "available_units": units}
            for sku, units in items
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    # Apply the exact same constraints to generated synthetic fixture bytes.
    parse_demo_inventory_fixture(
        tenant_id=tenant_id, body=encoded, content_type=CONTENT_TYPE,
    )
    return encoded
