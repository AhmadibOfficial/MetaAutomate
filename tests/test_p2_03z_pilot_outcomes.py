"""P2-03z: honest arithmetic, aggregate-only validation and immutable receipt policy."""
from datetime import date,timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.pilot_outcomes import (
    OutcomePeriodInput, ReviewInput, canonical_hash, input_document,
    measure, _evidence, _require_key,
)

SOURCE="a"*64
CONSENT="b"*64

def sample(**updates):
    x={
        "project_key":"project-01",
        "period_kind":"BASELINE",
        "period_start":"2026-01-01",
        "period_end":"2026-01-30",
        "currency":"NGN",
        "gross_sales_minor":120_000_00,
        "variable_cost_minor":50_000_00,
        "marketing_spend_minor":10_000_00,
        "processing_fees_minor":5_000_00,
        "fulfillment_cost_minor":10_000_00,
        "software_cost_minor":5_000_00,
        "refunds_minor":0,
        "completed_orders":60,
        "source_kind":"BOOKKEEPING_EXPORT",
        "source_sha256":SOURCE,
        "consent_sha256":CONSENT,
    }
    x.update(updates)
    return x


def test_arithmetic_is_integer_deterministic_and_noncausal():
    x=OutcomePeriodInput.model_validate(sample())
    result=measure(x)
    assert result["identified_costs_minor"]==80_000_00
    assert result["contribution_after_identified_costs_minor"]==40_000_00
    assert result["average_gross_sale_per_order_minor"]==200_000
    assert result["net_profit_verified"] is False
    assert result["attributable_platform_impact_verified"] is False
    assert result["source_documents_independently_authenticated"] is False
    assert result==measure(x)
    assert len(canonical_hash(input_document(x)))==64


def test_negative_contribution_allowed_but_not_profit_claimed():
    x=OutcomePeriodInput.model_validate(sample(gross_sales_minor=10,variable_cost_minor=100,
                                                completed_orders=0))
    result=measure(x)
    assert result["contribution_after_identified_costs_minor"]<0
    assert result["average_gross_sale_per_order_minor"] is None
    assert not result["net_profit_verified"]


@pytest.mark.parametrize("mutation",[
    {"gross_sales_minor":True},
    {"gross_sales_minor":123.40},
    {"gross_sales_minor":"10000"},
    {"gross_sales_minor":-1},
    {"gross_sales_minor":10**20},
    {"marketing_spend_minor":None},
    {"refunds_minor":-10},
    {"completed_orders":False},
    {"completed_orders":10000001},
    {"source_kind":"EXTERNAL_CUSTOMER_CSV"},
    {"source_kind":"UNCONSENTED_DATA"},
    {"period_kind":"FUTURE"},
    {"currency":"NGN/USD"},
    {"currency":"ngn"},
    {"source_sha256":"evidence.jpg"},
    {"consent_sha256":""},
    {"project_key":"a"},
    {"customer_email":"do-not-retain@example.net"},
    {"email_list":["contact@example.org"]},
    {"raw_invoice":{"name":"customer"}},
    {"period_start":"2026-02-05","period_end":"2026-02-03"},
    {"period_start":"2025-01-01","period_end":"2026-02-01"},
    {"period_end":"2099-01-01"},
])
def test_sensitive_arbitrary_future_or_invalid_inputs_rejected(mutation):
    with pytest.raises(ValidationError):
        OutcomePeriodInput.model_validate(sample(**mutation))


def test_single_day_and_period_length_366_days_are_bounded():
    short=OutcomePeriodInput.model_validate(sample(
        period_start="2026-01-12",period_end="2026-01-12"))
    assert short.period_start==short.period_end
    limit=OutcomePeriodInput.model_validate(sample(
        period_start="2025-01-01",period_end="2026-01-02"))
    assert (limit.period_end-limit.period_start).days==366


def test_attestation_digest_receipt_recomputes():
    x=OutcomePeriodInput.model_validate(sample())
    r={**x.model_dump(), "id":uuid4(),"submitted_by_user_id":uuid4(),
       "input_sha256":canonical_hash(input_document(x))}
    out=_evidence(r)
    assert out["measurements"]["calculation_status"]=="ARITHMETIC_VERIFIED_ONLY"
    assert out["review_state"]=="PENDING_REVIEW"
    assert out["source_provenance_claim"]=="BOOKKEEPING_EXPORT"
    for key in ("source_documents_independently_verified",
                "human_consent_independently_verified",
                "live_customer_impact_verified",
                "external_actions_executed","release_ready"):
        assert out[key] is False
    r["input_sha256"]="f"*64
    with pytest.raises(HTTPException) as err:
        _evidence(r)
    assert err.value.status_code==409


@pytest.mark.parametrize("bad",[
    None,"short","a"*101,"abc/def/ghi/jkl","contains space here",
])
def test_idempotency_requires_safe_key(bad):
    with pytest.raises(HTTPException):
        _require_key(bad)


def test_reviewer_rejects_unknown_or_short_rationale():
    with pytest.raises(ValidationError):
        ReviewInput.model_validate({
            "decision":"EVIDENCE_CHECKED","reason":"ok",
            "source_sha256_confirmed":SOURCE,
        })
    with pytest.raises(ValidationError):
        ReviewInput.model_validate({
            "decision":"AUTO_APPROVED","reason":"This is twenty characters long",
            "source_sha256_confirmed":SOURCE,
        })


def test_source_gate_and_consent_are_never_proof_of_live_release():
    main=(ROOT/"apps/api/app/main.py").read_text()
    assert 'MAT_PILOT_OUTCOMES_ENABLED' in main
    assert 'MAT_PILOT_ACCEPTANCE_RECORD' in main
    assert '_mode != "oidc"' in main
    assert 'app.include_router(pilot_outcomes_router)' in main
    assert '"/v1/pilot-outcomes"' in main
    sql=(ROOT/"database/migrations/016_pilot_outcome_evidence.sql").read_text()
    for marker in (
        "ENABLE ROW LEVEL SECURITY","FORCE ROW LEVEL SECURITY",
        "enforce_tenant()","prevent_pilot_evidence_change()",
        "GRANT SELECT,INSERT ON pilot_outcome_periods,pilot_outcome_reviews",
        "review identity is not the authenticated actor",
        "independent reviewer required",
        "source hash mismatch",
    ):
        assert marker in sql
