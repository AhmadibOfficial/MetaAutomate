"""Design-contract checks for AMBOY M0.

These ensure the published draft schemas preserve product isolation.
They do not indicate that a live model or gateway has been implemented.
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "contracts" / "amboy" / "v1"


def load(name):
    with (BASE / name).open(encoding="utf-8") as fp:
        return json.load(fp)


def test_amboy_request_has_no_client_controllable_tenant_or_product_authority():
    schema = load("turn-request.schema.json")
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    props = schema["properties"]
    for forbidden in ("tenant_id", "organization_id", "user_id", "actor_id", "product_id", "roles", "scopes", "api_key"):
        assert forbidden not in props
    assert "message" in schema["required"]
    assert props["message"]["maxLength"] <= 8000
    assert props["context_hint"]["additionalProperties"] is False


def test_amboy_responses_distinguish_proposals_from_verified_execution():
    schema = load("turn-response.schema.json")
    assert schema["additionalProperties"] is False
    assert {"status", "execution_performed", "reply"}.issubset(schema["required"])
    statuses = set(schema["properties"]["status"]["enum"])
    assert {"answered", "proposed", "approval_required", "completed_verified", "unsupported", "failed"} <= statuses
    assert "evidence_refs" in schema["properties"]


def test_amboy_capabilities_remain_draft_and_product_scoped():
    schema = load("capability-manifest.schema.json")
    assert schema["properties"]["status"]["const"] == "draft"
    assert set(schema["properties"]["product"]["enum"]) == {"metaautomate", "onecall"}
    assert schema["properties"]["id"]["pattern"].startswith("^(metaautomate|onecall)")
    assert {"required_scopes", "approval_required", "risk"}.issubset(schema["required"])
    assert "mutate_sensitive" in schema["properties"]["risk"]["enum"]


def test_amboy_is_a_specification_not_an_implemented_service():
    docs = (BASE.parents[2] / "docs" / "architecture" / "ADR-011-AMBOY-SHARED-INTELLIGENCE.md").read_text(encoding="utf-8")
    assert "MetaAutomate-owned" in docs
    assert "OneCall" in docs
    assert "does not deploy Amboy" in docs
