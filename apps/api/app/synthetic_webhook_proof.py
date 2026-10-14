"""P2-04b: offline synthetic webhook-proof verification, WITHOUT a receiver.

There is no HTTP route, real provider, worker, delivery, database, secret manager
or clock. Logical ticks and DEMO fixture keys are not production security.
Tenant UUIDs are trusted test-partition inputs, NOT authenticated tenancy.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import re
from threading import RLock
from uuid import UUID

SCHEMA = "metaautomate.synthetic-webhook.v1"
EVENT_TYPE = "DEMO-DELIVERY-ACK"
SCENARIOS = frozenset({
    "DEMO-INVENTORY-LOW-STOCK",
    "DEMO-INVENTORY-IN-RANGE",
    "DEMO-DELIVERY-TRANSIENT",
})
MAX_BODY_BYTES = 2048
MAX_TICK = 1_000_000
MAX_AGE_TICKS = 5
MAX_FUTURE_TICKS = 1
MAX_EVENTS_PER_TENANT = 32
MAX_EVENTS_PER_VERIFIER = 128
MAX_DEMO_KEYS = 64
MAX_KEYS_PER_TENANT = 2
DEMO_MATERIAL_PREFIX = b"DEMO-KEY-MATERIAL-"
KEY_ID_PATTERN = re.compile(r"DEMO-KID-[A-Z0-9-]{3,32}\Z")
EVENT_ID_PATTERN = re.compile(r"DEMO-EVT-[A-Z0-9-]{3,48}\Z")
SIGNATURE_PATTERN = re.compile(r"sha256=[0-9a-f]{64}\Z")
FIELDS = frozenset({
    "schema", "event_id", "tenant_marker",
    "event_type", "scenario", "issued_tick",
})


class DemoWebhookDenied(ValueError):
    """Invalid demo-only proof; errors deliberately give no key/oracle details."""


def _deny() -> None:
    raise DemoWebhookDenied("Synthetic webhook proof rejected")


def _tenant(tenant_id: UUID) -> None:
    if type(tenant_id) is not UUID:
        _deny()


def _kid(key_id: str) -> None:
    if type(key_id) is not str or KEY_ID_PATTERN.fullmatch(key_id) is None:
        _deny()


def _material(material: bytes) -> None:
    # Only syntactically marked test keys are accepted; this does NOT prove
    # that an arbitrary caller has not copied real secret material into one.
    if (type(material) is not bytes or not 32 <= len(material) <= 128
            or not material.startswith(DEMO_MATERIAL_PREFIX)
            or not all(32 <= byte <= 126 for byte in material)):
        _deny()


def synthetic_tenant_marker(tenant_id: UUID) -> str:
    """Derive a DEMO marker; NOT a verified tenant or authorization claim."""
    _tenant(tenant_id)
    digest = sha256(b"metaautomate:p2-04b:demo-tenant:" + tenant_id.bytes).hexdigest()
    return "DEMO-TENANT-" + digest[:16].upper()


def _frame(tenant_id: UUID, key_id: str, raw_body: bytes) -> bytes:
    _tenant(tenant_id)
    _kid(key_id)
    if type(raw_body) is not bytes or not 1 <= len(raw_body) <= MAX_BODY_BYTES:
        _deny()
    # Length + domain + tenant bytes + KID prevent cross-context signatures.
    return (b"metaautomate:p2-04b:synthetic-webhook:v1\n"
            + tenant_id.bytes + b"\n"
            + key_id.encode("ascii") + b"\n"
            + len(raw_body).to_bytes(4, "big") + raw_body)


def sign_synthetic_fixture(
    tenant_id: UUID, key_id: str, key_material: bytes, raw_body: bytes,
) -> str:
    """Test-fixture generator; MUST NOT be used for live provider messages."""
    _material(key_material)
    frame = _frame(tenant_id, key_id, raw_body)
    return "sha256=" + hmac.new(key_material, frame, sha256).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            _deny()
        obj[key] = value
    return obj


def _strict_payload(raw_body: bytes, tenant_id: UUID, now_tick: int) -> dict[str, object]:
    try:
        payload = json.loads(raw_body.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _deny()
    if type(payload) is not dict or payload.keys() != FIELDS:
        _deny()
    issued_tick = payload["issued_tick"]
    event_id = payload["event_id"]
    if (payload["schema"] != SCHEMA
            or payload["event_type"] != EVENT_TYPE
            or payload["tenant_marker"] != synthetic_tenant_marker(tenant_id)
            or type(event_id) is not str
            or EVENT_ID_PATTERN.fullmatch(event_id) is None
            or type(payload["scenario"]) is not str
            or payload["scenario"] not in SCENARIOS
            or type(issued_tick) is not int
            or not 0 <= issued_tick <= MAX_TICK
            or not -MAX_FUTURE_TICKS <= now_tick - issued_tick <= MAX_AGE_TICKS):
        _deny()
    return payload


@dataclass(frozen=True)
class SyntheticProof:
    """A consumed synthetic message, NOT a provider receipt or permission."""
    event_id: str
    tenant_demo_marker: str
    scenario: str
    event_type: str = EVENT_TYPE
    accepted_for_simulation: bool = True
    simulation_only: bool = True
    executed: bool = False
    actual_business_data: bool = False
    persisted: bool = False
    webhook_endpoint_available: bool = False


class OfflineSyntheticWebhookVerifier:
    """Thread-safe in-memory proof/replay demonstration. No real I/O."""

    def __init__(self, keyring: dict[tuple[UUID, str], bytes]) -> None:
        if type(keyring) is not dict or len(keyring) > MAX_DEMO_KEYS:
            _deny()
        copied: dict[tuple[UUID, str], bytes] = {}
        by_tenant: dict[UUID, int] = {}
        for identity, material in keyring.items():
            if type(identity) is not tuple or len(identity) != 2:
                _deny()
            tenant_id, key_id = identity
            _tenant(tenant_id)
            _kid(key_id)
            _material(material)
            by_tenant[tenant_id] = by_tenant.get(tenant_id, 0) + 1
            if by_tenant[tenant_id] > MAX_KEYS_PER_TENANT:
                _deny()
            copied[identity] = material
        self._keys = copied
        self._seen: set[tuple[UUID, str]] = set()
        self._tenant_counts: dict[UUID, int] = {}
        self._lock = RLock()

    def verify_once(
        self, tenant_id: UUID, key_id: str, raw_body: bytes,
        signature: str, *, now_tick: int,
    ) -> SyntheticProof:
        _tenant(tenant_id)
        _kid(key_id)
        if (type(now_tick) is not int or not 0 <= now_tick <= MAX_TICK
                or type(signature) is not str
                or SIGNATURE_PATTERN.fullmatch(signature) is None):
            _deny()
        frame = _frame(tenant_id, key_id, raw_body)
        material = self._keys.get((tenant_id, key_id))
        if material is None:
            _deny()
        expected = hmac.new(material, frame, sha256).hexdigest()
        if not hmac.compare_digest(signature[7:], expected):
            _deny()
        payload = _strict_payload(raw_body, tenant_id, now_tick)
        event_id = payload["event_id"]
        with self._lock:
            unique_event = (tenant_id, event_id)
            if unique_event in self._seen:
                _deny()
            # Fail closed when bounded replay state fills: NEVER evict old
            # event IDs and silently allow previously seen events back in.
            if (len(self._seen) >= MAX_EVENTS_PER_VERIFIER
                    or self._tenant_counts.get(tenant_id, 0) >= MAX_EVENTS_PER_TENANT):
                _deny()
            self._seen.add(unique_event)
            self._tenant_counts[tenant_id] = (
                self._tenant_counts.get(tenant_id, 0) + 1
            )
        return SyntheticProof(
            event_id=event_id,
            tenant_demo_marker=synthetic_tenant_marker(tenant_id),
            scenario=payload["scenario"],
        )
