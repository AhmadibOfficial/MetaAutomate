"""Operational Core v1: deterministic business-report mathematics and constraints."""
from copy import deepcopy

import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.assessment_engine import (
    AssessmentInput, QUESTIONS, canonical_hash, input_document,
    produce_report, questionnaire,
)
from app.main import app


def payload(score=0):
    return {
        "business_label": "Example Trading",
        "objective": "Identify cost reduction opportunities in operations",
        "answers": [{"question_id": q["id"], "score": score} for q in QUESTIONS],
    }


def test_questionnaire_has_five_domains_and_fifteen_questions():
    q = questionnaire()
    assert len(q["domains"]) == 5
    assert sum(len(d["questions"]) for d in q["domains"]) == 15
    assert len({q["id"] for q in QUESTIONS}) == 15
    assert [x["value"] for x in q["scale"]] == [0, 1, 2, 3, 4]


def test_all_foundation_ratings_are_zero_with_traceable_recommendations():
    model = AssessmentInput.model_validate(payload())
    report = produce_report(model)
    assert report["overall_score"] == 0
    assert report["maturity_level"] == "Foundation"
    assert len(report["domain_results"]) == 5
    assert all(d["score"] == 0 for d in report["domain_results"])
    assert len(report["prioritized_actions"]) == 5
    assert report["prioritized_actions"][0]["rank_source_question"] == "STR-1"
    assert all(x["rank_source_question"] in {q["id"] for q in QUESTIONS}
               for x in report["prioritized_actions"])
    assert not report["external_actions_executed"]


def test_all_best_ratings_score_one_hundred_without_claiming_business_impact():
    report = produce_report(AssessmentInput.model_validate(payload(4)))
    assert report["overall_score"] == 100
    assert report["maturity_level"] == "Established"
    assert not report["prioritized_actions"]
    assert any("not independently audited" in n for n in report["limitations"])


def test_lowest_scoring_domain_and_weakest_evidence_are_prioritized():
    p = payload(3)
    scores = {q["question_id"]: q for q in p["answers"]}
    scores["SEC-2"]["score"] = 0
    scores["OPS-3"]["score"] = 1
    report = produce_report(AssessmentInput.model_validate(p))
    assert report["prioritized_actions"][0]["domain"] == "SEC"
    assert report["prioritized_actions"][0]["rank_source_question"] == "SEC-2"
    assert "backup" in report["prioritized_actions"][0]["recommended_action"].lower()
    assert report["prioritized_actions"][1]["domain"] == "OPS"


def test_incomplete_duplicate_unknown_and_client_identity_fields_are_rejected():
    for mutation in [
        lambda p: p["answers"].pop(),
        lambda p: p["answers"].__setitem__(0,deepcopy(p["answers"][1])),
        lambda p: p["answers"][0].update(question_id="ZZZ-1"),
        lambda p: p.update(organization_id="00000000-0000-0000-0000-000000000000"),
        lambda p: p["answers"][0].update(score=5),
        lambda p: p["answers"][0].update(score=2.5),
    ]:
        p = payload(2)
        mutation(p)
        with pytest.raises(ValidationError):
            AssessmentInput.model_validate(p)


def test_canonical_answers_reorder_to_a_stable_receipt():
    first = AssessmentInput.model_validate(payload(2))
    reverse = payload(2)
    reverse["answers"].reverse()
    second = AssessmentInput.model_validate(reverse)
    assert input_document(first) == input_document(second)
    assert canonical_hash(input_document(first)) == canonical_hash(input_document(second))
    assert produce_report(first) == produce_report(second)


def test_assessment_routes_fail_closed_for_unauthenticated_visitors():
    client = TestClient(app)
    p = payload(2)
    assert client.get("/v1/assessments/questions").status_code == 401
    assert client.get("/v1/assessments").status_code == 401
    assert client.post("/v1/assessments",json=p).status_code == 401
    assert client.get("/assessments").status_code == 200
    assert 'id="assessment-form"' in client.get("/assessments").text


def test_verification_detects_mismatched_stored_report():
    from uuid import uuid4
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from app.assessments import _verified_receipt

    input_ = AssessmentInput.model_validate(payload(2))
    doc, report = input_document(input_), produce_report(input_)
    row = {
        "id":uuid4(), "business_label":input_.business_label, "objective":input_.objective,
        "answers":doc["answers"], "report":deepcopy(report),
        "input_sha256":canonical_hash(doc), "report_sha256":canonical_hash(report),
        "scoring_version":"1.0.0","created_at":datetime.now(timezone.utc),
    }
    assert _verified_receipt(row)["verification_status"] == "CALCULATION_VERIFIED"
    row["report"]["overall_score"] = 100
    with pytest.raises(HTTPException) as error:
        _verified_receipt(row)
    assert error.value.status_code == 409
