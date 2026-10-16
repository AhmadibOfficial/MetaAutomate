"""Integration checks for twelve source-only modules, five engines, and hostile fixtures."""
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_integrated_intelligence import (
    FIXTURE, MODULES, ENGINES, parse_suite_fixture, build_integrated_suite,
)


def test_all_twelve_modules_and_five_engines_integrated_and_reproducible():
    for workspace in ("academy_demo", "bespoke_demo"):
        for goal in ("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"):
            a = build_integrated_suite(workspace, goal)
            assert a == build_integrated_suite(workspace, goal)
            assert len(a["modules"]) == 12
            assert len(a["engines"]) == 5
            assert tuple(a["modules"]) == tuple(module for module, _ in MODULES)
            assert tuple(a["engines"]) == ENGINES
            assert a["source"]["value_evidence_sha256"]
            assert a["modules"]["finance"]["gross_sales"] == a["modules"]["commerce"]["gross_sales"]
            assert (a["modules"]["finance"]["gross_sales"] - a["modules"]["finance"]["total_identified_costs"]
                    == a["modules"]["finance"]["modeled_contribution"])
            assert not a["safety"]["real_customer_data"]
            assert a["safety"]["provider_calls"] == 0
            assert a["safety"]["messages_sent"] == 0
            assert a["safety"]["database_writes"] == 0
            assert not a["safety"]["production_ready"]
            assert a["engines"]["learning"]["controlled_causal_effect"] is None
            assert all(not op["can_auto_execute"] for op in a["engines"]["recommendation"]["ranked"])


def test_reorder_and_outreach_gates():
    a = build_integrated_suite()
    assert a["modules"]["inventory"]["reorder_flags"] >= 1
    assert a["modules"]["crm"]["outreach_enabled"] is False
    assert a["modules"]["marketing"]["posts_published"] == 0
    assert a["modules"]["decision"]["hypothetical_zero_change"]["forecast"] is False
    assert a["engines"]["automation"]["state"] == "REVIEW_ONLY"


@pytest.mark.parametrize("value", ["unknown", 0, None, True, ["academy_demo"]])
def test_unknown_workspace_rejected(value):
    with pytest.raises(SyntheticGrowthError):
        build_integrated_suite(value)


@pytest.mark.parametrize("raw", [
    b"", b"{}", b'{"schema_version":1,"schema_version":1}',
    b'{"schema_version":1.0}', b'{"a":NaN}', b'{"a":true}',
    b"\\x00" * 100, b"{" + b"x" * 17000,
])
def test_invalid_json_rejected(raw):
    with pytest.raises(SyntheticGrowthError):
        parse_suite_fixture(raw)


def test_invalid_or_private_fields_rejected():
    obj = json.loads(FIXTURE.read_bytes())
    obj["workspaces"][0]["crm"]["email"] = "private@example.invalid"
    with pytest.raises(SyntheticGrowthError):
        parse_suite_fixture(json.dumps(obj).encode())


def test_inconsistent_counts_fail_closed():
    obj = json.loads(FIXTURE.read_bytes())
    obj["workspaces"][0]["marketing"]["clicks"] = 1000
    with pytest.raises(SyntheticGrowthError):
        parse_suite_fixture(json.dumps(obj).encode())


def test_cross_tenant_duplicate_fail_closed():
    obj = json.loads(FIXTURE.read_bytes())
    obj["workspaces"][1]["workspace"] = "academy_demo"
    with pytest.raises(SyntheticGrowthError):
        parse_suite_fixture(json.dumps(obj).encode())


def test_no_unapproved_arbitrary_customer_records():
    obj = json.loads(FIXTURE.read_bytes())
    obj["workspaces"][0]["inventory"][0]["customer_phone"] = "00000"
    with pytest.raises(SyntheticGrowthError):
        parse_suite_fixture(json.dumps(obj).encode())


def test_no_income_claims_or_fake_accounting():
    a = build_integrated_suite()
    assert a["modules"]["finance"]["net_profit"] is None
    assert a["modules"]["finance"]["cash_balance"] is None
    assert a["modules"]["marketing"]["attributed_sales"] is None
    assert a["modules"]["commerce"]["conversion_rate_verified"] is False
    assert a["modules"]["operations"]["time_saved_by_ai_verified"] is False
    assert a["engines"]["recommendation"]["actual_impact_verified"] is False
