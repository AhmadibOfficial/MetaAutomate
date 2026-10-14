"""P2-05e/f: synthetic provider receipt consistency, never provider verification.

All fixtures are created locally by this file; hashes are unkeyed checksum
demonstrations and do not prove issuer identity, external effects or consent.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
from threading import RLock
from uuid import UUID

from app.phase02_approval_evidence import DemoApprovalView, REVIEWED, DemoDenied

RECEIPT_LABEL = re.compile(r"DEMO-RECEIPT-[A-Z0-9-]{3,48}\Z")
OUTCOMES = frozenset(("SIM_PROVIDER_REPORTS_MATCH", "SIM_PROVIDER_REPORTS_DIFFERENCE"))
MAX_RECEIPTS = 64


@dataclass(frozen=True)
class DemoProviderReceipt:
    receipt_id: str
    proposal_id: UUID
    operation_id: str
    scenario: str
    proposal_revision: int
    proposal_audit_head: str
    simulated_outcome: str
    checksum: str


@dataclass(frozen=True)
class DemoReceiptVerdict:
    receipt_id: str
    synthetic_consistency: bool
    explanation: str
    decision: str = "DENY"
    provider_identity_verified: bool = False
    independent_provider_query_performed: bool = False
    execution_authorized: bool = False
    executed: bool = False
    provider_called: bool = False
    authoritative_receipt_verified: bool = False
    persisted: bool = False


def _digest(data: dict[str, object]) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode("ascii")).hexdigest()


def _fields(
    receipt_id: str, proposal_id: UUID, operation_id: str, scenario: str,
    revision: int, head: str, outcome: str,
) -> dict[str, object]:
    return {
        "receipt_id": receipt_id, "proposal_id": str(proposal_id),
        "operation_id": operation_id, "scenario": scenario,
        "proposal_revision": revision,
        "proposal_audit_head": head, "simulated_outcome": outcome,
    }


def make_demo_receipt(
    proposal: DemoApprovalView, receipt_id: str, outcome: str,
) -> DemoProviderReceipt:
    """Generate fake evidence; no external provider is ever contacted."""
    if (type(proposal) is not DemoApprovalView or proposal.status != REVIEWED
            or type(receipt_id) is not str
            or RECEIPT_LABEL.fullmatch(receipt_id) is None
            or type(outcome) is not str or outcome not in OUTCOMES):
        raise DemoDenied("Synthetic receipt creation denied")
    data = _fields(
        receipt_id, proposal.proposal_id, proposal.operation_id,
        proposal.scenario, proposal.revision, proposal.audit_head, outcome,
    )
    return DemoProviderReceipt(
        receipt_id, proposal.proposal_id, proposal.operation_id,
        proposal.scenario, proposal.revision, proposal.audit_head,
        outcome, _digest(data),
    )


def inspect_demo_receipt(
    proposal: DemoApprovalView, receipt: DemoProviderReceipt,
) -> DemoReceiptVerdict:
    if (type(proposal) is not DemoApprovalView
            or type(receipt) is not DemoProviderReceipt
            or type(receipt.receipt_id) is not str
            or RECEIPT_LABEL.fullmatch(receipt.receipt_id) is None):
        raise DemoDenied("Synthetic receipt inspection denied")
    equal = (
        proposal.status == REVIEWED
        and proposal.proposal_id == receipt.proposal_id
        and proposal.operation_id == receipt.operation_id
        and proposal.scenario == receipt.scenario
        and proposal.revision == receipt.proposal_revision
        and proposal.audit_head == receipt.proposal_audit_head
        and type(receipt.simulated_outcome) is str
        and receipt.simulated_outcome in OUTCOMES
        and type(receipt.checksum) is str
        and receipt.checksum == _digest(_fields(
            receipt.receipt_id, receipt.proposal_id, receipt.operation_id,
            receipt.scenario, receipt.proposal_revision,
            receipt.proposal_audit_head, receipt.simulated_outcome,
        ))
    )
    return DemoReceiptVerdict(
        receipt_id=receipt.receipt_id,
        synthetic_consistency=equal,
        explanation=("SIM_CHECKSUM_CONSISTENT_NO_REAL_PROVIDER"
                     if equal else "SIM_EVIDENCE_MISMATCH"),
    )


class OfflineReceiptReplayRegistry:
    """Single-process replay-rejection demonstration, not distributed JTI."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._observations: dict[tuple[UUID, str], DemoProviderReceipt] = {}

    def inspect_once(
        self, *, tenant_id: UUID, proposal: DemoApprovalView,
        receipt: DemoProviderReceipt,
    ) -> DemoReceiptVerdict:
        if (type(tenant_id) is not UUID or type(proposal) is not DemoApprovalView
                or proposal.tenant_id != tenant_id):
            raise DemoDenied("Synthetic tenant partition mismatch")
        verdict = inspect_demo_receipt(proposal, receipt)
        with self._lock:
            key = (tenant_id, receipt.receipt_id)
            old = self._observations.get(key)
            if old is not None:
                if old != receipt:
                    raise DemoDenied("Conflicting synthetic receipt replay")
                return verdict
            if len(self._observations) >= MAX_RECEIPTS:
                raise DemoDenied("Synthetic receipt capacity exceeded")
            self._observations[key] = receipt
            return verdict
