# MetaAutomate — Real-user usability validation, round 01

**Status:** TEST PLAN ONLY, NOT CUSTOMER EVIDENCE. As of 2026-10-28, no recruitment, interviews, user sessions, customer activation or market traction is evidenced by this document.

**Scope:** Review draft [PR #132](https://github.com/AhmadibOfficial/MetaAutomate/pull/132). Do not add GUI sections or change capabilities during the testing round. Foundation release remains **NO-GO**; PR draft, unmerged, not deployed.

**Session preparation:** [Five fictional scenarios, unbooked invitation board, ready-to-send outreach and confusion log](round-01-five-session-pack.md). This does not mean participants have been contacted or sessions booked.

## One simple research question

**Can a real business user understand what MetaAutomate offers within 20 seconds, then create and review a simple plan without help—and accurately recognize that no real business operation has happened?**

### Audience and recruitment targets (not completed)

- **First round:** 5 consenting adult business users, ideally one from each of sales, healthcare administration (non-clinical), real estate, retail, and authorized IT operations. These are *targets*, not participants already recruited.
- **Confirmatory round if results merit it:** 10 additional consenting business users, ideally two per industry. Aim to include Qatar-based operators or people familiar with Qatar workflows. Record geography as **self-reported**, not verified market proof.
- Recruiting in Nigeria or remotely may identify usability issues, but **must not** be described as validating demand among Qatar buyers.
- Do not invite patients, collect medical records, ask people for credentials, pull private company reports or request live corporate access. Avoid children's data and recordings.
- **No emails, posts, invitations or recruitment outreach are authorized by this document.** Recruit only with a separate human decision.

## Session setup and privacy (15 minutes)

1. Moderator runs the **draft GUI locally**, with no live integrations, from a clean review checkout. Use a supported, already-installed browser; do not deploy, install paid dependencies or modify customer systems. For a direct in-person test, use a pre-opened browser tab. For remote tests, screen-share the **test machine only** after informed consent and do not show secrets, terminals or customer data.
2. Use only **fictional business tasks** and the bundled fictional retail stock CSV. No personal, patient, financial, tenant or infrastructure data. No recordings by default. The participant may stop at any time.
3. Explain: “This is a local prototype. It can create reviewable plans, not operate your business. We are testing whether the interface is understandable.” Do **not** explain navigation or point to buttons before tasks. Consent to *anonymous notes* separately.
4. Assign only random-looking, non-identifying codes such as P01; **no names, organizations, contact details, precise locations or IP addresses** in the scorecard. Store raw session notes privately outside GitHub and only share anonymized aggregates once reviewed.

### Start the unchanged review build on Kali (operator-initiated)

    cd "$HOME/MetaAutomate"
    git fetch origin
    git worktree add "$HOME/MetaAutomate-UX-Review" origin/feature/p2-062-unified-workspace-ui
    cd "$HOME/MetaAutomate-UX-Review"
    python3 -m http.server 8765 --bind 127.0.0.1 --directory apps/site

Open http://127.0.0.1:8765/workspace/ on that machine. **Do not run the worktree-add command if the destination already exists**; check existing worktrees without deleting or overwriting anything. This is a local preview, not an external URL or production rollout.

## Moderated task script — use identical instructions

| Step | Moderator instruction | Observe without hints | Success definition |
|---|---|---|---|
| 0. Twenty-second first impression | Display Home for 20 seconds, then hide it. Ask: “What can this tool help you do? What would you do first? Do you think it actually sends messages or makes changes?” | Exact words, hesitation, correct/incorrect expectation | Can state it's for organizing/improving a business workflow, identify sector/plan entry, and **does not claim live operations** |
| 1. Find your starting point | “Choose the business area that fits the fictional example. Create a plan for this problem.” | Time, incorrect clicks, hints | Correct industry selected and a new plan appears in **My Work**, without help |
| 2. Review your plan | “Show how you'd work through the steps and mark your plan reviewed.” | Understand checkbox and required review; any confusion about execution | All four steps checked and the review acknowledgment recorded, without help |
| 3. Find your results | “Show me what this session has recorded. Did MetaAutomate perform the task for you?” | Can find Results and distinguish activity counts from proven savings | Finds Results and explicitly identifies counts as local planning, **not actual business execution** |
| 4. Privacy control | “Clear everything from this session.” | Able to navigate Team & Settings and reset | Results return to zero; no client data was ever present |
| Optional retail-only | “Using the sample CSV provided by the moderator, find an item to review for promotion.” | Can find collapsed inventory tool in My Work; understands product recommendations | Sees stock opportunities; understands they are rules over fictional data, not AI forecasts |

**No coaching during scored tasks.** If the moderator must intervene, mark *hinted* and task success **false** for the unassisted score, then allow the user to finish for qualitative observation. Capture errors as issues, not as participant failures.

## Record exactly what happened

Use the blank header template in [round-01-scorecard-template.csv](round-01-scorecard-template.csv); create a **private copy outside the repository** before putting participant observations in it. Do not commit completed scorecards, transcripts, screenshots showing participant information, or other human research data.

- Binary per-task scores: **1 = achieved without hints; 0 = not achieved**.
- Timing: use observed seconds for tasks 1 and 2. If not completed, leave seconds blank and write why.
- **Direct observation**: clicks, completion, read-back, comprehension and misunderstandings; notes are anonymized.
- **Self-reported**: existing pain, number of inquiries, time wasted, existing tools/spend, willingness to pay. Not confirmed outcomes or invoices. Do not fabricate values, and keep these questions separate from the interface task score.
- **Unknown**: number of real users, savings, Qatar market size, pipeline, customer retention, clinical benefit and production performance unless supported by separate independent evidence.

### Optional interview after tasks (3 minutes)

Ask neutrally: “Which part of your actual work is hardest to manage?”, “How often does it happen?”, “How do you handle it today?”, “What evidence would convince you an assistant improved it?”, “What would you consider reasonable to pay if it *proved* valuable?” Do not suggest amounts, put words in their mouths or convert stated willingness into revenue.

## Precommitted decision criteria (targets, not results)

After **at least five independent consenting sessions**, review qualitatively. Do not turn 5-person findings into a statistically representative Qatar-demand claim.

- **20-second clarity:** 4/5 or more explain the purpose, first action, and operational limits correctly.
- **Unassisted core task completion:** at least 4/5 complete *each* of tasks 1, 2 and 3, with no hints.
- **First usable plan:** median time to create a plan **≤ 120 seconds**, measured across successful unassisted task-1 attempts.
- **Safety comprehension:** 5/5 must understand it is not autonomously sending messages, booking patients or changing infrastructure. Any unsafe misunderstanding triggers a blocker and revised copy before further testing.
- **Usability:** zero unaddressed critical navigation/accessibility blockers. Track high/medium/low issues with reproducible steps.
- **Commercial demand:** **not proven by usability.** Separate buyer interviews, confirmed real problem frequency, present-day spending and pilot intent are required. Willingness-to-pay answers are self-reported signals only.

If thresholds fail: fix **only the top observed confusion** and repeat the same test with new participants before adding anything. If thresholds pass: proceed to a consent-based, authorized buyer-discovery interview round, not automatic activation or release.

## Evidence and release decision

| Category | Before first real session | Acceptable later claim |
|---|---|---|
| GUI source | GitHub committed draft | Source exists; not production deployed |
| Automated unit/browser tests | Exact-head and real Chromium acceptance pending | Only report exact recorded runs on exact commit |
| Human usability | **0 sessions recorded in this plan** | X/Y consented participants observed the specified tasks |
| Qatar demand | **Unverified** | Interview count and observed/self-reported sources separately stated |
| ROI, revenue, traction | **Unverified** | Only independently supportable figures; otherwise unknown |
| Production security | **NO-GO** | Requires F04–F09 independently accepted, including F06 |

Do not merge PR #132, deploy/publicize the preview, send invitations, apply migrations, connect live messaging/AI/medical/enterprise services, purchase subscriptions or submit QDB START without separate explicit authorization.

**After the first session:** record an anonymized issue ID, the exact failure step and a minimal reproduction. Prioritize that evidence over new modules.
