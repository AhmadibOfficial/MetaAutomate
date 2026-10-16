"""P2-03e: transportation trip-capacity, quotation and follow-up *simulation*.

Only a committed invented fixture is used. No API routes, service accounts, real
vehicle/passenger data, reservations, money movement, messages or DB mutations.
Transportation remains DESIGN_MAPPING_ONLY in Cross-Sector Contract v1.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

FIXTURE = Path(__file__).resolve().parents[3] / "contracts/domains/v1/fixtures/synthetic_transportation.json"
MAX_BYTES = 12_288
MAX_TRIPS = 6
MAX_REQUESTS = 12
MAX_SEATS = 50
MAX_FARE = 100_000
MAX_QUOTE = 1_000_000
TRIP_ID = re.compile(r"DEMO-TRIP-[A-Z0-9-]{2,20}\Z")
REQUEST_ID = re.compile(r"DEMO-REQ-[A-Z0-9-]{2,20}\Z")
TRIP_LABEL = re.compile(r"Synthetic Route [A-Za-z0-9 -]{1,30}\Z")
PARTY_LABEL = re.compile(r"Synthetic Party [A-Za-z0-9 -]{1,30}\Z")
STAGES = (
    "AVAILABILITY_PREVIEW", "QUOTATION_DRAFT", "CUSTOMER_FOLLOWUP_DRAFT",
    "FINANCE_PREVIEW", "VERIFY_INVARIANTS",
)


class SyntheticTransportationError(ValueError):
    """Malformed, non-synthetic or unsafe proposal: reject the whole preview."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SyntheticTransportationError(reason)


def _obj(value: object, required: set[str], label: str) -> dict:
    _require(type(value) is dict and set(value) == required, f"{label}: invalid fields")
    return value


def _int(value: object, *, low: int, high: int, label: str) -> int:
    _require(type(value) is int and low <= value <= high, f"{label}: invalid integer")
    return value


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict[str, object] = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise SyntheticTransportationError(f"Nonfinite JSON token: {value}")


def validate_synthetic_transportation_bytes(raw: bytes) -> dict:
    """Bounded in-memory validation; validates even unselected trips and requests."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES and b"\x00" not in raw,
             "Invalid fixture bytes or size")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
                          parse_constant=_reject_constant)
    except SyntheticTransportationError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise SyntheticTransportationError("Invalid synthetic JSON") from exc
    root = _obj(data, {"schema_version", "classification", "currency", "sector",
                       "trips", "requests"}, "fixture")
    _require(type(root["schema_version"]) is int and root["schema_version"] == 1,
             "Unsupported fixture version")
    _require(root["classification"] == "SYNTHETIC_DEMO_ONLY" and
             root["currency"] == "DEMO_CREDITS" and root["sector"] == "transportation",
             "Fixture must be fictional transportation and not real monetary data")
    trips, requests = root["trips"], root["requests"]
    _require(type(trips) is list and 1 <= len(trips) <= MAX_TRIPS, "Invalid trip count")
    _require(type(requests) is list and 1 <= len(requests) <= MAX_REQUESTS,
             "Invalid request count")
    known_trips: set[str] = set()
    availability: dict[str, int] = {}
    for trip in trips:
        t = _obj(trip, {"trip_id", "route_label", "capacity_seats", "existing_demo_holds",
                        "fare_per_seat_demo_credits"}, "trip")
        key = t["trip_id"]
        _require(type(key) is str and TRIP_ID.fullmatch(key) and key not in known_trips,
                 "Unknown/duplicate synthetic trip identity")
        known_trips.add(key)
        _require(type(t["route_label"]) is str and TRIP_LABEL.fullmatch(t["route_label"]),
                 "Real route or location data prohibited")
        capacity = _int(t["capacity_seats"], low=1, high=MAX_SEATS, label="trip capacity")
        held = _int(t["existing_demo_holds"], low=0, high=MAX_SEATS,
                    label="existing synthetic holds")
        _require(held <= capacity, "Existing synthetic holds exceed capacity")
        _int(t["fare_per_seat_demo_credits"], low=1, high=MAX_FARE, label="demo fare")
        availability[key] = capacity - held
    requests_seen: set[str] = set()
    for req in requests:
        r = _obj(req, {"request_id", "trip_id", "party_label", "seats_requested"},
                 "transport request")
        key = r["request_id"]
        _require(type(key) is str and REQUEST_ID.fullmatch(key) and key not in requests_seen,
                 "Invalid/duplicate request identity")
        requests_seen.add(key)
        _require(type(r["party_label"]) is str and PARTY_LABEL.fullmatch(r["party_label"]),
                 "Real passenger identities/contact data are prohibited")
        _require(type(r["trip_id"]) is str and r["trip_id"] in known_trips,
                 "Unknown trip or cross-sector reference")
        qty = _int(r["seats_requested"], low=1, high=MAX_SEATS,
                   label="requested seats")
        available = availability[r["trip_id"]]
        _require(qty <= available,
                 f"Proposed trip overbooked: {r['trip_id']}")
        availability[r["trip_id"]] -= qty
    return root


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode("ascii")).hexdigest()


def render_synthetic_transportation(raw: bytes, *, trip: str | None = None) -> dict:
    """Pure deterministic proposal; filters *after* validating the full fixture."""
    source = validate_synthetic_transportation_bytes(raw)
    trip_map = {t["trip_id"]: t for t in source["trips"]}
    _require(trip is None or (type(trip) is str and trip in trip_map),
             "Unknown trip selector")
    selected_trips = [t for t in source["trips"] if trip is None or t["trip_id"] == trip]
    selected_ids = {t["trip_id"] for t in selected_trips}
    held = {t["trip_id"]: 0 for t in selected_trips}
    quotes: list[dict] = []
    followups: list[dict] = []
    finance: list[dict] = []
    traces: list[dict] = []
    for req in source["requests"]:
        key = req["trip_id"]
        if key not in selected_ids:
            continue
        t = trip_map[key]
        units = req["seats_requested"]
        held[key] += units
        quote = units * t["fare_per_seat_demo_credits"]
        _require(0 < quote <= MAX_QUOTE, "Out-of-range demo quotation")
        digest = _digest({"request_id": req["request_id"], "trip_id": key})[:24]
        quotes.append({
            "request_id": req["request_id"], "trip_id": key, "party_label": req["party_label"],
            "seats": units, "quoted_demo_credits": quote,
            "state": "UNISSUED_TRIP_ESTIMATE", "idempotency_preview": digest,
            "seat_reservation_performed": False, "ticket_issued": False,
        })
        followups.append({
            "request_id": req["request_id"], "trip_id": key,
            "draft_purpose": "REVIEW_TRIP_ESTIMATE_AND_AVAILABILITY",
            "delivery_state": "NOT_SENT", "contact_details": None,
        })
        finance.append({
            "request_id": req["request_id"], "state": "UNPOSTED_PROPOSAL",
            "record_type": "ILLUSTRATIVE_TRIP_ESTIMATE_NOT_INVOICE",
            "entries": [
                {"account": "DEMO_ACCOUNTS_RECEIVABLE", "side": "DEBIT",
                 "amount_demo_credits": quote},
                {"account": "DEMO_TRANSPORT_ESTIMATE", "side": "CREDIT",
                 "amount_demo_credits": quote},
            ],
            "debit_total_demo_credits": quote, "credit_total_demo_credits": quote,
            "balanced": True, "actual_payment_recorded": False,
            "recognized_revenue": False,
        })
        traces.append({
            "request_id": req["request_id"], "trip_id": key,
            "stages": [{"stage": stage, "state": "SIMULATED_NOT_EXECUTED"}
                       for stage in STAGES],
            "approval_state": "HUMAN_REVIEW_REQUIRED",
        })
    capacity = [{
        "trip_id": t["trip_id"], "route_label": t["route_label"],
        "original_capacity_seats": t["capacity_seats"],
        "existing_demo_holds": t["existing_demo_holds"],
        "proposed_seats": held[t["trip_id"]],
        "projected_free_if_approved": (
            t["capacity_seats"] - t["existing_demo_holds"] - held[t["trip_id"]]
        ),
        "capacity_unchanged": True,
    } for t in selected_trips]
    total = sum(x["quoted_demo_credits"] for x in quotes)
    _require(total == sum(f["debit_total_demo_credits"] for f in finance)
             == sum(f["credit_total_demo_credits"] for f in finance),
             "Unbalanced imaginary finance")
    _require(sum(t["proposed_seats"] for t in capacity) ==
             sum(q["seats"] for q in quotes),
             "Capacity and quotes differ")
    _require(all(x["projected_free_if_approved"] >= 0 for x in capacity),
             "Proposed overbooking")
    result = {
        "schema_version": 1, "mode": "LOCAL_SYNTHETIC_TRANSPORTATION_PREVIEW",
        "classification": "SYNTHETIC_DEMO_ONLY", "sector": "transportation",
        "cross_sector_contract_reference":
            "contracts/domains/v1/cross_sector_workflow_contract.v1.json",
        "cross_sector_profile_readiness": "DESIGN_MAPPING_ONLY",
        "transportation_source_status": "NEW_SYNTHETIC_EXPERIMENT_NOT_ACCEPTED_AS_CONTRACT_EVIDENCE",
        "operational_status": "NO_GO", "currency": "DEMO_CREDITS",
        "simulation_only": True, "real_transport_records_used": False,
        "real_passenger_data_used": False, "driver_data_used": False,
        "geo_or_live_location_used": False, "road_safety_assessment_performed": False,
        "execution_available": False, "trip_scheduled": False,
        "reservation_made": False, "ticket_issued": False,
        "customer_messages_sent": False, "payments_processed": False,
        "invoices_issued": False, "ledger_posted": False,
        "database_write_performed": False, "external_request_performed": False,
        "human_review_required": True,
        "fixture_sha256": sha256(raw).hexdigest(),
        "capacity_previews": capacity,
        "trip_estimates": quotes,
        "followup_drafts": followups,
        "finance_previews": finance,
        "traces": traces,
        "totals": {
            "draft_requests": len(quotes),
            "proposed_seats": sum(x["proposed_seats"] for x in capacity),
            "quoted_demo_credits": total,
            "unsent_followups": len(followups),
            "unposted_finance_proposals": len(finance)
        }
    }
    result["evidence_sha256"] = _digest(result)
    return result


def read_committed_synthetic_transportation(*, trip: str | None = None) -> dict:
    """Fixed code-owned sample only; no source paths or data accepted at runtime."""
    return render_synthetic_transportation(FIXTURE.read_bytes(), trip=trip)
