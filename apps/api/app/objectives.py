"""MetaAutomate Objective Engine v1.0 — read-only, deterministic plan preview.

No tenant context, database writes, side effects, activation, or execution.
This temporary development API requires the same shared key as the registry.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import registry

router = APIRouter(prefix="/v1/objectives", tags=["objectives"])
CAPABILITY_ID = re.compile(r"^[A-Z]+-[0-9]{3}$")


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SuccessCriterion(StrictInput):
    metric: str = Field(min_length=3, max_length=120)
    target: str = Field(min_length=1, max_length=120)
    timeframe_days: int = Field(ge=1, le=3650)


class PreviewRequest(StrictInput):
    title: str = Field(min_length=8, max_length=200)
    description: str = Field(default="", max_length=2000)
    success_criteria: list[SuccessCriterion] = Field(min_length=1, max_length=8)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    requested_capability_ids: list[str] = Field(min_length=1, max_length=10)

    @field_validator("title", "description")
    @classmethod
    def require_meaningful_content(cls, value: str) -> str:
        if value and not value.strip():
            raise ValueError("Text must not contain only whitespace")
        return value

    @field_validator("constraints")
    @classmethod
    def valid_constraints(cls, constraints: list[str]) -> list[str]:
        if any(not isinstance(c, str) or not 3 <= len(c.strip()) <= 300 for c in constraints):
            raise ValueError("Each constraint must be 3–300 non-whitespace characters")
        return [c.strip() for c in constraints]

    @field_validator("requested_capability_ids")
    @classmethod
    def valid_capabilities(cls, values: list[str]) -> list[str]:
        if any(not CAPABILITY_ID.fullmatch(value) for value in values):
            raise ValueError("Invalid capability ID format")
        if len(set(values)) != len(values):
            raise ValueError("Duplicate capability IDs are not permitted")
        return values


def build_preview(payload: PreviewRequest, caps: list[dict], dependencies: list[dict]) -> dict:
    """Pure deterministic proposal reused by previews and persistence."""
    ids = payload.requested_capability_ids
    by_id = {row["capability_id"]: row for row in caps}
    unknown = [cap_id for cap_id in ids if cap_id not in by_id]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={"reason": "Unknown registered capabilities", "capability_ids": unknown},
        )

    deps_by_id: dict[str, list[str]] = {cap_id: [] for cap_id in ids}
    for dep in dependencies:
        deps_by_id[dep["capability_id"]].append(dep["depends_on_capability_id"])

    # Reject cyclic dependencies even for a preview; cycles cannot form a work DAG.
    visits: dict[str, int] = {}

    def inspect_dependencies(capability_id: str) -> None:
        state = visits.get(capability_id, 0)
        if state == 1:
            raise HTTPException(status_code=422, detail="Cyclic capability dependencies require review")
        if state == 2:
            return
        visits[capability_id] = 1
        for dep_id in deps_by_id[capability_id]:
            if dep_id in deps_by_id:
                inspect_dependencies(dep_id)
        visits[capability_id] = 2

    for selected_id in ids:
        inspect_dependencies(selected_id)

    graph = [
        {"step_id": "S1", "type": "STRUCTURE_OBJECTIVE", "depends_on": [],
         "summary": "Review the objective, constraints and explicit success criteria"},
        {"step_id": "S2", "type": "REVIEW_CAPABILITY_MATCH", "depends_on": ["S1"],
         "summary": "Review explicitly selected capabilities against the draft catalog"},
    ]
    matched = []
    for i, cap_id in enumerate(ids, start=1):
        cap = by_id[cap_id]
        prereqs = deps_by_id[cap_id]
        unmatched_prereqs = [item for item in prereqs if item not in ids]
        step_id = f"C{i}"
        matched.append({
            "capability_id": cap_id,
            "name": cap["name"],
            "domain": cap["domain"],
            "release": cap["release"],
            "lifecycle_status": cap["lifecycle_status"],
            "catalog_enabled": cap["is_enabled"],
            "declared_dependencies": prereqs,
            "unselected_dependencies": unmatched_prereqs,
            "execution_ready": False,
        })
        graph.append({
            "step_id": step_id,
            "type": "PROPOSED_CAPABILITY_WORK",
            "capability_id": cap_id,
            "depends_on": ["S2"] + [f"C{ids.index(p) + 1}" for p in prereqs if p in ids],
            "summary": f"Design and review work for {cap['name']}; do not execute",
            "blocked": True,
        })
    graph.append({
        "step_id": "S3", "type": "REVIEW_PROPOSED_PLAN",
        "depends_on": [f"C{i}" for i in range(1, len(ids) + 1)],
        "summary": "Human review required; no actions or tenant permissions granted",
    })
    return {
        "preview_version": "1.0",
        "mode": "PLAN_PREVIEW_ONLY",
        "execution_allowed": False,
        "persisted": False,
        "objective": {
            "title": payload.title,
            "description": payload.description,
            "success_criteria": [criterion.model_dump() for criterion in payload.success_criteria],
            "constraints": payload.constraints,
        },
        "selection_method": "EXPLICIT_CAPABILITY_IDS",
        "matched_capabilities": matched,
        "work_graph": graph,
        "warnings": [
            "This is a draft preview, not an autonomous objective interpretation or executable workflow.",
            "The registry contains draft capability placeholders; no capability may run from this endpoint.",
            "No tenant identity, permissions, approvals, or persistence are established by this preview.",
        ],
    }


@router.post("/preview", dependencies=[Depends(registry.require_registry_key)])
def preview_objective(payload: PreviewRequest):
    ids = payload.requested_capability_ids
    caps = registry._query(
        "SELECT capability_id, name, domain, release, lifecycle_status, is_enabled "
        "FROM capability_definitions WHERE capability_id = ANY(%s::text[]) "
        "ORDER BY capability_id", (ids,),
    )
    dependencies = registry._query(
        "SELECT capability_id, depends_on_capability_id "
        "FROM capability_dependencies WHERE capability_id = ANY(%s::text[]) "
        "ORDER BY capability_id, depends_on_capability_id", (ids,),
    )
    return build_preview(payload, caps, dependencies)
