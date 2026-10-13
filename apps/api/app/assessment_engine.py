"""Operational Core v1: reproducible, evidence-linked digital maturity assessment.

This *executes* a real deterministic business assessment and generates an action
report. It does not use an LLM, contact outside services, promise a financial
outcome, or enable the 33 draft capabilities in the global registry.
"""
import hashlib
import json
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Answer(Strict):
    question_id: str = Field(min_length=3, max_length=12, pattern=r"^[A-Z]{3}-[1-3]$")
    score: int = Field(strict=True, ge=0, le=4)


class AssessmentInput(Strict):
    business_label: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=15, max_length=300)
    answers: list[Answer] = Field(min_length=15, max_length=15)

    @model_validator(mode="after")
    def complete_answers(self):
        supplied = [a.question_id for a in self.answers]
        required = [q["id"] for q in QUESTIONS]
        if len(set(supplied)) != 15 or set(supplied) != set(required):
            raise ValueError("Provide exactly one answer to every known question")
        return self


# Fixed, auditable rubric. Each of the 15 statements is self-reported 0-4.
# Domains have equal weight. The questions / evidence can be challenged by
# reviewers without misleading claims about business outcomes.
DOMAINS = (
    ("STR", "Strategy and leadership"),
    ("OPS", "Business operations"),
    ("DAT", "Data and decisions"),
    ("CUS", "Customer experience"),
    ("SEC", "Security and resilience"),
)

QUESTIONS = (
    {"id": "STR-1", "domain": "STR", "prompt": "Digital goals are documented and measured.", "action": "Document a measurable digital objective with an accountable owner.", "metric": "Percentage of digital objectives reviewed monthly"},
    {"id": "STR-2", "domain": "STR", "prompt": "A practical digital improvement roadmap is maintained.", "action": "Build a 90-day digital improvement roadmap with milestones.", "metric": "Roadmap milestones completed each month"},
    {"id": "STR-3", "domain": "STR", "prompt": "Leadership reviews progress using regular evidence.", "action": "Schedule a leadership review of digital performance and blockers.", "metric": "Number of monthly progress reviews completed"},
    {"id": "OPS-1", "domain": "OPS", "prompt": "Key operational workflows are documented.", "action": "Map one costly recurring workflow and document its handoffs.", "metric": "Number of documented critical workflows"},
    {"id": "OPS-2", "domain": "OPS", "prompt": "Repetitive manual work is measured and simplified.", "action": "Measure repeated manual tasks and test one small efficiency improvement.", "metric": "Hours spent per week on the selected process"},
    {"id": "OPS-3", "domain": "OPS", "prompt": "Tasks have clear owners and completion tracking.", "action": "Introduce accountable task ownership and completion tracking.", "metric": "Percentage of tasks delivered by the agreed date"},
    {"id": "DAT-1", "domain": "DAT", "prompt": "Business records are consistently maintained.", "action": "Create one trustworthy source of records with clear ownership.", "metric": "Percentage of required records complete"},
    {"id": "DAT-2", "domain": "DAT", "prompt": "Data accuracy is checked before decisions.", "action": "Add a weekly data quality review for the most important records.", "metric": "Data exceptions detected and corrected weekly"},
    {"id": "DAT-3", "domain": "DAT", "prompt": "Business performance is reviewed through useful metrics.", "action": "Define three decision-driving metrics and review them regularly.", "metric": "Percentage of reporting periods with updated KPIs"},
    {"id": "CUS-1", "domain": "CUS", "prompt": "Customers can reliably contact the business.", "action": "Publish and maintain clear, monitored customer contact channels.", "metric": "Time to first customer response"},
    {"id": "CUS-2", "domain": "CUS", "prompt": "Customer requests and follow-ups are tracked.", "action": "Create a simple customer request and follow-up register.", "metric": "Percentage of customer requests followed up"},
    {"id": "CUS-3", "domain": "CUS", "prompt": "Feedback is used to improve service quality.", "action": "Collect customer feedback and track one improvement at a time.", "metric": "Feedback items resolved each month"},
    {"id": "SEC-1", "domain": "SEC", "prompt": "Sensitive accounts have appropriate access protections.", "action": "Review account permissions and enable multi-factor authentication where available.", "metric": "Percentage of high-risk accounts protected with MFA"},
    {"id": "SEC-2", "domain": "SEC", "prompt": "Important business information has recoverable backups.", "action": "Set a backup schedule and test restoring a non-sensitive file.", "metric": "Successful recovery tests per quarter"},
    {"id": "SEC-3", "domain": "SEC", "prompt": "The business knows how to respond to a security incident.", "action": "Write a simple incident contact and response checklist.", "metric": "Time taken to complete a response drill"},
)

BY_ID = {q["id"]: q for q in QUESTIONS}
VERSION = "1.0.0"
SCALE = {
    0: "Not in place", 1: "Informal", 2: "Partially established",
    3: "Mostly established", 4: "Consistently demonstrated"
}


def canonical_hash(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def input_document(payload: AssessmentInput) -> dict:
    return {
        "business_label": payload.business_label,
        "objective": payload.objective,
        # Stable canonical order regardless of how the browser submits answers.
        "answers": [
            {"question_id": q["id"], "score": next(
                a.score for a in payload.answers if a.question_id == q["id"]
            )} for q in QUESTIONS
        ],
    }


def questionnaire() -> dict:
    return {
        "version": VERSION,
        "scale": [{"value": k, "label": v} for k, v in SCALE.items()],
        "domains": [{"id": code, "name": label, "questions": [
            {"id": q["id"], "prompt": q["prompt"]} for q in QUESTIONS if q["domain"] == code
        ]} for code, label in DOMAINS],
        "source": "Owner-submitted self-assessment; do not infer external facts"
    }


def produce_report(payload: AssessmentInput) -> dict:
    values = {a.question_id: a.score for a in payload.answers}
    overall = (sum(values.values()) * 100 + 30) // 60  # 60 maximum points, round-half-up.
    if overall < 40:
        level = "Foundation"
    elif overall < 70:
        level = "Developing"
    else:
        level = "Established"
    details = []
    priorities = []
    for domain_index, (code, name) in enumerate(DOMAINS):
        questions = [q for q in QUESTIONS if q["domain"] == code]
        points = sum(values[q["id"]] for q in questions)
        score = (points * 100 + 6) // 12  # Same method for all 5 domains.
        details.append({
            "id": code, "name": name, "score": score, "max_points": 12,
            "earned_points": points, "gap_points": 12 - points,
            "evidence": [{"question_id": q["id"], "self_reported_score": values[q["id"]]} for q in questions]
        })
        weakest = min(questions, key=lambda q: values[q["id"]])
        if values[weakest["id"]] < 4:
            priorities.append({
                "domain": code, "priority_domain_score": score,
                "rank_source_question": weakest["id"],
                "self_reported_score": values[weakest["id"]],
                "recommended_action": weakest["action"],
                "measurement": weakest["metric"],
                "urgency": "High" if score < 40 else "Medium" if score < 70 else "Maintain",
                "_order": domain_index
            })
    priorities.sort(key=lambda x: (x["priority_domain_score"], x["self_reported_score"], x["_order"]))
    for rank, a in enumerate(priorities, 1):
        a.pop("_order")
        a["rank"] = rank
    return {
        "report_version": VERSION, "business_label": payload.business_label,
        "objective": payload.objective, "overall_score": overall,
        "maturity_level": level, "domain_results": details,
        "prioritized_actions": priorities,
        "scoring_method": "15 owner-rated statements, each 0-4; five equally weighted domains; rounded 0-100",
        "outcome_type": "Digital maturity assessment and prioritized action plan",
        "limitations": [
            "Ratings are self-reported and not independently audited.",
            "Verifying arithmetic does not verify a change in revenue, productivity or security.",
            "Actions are recommendations, not work executed in business systems."
        ],
        "external_actions_executed": False
    }
