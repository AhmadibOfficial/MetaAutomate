"""P2-03: free, local-only synthetic inventory read simulator.

This is NOT a connector to business records and does NOT activate BIZ-011.
The only data source is a committed, explicitly synthetic JSON fixture. The
sandbox is default OFF, requires a loopback HTTP server and authenticated
workspace roles, and cannot access an external provider or write to a DB.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Annotated

from app.authn import TenantSession, get_tenant_session, require_role

router = APIRouter(prefix="/v1/domain-integrations/sandbox", tags=["phase02-synthetic-inventory"])
Session = Annotated[TenantSession, Depends(get_tenant_session)]
FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts/domains/v1/fixtures/synthetic_inventory.json"
)
MAX_FIXTURE_BYTES = 16 * 1024
ALLOWED_ROLES = {"OWNER", "ADMIN", "OPERATOR"}


def _require_isolated_local(request: Request) -> None:
    """No external use, even if a production operator sets a demo flag."""
    origin = urlsplit(os.environ.get("WORKSPACE_ORIGIN", "http://127.0.0.1:8000"))
    peer = request.client.host if request.client else ""
    if not (
        os.environ.get("DOMAIN_SANDBOX_MODE", "off") == "local_synthetic"
        and os.environ.get("WORKSPACE_AUTH_MODE", "dev_key") == "dev_key"
        and origin.scheme == "http"
        and origin.hostname in {"127.0.0.1", "localhost", "::1"}
        and origin.username is None and origin.password is None
        and not origin.path.strip("/")
        and not origin.query and not origin.fragment
        and peer in {"127.0.0.1", "::1"}
    ):
        raise HTTPException(status_code=404, detail="Synthetic inventory sandbox unavailable")


def render_synthetic_inventory(organization_id: UUID) -> dict:
    """Bounded, deterministic transformation of synthetic data, no side effects."""
    if type(organization_id) is not UUID:
        raise ValueError("Organization context must be server validated")
    raw = FIXTURE_PATH.read_bytes()
    if len(raw) > MAX_FIXTURE_BYTES:
        raise ValueError("Oversized synthetic inventory fixture")
    source = json.loads(raw)
    if (source.get("classification") != "SYNTHETIC_DEMO_ONLY"
        or source.get("schema_version") != 1
        or source.get("currency") != "NONE"
        or type(source.get("items")) is not list
        or not 1 <= len(source["items"]) <= 20):
        raise ValueError("Invalid synthetic fixture declaration")
    seen = set()
    items = []
    for entry in source["items"]:
        if type(entry) is not dict or set(entry) != {
            "sku", "label", "on_hand_units",
            "reorder_threshold_units", "target_units"
        }:
            raise ValueError("Invalid item schema")
        sku, label = entry["sku"], entry["label"]
        stock, threshold, target = (
            entry["on_hand_units"], entry["reorder_threshold_units"], entry["target_units"])
        if (not isinstance(sku, str) or not sku.startswith("DEMO-")
            or len(sku) > 40 or sku in seen
            or not isinstance(label, str) or not label.startswith("Synthetic ")
            or len(label) > 80
            or any(type(v) is not int or not 0 <= v <= 1000000
                   for v in (stock, threshold, target))
            or target < threshold):
            raise ValueError("Invalid synthetic inventory item")
        seen.add(sku)
        reorder = stock < threshold
        items.append({
            "sku": sku, "label": label, "on_hand_units": stock,
            "reorder_threshold_units": threshold, "target_units": target,
            "below_threshold": reorder,
            "suggested_restock_units": max(0, target-stock) if reorder else 0,
        })
    # This is a demo namespace marker, NOT a secret or proof of tenant ownership.
    demo_partition = sha256(
        ("metaautomate-synthetic-inventory-v1:" + str(organization_id)).encode()
    ).hexdigest()[:24]
    return {
        "mode": "LOCAL_SYNTHETIC_SIMULATION",
        "product": "metaautomate",
        "operation_id": "business.inventory.stock-preview.v1",
        "capability_state": "draft",
        "connector_state": "unbound",
        "external_provider": None,
        "actual_business_data": False,
        "simulation_only": True,
        "execution_available": False,
        "database_write_performed": False,
        "external_request_performed": False,
        "tenant_demo_partition": demo_partition,
        "fixture_sha256": sha256(raw).hexdigest(),
        "totals": {
            "sku_count": len(items),
            "below_threshold_count": sum(i["below_threshold"] for i in items),
            "units_on_hand": sum(i["on_hand_units"] for i in items),
            "suggested_restock_units": sum(i["suggested_restock_units"] for i in items),
        },
        "items": items,
    }


@router.get("/inventory")
def local_inventory_preview(request: Request, session: Session):
    _require_isolated_local(request)
    if request.query_params:
        # Tenant ID, fixture path, connector URL, data source and arbitrary
        # query keys are never accepted on this simulation endpoint.
        raise HTTPException(status_code=422, detail="Sandbox does not accept query parameters")
    require_role(session, ALLOWED_ROLES)
    return render_synthetic_inventory(session.principal.organization_id)
