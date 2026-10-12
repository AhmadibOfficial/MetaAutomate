"""Read-only, locally authenticated MetaAutomate capability catalog API.

Global metadata only; tenant activations and execution endpoints are intentionally absent.
DRAFT entries are catalog placeholders, not runnable capabilities.
"""

import hmac
import logging
import os
import re
from typing import Annotated, Literal

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, Depends, Header, HTTPException, Query

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/capabilities", tags=["capabilities"])
Domain = Literal["CORE", "BIZ", "PER", "CRE", "SPEC"]
Release = Literal["R1", "R2", "R3", "R4"]
Lifecycle = Literal["DRAFT", "REVIEW", "ACTIVE", "DEPRECATED", "RETIRED"]


def require_registry_key(
    x_registry_key: Annotated[str | None, Header(alias="X-Registry-Key")] = None,
) -> None:
    """Local development guard; not a production identity/tenant authorization model."""
    expected = os.getenv("REGISTRY_READ_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Registry API authentication is not configured")
    if x_registry_key is None or not hmac.compare_digest(x_registry_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing registry key")


def _query(sql: str, params: tuple = (), *, single: bool = False):
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone() if single else cur.fetchall()
    except (psycopg.OperationalError, psycopg.errors.UndefinedTable, KeyError):
        log.warning("Capability registry database is not ready")
        raise HTTPException(status_code=503, detail="Capability registry database is not ready") from None


@router.get("", dependencies=[Depends(require_registry_key)])
def list_capabilities(
    domain: Domain | None = None,
    release: Release | None = None,
    status: Lifecycle | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    filters: list[str] = []
    params: list[str] = []
    if domain is not None:
        filters.append("d.domain = %s")
        params.append(domain)
    if release is not None:
        filters.append("d.release = %s")
        params.append(release)
    if status is not None:
        filters.append("d.lifecycle_status = %s")
        params.append(status)
    where = (" WHERE " + " AND ".join(filters)) if filters else ""
    rows = _query(
        "SELECT d.capability_id, d.name, d.domain, d.release, d.priority, "
        "d.lifecycle_status, d.is_enabled, v.version, v.version_state, "
        "(v.contract IS NOT NULL) AS contract_provided, "
        "(d.lifecycle_status = 'ACTIVE' AND d.is_enabled "
        "AND v.is_current AND v.version_state = 'ACTIVE' "
        "AND v.contract IS NOT NULL) AS catalog_ready "
        "FROM capability_definitions d "
        "LEFT JOIN LATERAL ("
        " SELECT version, version_state, contract, is_current"
        " FROM capability_versions WHERE capability_id = d.capability_id"
        " ORDER BY is_current DESC, id DESC LIMIT 1"
        ") v ON true" + where +
        " ORDER BY d.capability_id LIMIT %s OFFSET %s",
        tuple(params) + (limit, offset),
    )
    count = _query(
        "SELECT count(*) AS total FROM capability_definitions d" + where,
        tuple(params), single=True,
    )
    return {"items": rows, "total": count["total"], "limit": limit, "offset": offset}


@router.get("/{capability_id}", dependencies=[Depends(require_registry_key)])
def get_capability(capability_id: str):
    if not re.fullmatch(r"[A-Z]+-[0-9]{3}", capability_id):
        raise HTTPException(status_code=404, detail="Capability not found")
    row = _query(
        "SELECT d.capability_id, d.name, d.domain, d.release, d.priority, "
        "d.lifecycle_status, d.is_enabled, v.version, v.version_state, "
        "(v.contract IS NOT NULL) AS contract_provided, "
        "(d.lifecycle_status = 'ACTIVE' AND d.is_enabled "
        "AND v.is_current AND v.version_state = 'ACTIVE' "
        "AND v.contract IS NOT NULL) AS catalog_ready "
        "FROM capability_definitions d "
        "LEFT JOIN LATERAL ("
        " SELECT version, version_state, contract, is_current"
        " FROM capability_versions WHERE capability_id = d.capability_id"
        " ORDER BY is_current DESC, id DESC LIMIT 1"
        ") v ON true WHERE d.capability_id = %s",
        (capability_id,), single=True,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Capability not found")
    deps = _query(
        "SELECT depends_on_capability_id, min_version "
        "FROM capability_dependencies WHERE capability_id = %s "
        "ORDER BY depends_on_capability_id", (capability_id,),
    )
    perms = _query(
        "SELECT permission_key, requires_approval "
        "FROM capability_permissions WHERE capability_id = %s "
        "ORDER BY permission_key", (capability_id,),
    )
    return {**row, "dependencies": deps, "required_permissions": perms}
