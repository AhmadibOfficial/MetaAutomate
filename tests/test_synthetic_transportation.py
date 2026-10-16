"""P2-03e transportation only: bounded source simulation and negative cases."""
import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_transportation import (  # noqa: E402
    FIXTURE, MAX_BYTES, STAGES, SyntheticTransportationError,
    read_committed_synthetic_transportation, render_synthetic_transportation,
    validate_synthetic_transportation_bytes,
)


def data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def raw(obj):
    return json.dumps(obj, sort_keys=True).encode("utf-8")


def must_reject(obj, reason):
    with pytest.raises(SyntheticTransportationError, match=reason):
        render_synthetic_transportation(raw(obj))


def test_draft_transportation_capacity_quotes_and_finance_are_consistent():
    report = read_committed_synthetic_transportation()
    assert report["mode"] == "LOCAL_SYNTHETIC_TRANSPORTATION_PREVIEW"
    assert report["cross_sector_profile_readiness"] == "DESIGN_MAPPING_ONLY"
    assert report["operational_status"] == "NO_GO"
    assert report["transportation_source_status"].startswith("NEW_SYNTHETIC_EXPERIMENT")
    assert report["totals"] == {
        "draft_requests": 3, "proposed_seats": 9,
        "quoted_demo_credits": 15900, "unsent_followups": 3,
        "unposted_finance_proposals": 3,
    }
    assert [(x["trip_id"], x["proposed_seats"], x["projected_free_if_approved"])
            for x in report["capacity_previews"]] == [
        ("DEMO-TRIP-A1", 7, 3), ("DEMO-TRIP-B2", 2, 5)
    ]
    assert [q["quoted_demo_credits"] for q in report["trip_estimates"]] == [
        4500, 6000, 5400
    ]
    assert all(q["state"] == "UNISSUED_TRIP_ESTIMATE"
               and q["seat_reservation_performed"] is False
               and q["ticket_issued"] is False for q in report["trip_estimates"])


def test_cross_functional_trace_no_side_effects_or_real_people():
    report = read_committed_synthetic_transportation()
    keys = {x["request_id"] for x in report["trip_estimates"]}
    assert keys == {x["request_id"] for x in report["followup_drafts"]}
    assert keys == {x["request_id"] for x in report["finance_previews"]}
    assert keys == {x["request_id"] for x in report["traces"]}
    assert [x["route_label"] for x in report["capacity_previews"]] == [
        "Synthetic Route Alpha", "Synthetic Route Beta"
    ]
    assert [x["party_label"] for x in report["trip_estimates"]] == [
        "Synthetic Party One", "Synthetic Party Two", "Synthetic Party Three"
    ]
    for trace in report["traces"]:
        assert [stage["stage"] for stage in trace["stages"]] == list(STAGES)
        assert all(stage["state"] == "SIMULATED_NOT_EXECUTED" for stage in trace["stages"])
        assert trace["approval_state"] == "HUMAN_REVIEW_REQUIRED"
    for f in report["finance_previews"]:
        assert f["state"] == "UNPOSTED_PROPOSAL"
        assert f["balanced"] is True
        assert f["debit_total_demo_credits"] == f["credit_total_demo_credits"]
        assert [e["side"] for e in f["entries"]] == ["DEBIT", "CREDIT"]
        assert f["actual_payment_recorded"] is False and f["recognized_revenue"] is False
    assert all(x["delivery_state"] == "NOT_SENT" and x["contact_details"] is None
               for x in report["followup_drafts"])
    assert all(x["capacity_unchanged"] is True for x in report["capacity_previews"])
    assert report["human_review_required"] is True
    assert report["simulation_only"] is True
    for flag in ("real_transport_records_used", "real_passenger_data_used",
                 "driver_data_used", "geo_or_live_location_used",
                 "road_safety_assessment_performed", "execution_available",
                 "trip_scheduled", "reservation_made", "ticket_issued",
                 "customer_messages_sent", "payments_processed", "invoices_issued",
                 "ledger_posted", "database_write_performed",
                 "external_request_performed"):
        assert report[flag] is False


def test_determinism_and_trip_filter_do_not_skip_input_validation():
    snap = FIXTURE.read_bytes()
    first = read_committed_synthetic_transportation()
    assert read_committed_synthetic_transportation() == first
    assert FIXTURE.read_bytes() == snap
    selected = read_committed_synthetic_transportation(trip="DEMO-TRIP-A1")
    assert selected["totals"]["draft_requests"] == 2
    assert selected["totals"]["proposed_seats"] == 7
    assert selected["totals"]["quoted_demo_credits"] == 10500
    assert len(selected["capacity_previews"]) == 1
    assert selected["evidence_sha256"] != first["evidence_sha256"]
    assert all(q["trip_id"] == "DEMO-TRIP-A1" for q in selected["trip_estimates"])
    with pytest.raises(SyntheticTransportationError, match="Unknown trip selector"):
        read_committed_synthetic_transportation(trip="DEMO-TRIP-OTHER")
    poisoned = data()
    poisoned["requests"][-1]["party_label"] = "Real Passenger Name"
    with pytest.raises(SyntheticTransportationError, match="Real passenger"):
        render_synthetic_transportation(raw(poisoned), trip="DEMO-TRIP-A1")


def test_aggregate_overbooking_and_existing_capacity_denied():
    d = data()
    d["requests"][1]["seats_requested"] = 8
    must_reject(d, "overbooked")
    d = data()
    d["trips"][0]["existing_demo_holds"] = 13
    must_reject(d, "holds exceed capacity")


def test_cross_trip_unrecognized_ids_and_duplicate_ids_denied():
    d = data()
    d["requests"][0]["trip_id"] = "DEMO-TRIP-WRONG"
    must_reject(d, "Unknown trip")
    d = data()
    d["trips"][1]["trip_id"] = d["trips"][0]["trip_id"]
    must_reject(d, "duplicate synthetic trip")
    d = data()
    d["requests"][1]["request_id"] = d["requests"][0]["request_id"]
    must_reject(d, "duplicate request")


def test_real_locations_contact_names_driver_and_vehicle_fields_denied():
    d = data()
    d["trips"][0]["route_label"] = "Abuja to Kaduna"
    must_reject(d, "Real route")
    d = data()
    d["trips"][0]["plate_number"] = "AB123"
    must_reject(d, "invalid fields")
    d = data()
    d["requests"][0]["passenger_phone"] = "12345"
    must_reject(d, "invalid fields")
    d = data()
    d["requests"][0]["party_label"] = "Jane Smith"
    must_reject(d, "Real passenger")


@pytest.mark.parametrize("value", [True, False, -1, 0, 51, 1.5, "3", None])
def test_invalid_capacity_rejected(value):
    d = data()
    d["trips"][0]["capacity_seats"] = value
    must_reject(d, "trip capacity")


@pytest.mark.parametrize("value", [True, False, -1, 0, 51, 1.5, "3", None])
def test_invalid_quantities_rejected(value):
    d = data()
    d["requests"][0]["seats_requested"] = value
    must_reject(d, "requested seats")


@pytest.mark.parametrize("value", [True, False, -1, 0, 100001, 1.5, "1500", None])
def test_invalid_demo_prices_rejected(value):
    d = data()
    d["trips"][0]["fare_per_seat_demo_credits"] = value
    must_reject(d, "demo fare")


def test_non_synthetic_classification_currency_unexpected_fields_denied():
    for key, value in (
        ("classification", "CUSTOMER_IMPORT"),
        ("currency", "NGN"),
        ("sector", "healthcare"),
        ("schema_version", True),
    ):
        d = data()
        d[key] = value
        must_reject(d, "fixture" if key == "schema_version" else "fictional")
    d = data()
    d["provider_token"] = "fake-token"
    must_reject(d, "invalid fields")


def test_nonfinite_duplicate_keys_bad_encoding_and_size_denied():
    text = FIXTURE.read_text(encoding="utf-8").replace(
        '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1
    )
    with pytest.raises(SyntheticTransportationError, match="Duplicate JSON key"):
        validate_synthetic_transportation_bytes(text.encode("utf-8"))
    for entry in (b"", b"\x00", b"\xff", b" " * (MAX_BYTES + 1),
                  b'{"schema_version": NaN}', b"[]"):
        with pytest.raises(SyntheticTransportationError):
            render_synthetic_transportation(entry)


def test_limit_quote_and_no_real_finance_actions():
    d = data()
    d["trips"][0]["fare_per_seat_demo_credits"] = 100000
    d["requests"][0]["seats_requested"] = 11
    # 2 fictional seats already held, so oversized quote cannot bypass capacity check.
    must_reject(d, "overbooked")
    d = data()
    d["trips"][0]["fare_per_seat_demo_credits"] = 100000
    report = render_synthetic_transportation(raw(d))
    assert report["payments_processed"] is False
    assert report["ledger_posted"] is False
    assert report["totals"]["quoted_demo_credits"] == 805900


def test_schema_stages_aligned_with_v1_contract_without_promoting_readiness():
    contract = json.loads(
        (ROOT / "contracts/domains/v1/cross_sector_workflow_contract.v1.json").read_text()
    )
    assert tuple(s["stage"] for s in contract["workflow_stages"]) == STAGES
    transportation = next(p for p in contract["sector_profiles"]
                          if p["sector"] == "transportation")
    assert transportation["readiness"] == "DESIGN_MAPPING_ONLY"
    assert transportation["source_scenario"] is None
    assert transportation["execution_available"] is False


def test_no_route_network_credentials_or_source_capability_activation():
    main = (ROOT / "apps/api/app/main.py").read_text()
    code = (ROOT / "apps/api/app/synthetic_transportation.py").read_text()
    assert "synthetic_transportation_router" not in main
    assert "include_router(synthetic_transportation" not in main
    for forbidden in ("psycopg", "requests.", "httpx.", "urllib.request",
                      "subprocess", "send_email", "smtp", "openai.", "redis.",
                      "sqlalchemy", "fastapi"):
        assert forbidden not in code
    assert "FIXTURE.read_bytes()" in code
    assert "reservation_made" in code and "ticket_issued" in code
