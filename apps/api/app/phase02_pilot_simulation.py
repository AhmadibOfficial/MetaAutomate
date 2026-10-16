"""P2-03/P2-06: fictional read-only pilot, support and value rehearsal.

Not a live adapter, live customer onboarding, verified revenue or hosting cost.
No network, database, files, production scopes, provisioning or provider I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from uuid import UUID
import re

STOCK_ITEMS = {"DEMO-SKU-MAIZE": 120, "DEMO-SKU-SOYBEAN": 65, "DEMO-SKU-SORGHUM": 40}
TICKET = re.compile(r"DEMO-TICKET-[A-Z0-9-]{3,40}\Z")
MAX_TICKETS = 32
PER_TENANT_TICKETS = 8
GATES = (
    "phase01_foundation_3_of_9_no_go",
    "private_branch_protection_not_verified",
    "independent_review_not_verified",
    "approved_private_staging_not_verified",
    "real_product_identity_not_verified",
    "tenant_provider_access_not_verified",
    "real_customer_consent_not_verified",
    "live_recovery_not_verified",
    "commercial_pilot_authorization_not_granted",
)


class PilotDenied(ValueError):
    """Source-only or invalid pilot request denied."""


class PilotNotFound(LookupError):
    """No such ticket in this invented tenant partition."""


@dataclass(frozen=True)
class DemoStockPreview:
    demo_tenant: UUID
    sku: str
    quantity: int
    mode: str = "LOCAL_SYNTHETIC_READ_ONLY"
    live_source_read: bool = False
    tenant_authenticated: bool = False
    provider_called: bool = False
    execution_authorized: bool = False
    data_accessed: bool = False


def synthetic_stock_preview(*, demo_tenant: UUID, sku: str) -> DemoStockPreview:
    if type(demo_tenant) is not UUID or type(sku) is not str or sku not in STOCK_ITEMS:
        raise PilotDenied("Only allowlisted synthetic stock may be previewed")
    return DemoStockPreview(demo_tenant, sku, STOCK_ITEMS[sku])


@dataclass(frozen=True)
class DemoPilotMetrics:
    demo_tenant: UUID
    observed_requests: int
    denied_requests: int
    simulated_support_tickets: int
    hypothetical_value_minor: int
    hypothetical_cost_minor: int


@dataclass(frozen=True)
class DemoPilotReport:
    demo_tenant: UUID
    synthetic_denial_rate_basis_points: int
    hypothetical_net_value_minor: int
    report_kind: str
    missing_operational_gates: tuple[str, ...]
    decision: str = "DENY"
    real_customer_onboarded: bool = False
    production_ready: bool = False
    live_identity_verified: bool = False
    live_provider_access: bool = False
    billable_cost_verified: bool = False
    real_value_proven: bool = False
    provider_called: bool = False
    executed: bool = False


def evaluate_demo_pilot(
    metrics: DemoPilotMetrics,
    *,
    alleged_approval_from_input: bool = False,
) -> DemoPilotReport:
    """Always NO-GO even with forged 'approval'; numbers are synthetic only."""
    if type(metrics) is not DemoPilotMetrics or type(metrics.demo_tenant) is not UUID:
        raise PilotDenied("Invalid invented pilot metrics")
    vals = (
        metrics.observed_requests, metrics.denied_requests,
        metrics.simulated_support_tickets, metrics.hypothetical_value_minor,
        metrics.hypothetical_cost_minor,
    )
    if (any(type(x) is not int or x < 0 or x > 1_000_000 for x in vals)
            or metrics.denied_requests > metrics.observed_requests
            or type(alleged_approval_from_input) is not bool):
        raise PilotDenied("Invalid invented pilot measurements")
    denominator = max(1, metrics.observed_requests)
    denial_basis = metrics.denied_requests * 10_000 // denominator
    return DemoPilotReport(
        demo_tenant=metrics.demo_tenant,
        synthetic_denial_rate_basis_points=denial_basis,
        hypothetical_net_value_minor=(
            metrics.hypothetical_value_minor - metrics.hypothetical_cost_minor
        ),
        report_kind="UNVERIFIED_SYNTHETIC_METRICS",
        missing_operational_gates=GATES,
    )


@dataclass(frozen=True)
class DemoTicketView:
    demo_tenant: UUID
    ticket_id: str
    severity: str
    category: str
    status: str
    created_tick: int
    demo_only: bool = True
    notification_sent: bool = False
    customer_identity_verified: bool = False
    real_case: bool = False
    persisted: bool = False


class OfflineSupportDesk:
    """Minimal synthetic incident desk, not connected to real customer support."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tickets: dict[tuple[UUID, str], DemoTicketView] = {}

    def open(
        self, *, demo_tenant: UUID, ticket_id: str, category: str,
        severity: str, tick: int,
    ) -> DemoTicketView:
        if (type(demo_tenant) is not UUID or type(ticket_id) is not str
                or TICKET.fullmatch(ticket_id) is None
                or type(category) is not str
                or category not in ("DEMO-ACCESS", "DEMO-INVENTORY", "DEMO-DENIAL")
                or type(severity) is not str
                or severity not in ("LOW", "MEDIUM", "HIGH")
                or type(tick) is not int or not 0 <= tick <= 1_000_000):
            raise PilotDenied("Invalid fictional support ticket")
        with self._lock:
            key = (demo_tenant, ticket_id)
            existing = self._tickets.get(key)
            if existing is not None:
                if (existing.category != category or existing.severity != severity
                        or tick < existing.created_tick):
                    raise PilotDenied("Conflicting synthetic ticket replay")
                return existing
            if (len(self._tickets) >= MAX_TICKETS
                    or sum(k[0] == demo_tenant for k in self._tickets)
                    >= PER_TENANT_TICKETS):
                raise PilotDenied("Bounded in-memory support capacity exceeded")
            result = DemoTicketView(
                demo_tenant, ticket_id, severity, category,
                "SIM_OPEN_UNSENT", tick,
            )
            self._tickets[key] = result
            return result

    def inspect(self, *, demo_tenant: UUID, ticket_id: str) -> DemoTicketView:
        if type(demo_tenant) is not UUID or type(ticket_id) is not str:
            raise PilotDenied("Invalid synthetic ticket lookup")
        with self._lock:
            if (demo_tenant, ticket_id) not in self._tickets:
                raise PilotNotFound("Synthetic support ticket unavailable")
            return self._tickets[(demo_tenant, ticket_id)]
