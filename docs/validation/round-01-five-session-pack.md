# MetaAutomate — Round 01: Founder verification across five sectors

**Prepared:** 2026-10-28. **Tester assigned:** founder, using the non-identifying code `SELF-01` in the repository. **Five controlled sample workflows, one individual. Status: 0/5 scheduled, 0/5 executed, 0/5 observed.** No external participants, bookings, consent records, customer accounts, market traction or Qatar demand have been established.

**Evidence classification:** internal self-evaluation only. Five walkthroughs by one founder do **not** equal five independent user tests, cannot meet the 4/5 independent usability thresholds and cannot validate buyer willingness to pay. Later independent testing remains required before relying on these findings for the Qatar START application.

**External user testing remains on hold until the founder verifies the complete interface and explicitly authorizes recruitment.** Sample cases are not live customer records, and no external execution or quantified benefit is implied. Do not describe unrun sessions as completed.

**Source under evaluation:** draft PR #132 at the tested checkout's exact HEAD SHA (record SHA before every session). Keep GUI unchanged until observed findings are reviewed; no merges or deployment.
**Research question:** Do real business users understand the offer in 20 seconds, create/review a plan, find Results, and understand that no real actions were executed?
**Duration:** 15 minutes per participant, plus a five-minute facilitator buffer. One moderator, one user, one local browser, controlled sample cases only. Default **no recording**.

## Self-test board — founder to run all five cases

| Scenario | Assigned evaluator | Purpose | Date/time | Executed | Findings |
|---|---|---|---|---|---|
| S01 Sales | SELF-01 (founder) | Missed inquiry | Not scheduled | No | Not observed |
| S02 Healthcare | SELF-01 (founder) | Admin appointment backlog | Not scheduled | No | Not observed |
| S03 Real Estate | SELF-01 (founder) | Viewing follow-up | Not scheduled | No | Not observed |
| S04 Retail | SELF-01 (founder) | Stock review | Not scheduled | No | Not observed |
| S05 Cloud & IT | SELF-01 (founder) | Cost review | Not scheduled | No | Not observed |

**Method:** Open the local workspace, run each sector's sample workflow, then write down actual UI failures, confusing wording, completion time and exact source SHA. Do not score founder self-tests as unbiased first-impression comprehension: the founder already knows the product. Use the same five cases for *functional/self-review* and reserve the 20-second independent comprehension score for first-time external users.

**Next independent research:** Keep the invitation template below for a later, separate round of five genuinely independent consenting adult users. No recruitment or outreach is requested or performed here. Do not add the founder's name/contact information or any human observations to GitHub.

## External-user invitation draft — ON HOLD until founder verification

**Subject:** Invitation: 15-minute MetaAutomate usability test

> Hello,
>
> I'm testing a simpler MetaAutomate business workspace and would value your feedback. It takes about 15 minutes. You would see a local prototype, choose a realistic sample business case, and try a few tasks while I observe whether the interface is clear.
>
> Participation is voluntary. Please don't share customer, patient, employee, financial or confidential business data. No recording is planned; with your consent I'd take anonymous notes about what is confusing. This is research, not a sales call, real business automation or a funding application.
>
> Would you be interested? If yes, please let me know a convenient time and your time zone. You can decline or stop at any point.
>
> Thank you.

Do not send automatically, infer consent from silence or promise payment.

## Five controlled business scenario cards

The founder reviews all five cards in separate clean local sessions; these are internal functional walkthroughs, not unassisted external-user usability observations.

### S01 — Sales: A missed inquiry
- Business: **Sample Stationery**, a sample business.
- Situation: “An online customer asked if the shop has 20 folders available; nobody has replied.”
- Goal to read aloud: “Using MetaAutomate, find where you would begin and prepare a plan to stop inquiries being overlooked.”
- Observe: Can participant find Sales & Customers, make a plan, review four checklist steps and accurately explain that no message was sent?
- **No real messages, people, phone numbers or channel connections.**

### S02 — Healthcare: Appointment backlog (administrative only)
- Business: **Example Appointment Office**, a sample organization.
- Situation: “An office has several appointment requests awaiting an administrator's review.”
- Goal: “Find a way to plan the administrative follow-up without changing a real patient appointment.”
- Observe: Can participant select Healthcare, understand the non-clinical scope, review the workflow and avoid believing any patient scheduling occurred?
- **No patient, health or medical record details; no diagnoses or clinical decision-making.**

### S03 — Real estate: Viewing follow-up
- Business: **Demo Property Agency**, sample company.
- Situation: “A prospective tenant requested a viewing for a vacant flat; the agent has not responded.”
- Goal: “Plan how an agent should organize and review the viewing request.”
- Observe: Can participant select Real Estate, understand approval and find the plan under My Work?
- **No actual tenant or property address, contracts, financing, phone numbers or broker activity.**

### S04 — Retail: Slow-moving products
- Business: **Example Clothing Shop**, fictional.
- Situation: “A CSV lists three products and stock/sales counts; some need closer review.”
- Goal: “Find the Retail & Stock area, create a review plan and, if time permits, use the sample inventory CSV to inspect stock candidates.”
- Observe: Can participant find the optional stock tool in My Work, understand fixed-rule vs predictive-AI decisions, and avoid assuming any marketing post was published?
- Sample file is generated using **Sample CSV** inside the local interface. No real stock data.

### S05 — Cloud/IT: Surprising cost
- Business: **Example IT Team**, fictional.
- Situation: “An authorized team noticed an unexplained increase in compute spending on a hypothetical account.”
- Goal: “Create a safe review plan for the cost question.”
- Observe: Can participant choose Cloud & IT, avoid interpreting the checklist as a live audit, and state that changes require an engineer's approval?
- **No cloud credentials, invoices, customer endpoints, actual cloud APIs, privileged actions or access tokens.**

## Founder verification instructions — repeat once per sector

1. **Comprehension review:** Open Home and assess whether purpose, starting action and operational scope are clear within 20 seconds. Because the founder already knows the product, label this *founder impression*, not unbiased comprehension evidence.
2. **Core task: choose and plan.** Read the assigned sample goal. Do not show where to click. Start stopwatch. Stop when a relevant plan appears under My Work. Record elapsed seconds, wrong turns and hint usage. Record any required workaround as a possible usability defect; do not count these internal walkthroughs as independent unassisted user scores.
3. **Core task: review.** “Mark this plan reviewed when you're ready.” Time the task. Watch whether all four steps and explicit human review are understood. Do not claim real operational execution.
4. **Core task: Results.** “Show me what the platform has recorded. Did it perform the business task for you?” Score unassisted navigation and comprehension.
5. **Safety and privacy.** “How would you clear this browser session?” Verify reset, then ask whether any live business data or actions were involved.
6. **After tasks only (2–3 minutes):** Ask what was confusing and which similar business problem they actually have. Keep real-world pain and willingness to pay clearly **self-reported**, not verified.

## Booking and consent gates

- [ ] **ON HOLD:** Founder signs off on the local interface and the complete internal five-sector verification report before recruitment begins.
- [ ] **After sign-off only:** choose an approved invitation method and available local time slots; do not invent time-zone availability.
- [ ] **After sign-off only:** external participant voluntarily accepts a specific invitation and confirms time and meeting method.
- [ ] **After sign-off only:** external participant separately agrees to anonymous task observation.
- [ ] Facilitator checks exact draft SHA, open local preview, synthetic fixture and no connected customer data.
- [ ] Facilitator records outcomes in a **private copy** of the blank scorecard template; do not commit observations or raw notes.
- [ ] Review evidence, triage actual confusion and fix **only observed** priority issues.
- [ ] For founder regression, repeat changed tasks locally. Independent retesting with new consenting users is **deferred until founder sign-off**.

### Actual confusion log — EMPTY UNTIL OBSERVED

No user confusion, mistakes, interviews, pilot outcomes or market validation have been observed or recorded as of preparation.

After an observed founder or independent test failure, create a **private** issue with:
- Issue code (e.g., U01; never a name), affected sector and task step
- What the user *actually did or said* (anonymized; separate direct observation from self-reported opinion)
- Reproducible UI steps and severity (blocker / major / minor)
- Proposed smallest copy/interaction fix and exact PR/commit link
- Retest first on the founder's local workspace; later with a new consenting participant after founder approval: outcome and exact version SHA

Do not edit the GUI based on imagined confusion or interpret this preparation document as real-user evidence.

## Decision criteria

Read the full [usability round 01 guide](round-01-usability.md) for the **later independent-user** thresholds (4/5 comprehension/completion, 5/5 safety comprehension, median ≤120 seconds). Those thresholds **do not apply** to five repetitions by one founder. These are **targets**, not results. If participants show safety confusion, stop external testing until copy is corrected and re-reviewed.

**Security release: NO-GO** throughout. No public deployment, live healthcare/real-estate/enterprise integration, social publishing, AI activation, spending, or QDB application submission.
