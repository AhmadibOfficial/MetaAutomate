"use strict";

/* Ephemeral fixture run handle only. No keys, cookies or browser storage. */
const $ = id => document.getElementById(id);
const stages = ["LOADED", "ASSESSED", "PLANNED", "APPROVED", "SIMULATED", "VERIFIED"];
const names = ["Scenario", "Assess", "Plan", "Approve", "Simulate", "Verify"];
const eventNames = {
  FIXTURE_LOADED: "Synthetic fixture loaded",
  ASSESSMENT_CALCULATED: "Assessment calculated",
  PLAN_PROPOSED: "Plan bound to input",
  SIMULATION_REVIEW_APPROVE: "Simulation approved",
  SIMULATION_REVIEW_REJECT: "Simulation rejected",
  SIMULATION_FINISHED: "Draft simulation finished"
};
let token = null, state = null, view = 0, busy = false;
const money = value => new Intl.NumberFormat("en-QA", {style:"currency", currency:"QAR"}).format(value / 100);

function node(tag, text = "", cls = "") {
  const item = document.createElement(tag);
  item.textContent = text;
  if (cls) item.className = cls;
  return item;
}
function button(text, handler, cls = "primary") {
  const item = node("button", text, "button " + cls);
  item.type = "button";
  item.disabled = busy;
  item.addEventListener("click", handler);
  return item;
}
function note(title, body, warning = false) {
  const item = node("div", "", "callout" + (warning ? " warning" : ""));
  item.append(node("strong", title), node("p", body));
  return item;
}
function receipt(label, digest) {
  const item = node("div", "", "receipt");
  item.append(node("span", label), node("code", digest));
  return item;
}
function table(headers, rows) {
  const wrap = node("div", "", "table-scroll"), t = node("table");
  const head = node("thead"), hr = node("tr"), body = node("tbody");
  for (const title of headers) { const th = node("th", title); th.scope = "col"; hr.append(th); }
  head.append(hr);
  for (const row of rows) {
    const tr = node("tr");
    for (const value of row) tr.append(node("td", String(value)));
    body.append(tr);
  }
  t.append(head, body); wrap.append(t); return wrap;
}
function actionRow(primary, hint, secondary) {
  const row = node("div", "", "action-row");
  if (primary) row.append(primary);
  if (secondary) row.append(secondary);
  if (hint) row.append(node("p", hint, "small-note"));
  return row;
}
async function request(path, method = "GET", body) {
  const headers = {"Accept":"application/json", "X-MetaAutomate-Demo":"1"};
  if (token) headers["X-Demo-Run"] = token;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {method, headers, credentials:"omit", cache:"no-store",
    body: body === undefined ? undefined : JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The demo action could not be completed.");
  return data;
}
function error(message) { $("error").textContent = message; $("error").hidden = !message; }
function focusStage() { $("stage-title")?.focus(); }
function centerActiveStep() {
  const nav = $("journey"), active = nav.querySelector('[aria-current="step"]');
  if (active && nav.scrollWidth > nav.clientWidth) {
    const left = active.getBoundingClientRect().left - nav.getBoundingClientRect().left + nav.scrollLeft;
    nav.scrollLeft = Math.max(0, left - (nav.clientWidth - active.clientWidth) / 2);
  }
}
function position() { return state?.stage === "REJECTED" ? 3 : stages.indexOf(state?.stage); }
function setBusy(value) {
  busy = value;
  $("stage-panel").setAttribute("aria-busy", String(value));
  for (const control of document.querySelectorAll("button, select, input")) {
    if (value) control.disabled = true;
  }
  if (!value && state) render();
}
async function newRun() {
  setBusy(true); error("");
  try {
    if (token) await request("/demo/run", "DELETE").catch(() => {});
    token = null;
    const data = await request("/demo/runs", "POST", {scenario_id:$("scenario").value});
    token = data.run_token; state = data.state; view = 0;
    $("announcement").textContent = "A new synthetic demonstration is ready.";
  } catch (err) { error(err.message); }
  finally {
    setBusy(false);
    $("restart").disabled = false;
    $("scenario").disabled = false;
  }
}
async function advance(action, payload = {}) {
  if (busy) return;
  setBusy(true); error("");
  try {
    state = await request("/demo/actions/" + action, "POST", payload);
    view = position();
    $("announcement").textContent = state.stage === "REJECTED"
      ? "Simulation rejected. No drafts were prepared."
      : names[view] + " complete. Inspect the result before continuing.";
  } catch (err) {
    error(err.message);
    // A lost response must not silently repeat an approval or simulation.
    try { state = await request("/demo/run"); view = position(); } catch { /* Keep the visible error. */ }
  } finally { setBusy(false); focusStage(); }
}
function openView(index) {
  view = index; render(); focusStage();
}
async function download() {
  if (busy || state?.stage !== "VERIFIED") return;
  setBusy(true); error("");
  try {
    const data = await request("/demo/report");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2) + "\n"], {type:"application/json"}));
    const link = document.createElement("a"); link.href = url;
    link.download = "metaautomate-synthetic-evidence.json"; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    $("announcement").textContent = "Synthetic evidence downloaded. No customer data is included.";
  } catch (err) { error(err.message); }
  finally { setBusy(false); $("download").focus({preventScroll:true}); }
}
function render() {
  if (!state) return;
  const current = position();
  $("download").disabled = busy || state.stage !== "VERIFIED";
  $("restart").disabled = busy; $("scenario").disabled = busy;
  $("objective-description").textContent = state.objective;
  $("kpi-low").textContent = state.inventory.totals.below_threshold_count;
  $("record-count").textContent = state.inventory.totals.sku_count;
  $("units-proposed").textContent = state.inventory.totals.suggested_restock_units;
  $("kpi-drafts").textContent = state.outcomes?.observed_in_simulation.drafts_prepared ?? "—";
  const net = state.outcomes?.illustrative_estimate.net_capacity_value_minor;
  $("kpi-value").textContent = net === undefined ? "—" : money(net);
  $("kpi-value").classList.toggle("negative", net < 0);
  const nav = $("journey"); nav.replaceChildren();
  names.forEach((name, index) => {
    const accessible = index <= current || (state.stage === "PLANNED" && index === 3);
    const item = button("", () => openView(index), "");
    item.className = "step" + (index === view ? " active" : "") + (index < current ? " done" : "");
    item.disabled = busy || !accessible;
    item.setAttribute("aria-label", "Step " + (index + 1) + ": " + name);
    if (index === view) item.setAttribute("aria-current", "step");
    item.append(node("span", index < current ? "✓" : String(index + 1).padStart(2,"0"), "number"),
      node("span", name, "step-label"), node("span", "↗", "step-arrow"));
    nav.append(item);
  });
  centerActiveStep();
  $("event-count").textContent = state.audit.length;
  $("audit-list").replaceChildren(...state.audit.map(event => {
    const item = node("li"); item.append(node("strong", eventNames[event.event] || event.event),
      node("small", "#" + event.sequence + " · " + event.sha256.slice(0,16) + "…")); return item;
  }));
  const root = $("stage-panel"); root.replaceChildren();
  const top = node("div", "", "stage-header");
  top.append(node("span", String(view + 1).padStart(2,"0"), "count"),
    node("span", names[view].toUpperCase() + " / SYNTHETIC DEMONSTRATION", "eyebrow"));
  root.append(top);
  const titles = ["A small business. A visible problem.", "Understand the operational gap.",
    "A plan you can inspect.", "Your approval sets the boundary.", "Inspect what actually happened.",
    "An outcome with evidence behind it."];
  const title = node("h2", titles[view]); title.id = "stage-title"; title.tabIndex = -1;
  root.append(title);
  [scenarioView, assessmentView, planView, approvalView, simulationView, verificationView][view](root);
}
function lead(root, text) { root.append(node("p", text, "stage-lead")); }
function scenarioView(root) {
  lead(root, "Inventory checks and purchase preparation are disconnected. Begin with four invented records and a simple objective: make low-stock items reviewable.");
  root.append(table(["Synthetic item", "On hand", "Threshold", "Proposed units"], state.inventory.items.map(item =>
    [item.label.replace("Synthetic ",""), item.on_hand_units, item.reorder_threshold_units,
      item.suggested_restock_units || "—"])));
  root.append(note("Start with evidence, not a promise", "The source contains two low-stock items. Their combined suggested replenishment is 68 units. All numbers describe an invented business."));
  root.append(receipt("Inventory source SHA-256", state.sources.inventory_sha256));
  if (state.stage === "LOADED") root.append(actionRow(button("Assess the synthetic business →", () => advance("assess")), "No connected systems or customer files."));
}
function assessmentView(root) {
  const report = state.assessment.maturity;
  lead(root, "Combine a transparent digital maturity assessment with a bounded inventory check. Every finding points back to a fixed input.");
  const summary = node("div", "", "maturity"); summary.append(node("strong", report.overall_score + "%"));
  const body = node("div"); body.append(node("p", report.maturity_level + " digital maturity"), node("small", "15 invented ratings · not an independently audited business")); summary.append(body); root.append(summary);
  for (const domain of report.domain_results) {
    const row = node("div", "", "bar-row"), meter = node("meter");
    meter.min = 0; meter.max = 100; meter.value = domain.score;
    meter.setAttribute("aria-label", domain.name + ": " + domain.score + " percent");
    row.append(node("span", domain.name), meter, node("strong", String(domain.score))); root.append(row);
  }
  root.append(note("Inventory finding: 2 low-stock items", "Prepare replenishment drafts for the maize and sorghum fixture records. The maturity score guides discussion; it does not predict profitability."));
  if (state.stage === "ASSESSED") root.append(actionRow(button("Create the proposed plan →", () => advance("plan")), "Built with the existing Objective Workspace planner."));
}
function planView(root) {
  lead(root, "The objective becomes a bounded proposal. Quantities, assumptions and source hashes are included before you approve a simulation.");
  const flow = node("div", "", "workflow");
  state.plan.drafts.forEach((draft, index) => {
    const row = node("div", "", "work-step"), body = node("div");
    body.append(node("h3", "Prepare draft · " + draft.label.replace("Synthetic ","")),
      node("p", draft.units + " units · invented purchase amount " + money(draft.estimated_purchase_cost_minor)),
      node("span", "Draft only · no supplier contacted", "chip"));
    row.append(node("span", String(index + 1).padStart(2,"0")), body); flow.append(row);
  }); root.append(flow);
  root.append(note("Purchase amount is a cost, not a benefit", "These drafts contain invented inventory costs. No order is placed, no stock arrives, and no payment is made."));
  const details = node("details"), graph = state.plan.workspace_preview.work_graph;
  details.append(node("summary", "Inspect the Objective Workspace proposal (" + graph.length + " steps)"));
  for (const step of graph) details.append(node("p", step.step_id + " · " + step.summary)); root.append(details);
  root.append(receipt("Plan SHA-256", state.plan.plan_sha256));
  if (state.stage === "PLANNED") root.append(actionRow(button("Review this plan →", () => openView(3)), "Changing the scenario requires a new plan and review."));
}
function approvalView(root) {
  lead(root, "Review the exact proposal before simulating its drafts. This demonstration records a local choice; it does not authenticate a reviewer or grant operational permissions.");
  root.append(table(["Proposed effect", "Allowed here?"], [
    ["Prepare synthetic drafts in memory", "Only after this review"],
    ["Contact suppliers / place orders", "No"], ["Change stock / make payments", "No"],
    ["Use customer data / activate a connector", "No"]]));
  root.append(receipt("Review binds to plan", state.plan.plan_sha256));
  if (state.stage === "PLANNED") {
    const form = node("form"), label = node("label", "", "review-check"), check = node("input");
    check.type = "checkbox"; check.id = "simulation-consent";
    label.append(check, node("span", "I approve only the synthetic draft simulation shown in this plan. No live business action is authorized."));
    const accept = button("Approve simulation →", () => {});
    accept.disabled = true; accept.type = "submit";
    check.addEventListener("change", () => { accept.disabled = busy || !check.checked; });
    const payload = decision => ({decision, plan_sha256:state.plan.plan_sha256, simulation_only:true});
    form.addEventListener("submit", event => { event.preventDefault(); if (check.checked) advance("review", payload("APPROVE")); });
    form.append(label, actionRow(accept, "A rejected proposal cannot be simulated.", button("Reject plan", () => advance("review", payload("REJECT")), "danger")));
    root.append(form);
  } else if (state.stage === "REJECTED") {
    root.append(note("Proposal rejected", "No simulation ran. Start a new demonstration to review another plan.", true));
    root.append(actionRow(button("Restart demonstration", newRun), "The existing workspace and its records are untouched."));
  } else {
    root.append(note("Approved for this simulation", "The approval matches the exact plan hash. All business capabilities remain draft and all live execution remains denied."));
    if (state.stage === "APPROVED") root.append(actionRow(button("Simulate the approved drafts →", () => advance("simulate")), "Creates in-memory demonstration artifacts only."));
  }
}
function simulationView(root) {
  const sim = state.simulation;
  lead(root, "The simulator reports each proposed step. A blocked step stays visible and contributes no estimated time benefit.");
  root.append(table(["Synthetic draft", "Units", "Result"], sim.steps.map(step =>
    [step.label.replace("Synthetic ",""), step.units, step.status === "BLOCKED" ? "Blocked · human review" : "Draft prepared"])));
  const blocked = sim.steps.filter(step => step.status === "BLOCKED");
  if (blocked.length) root.append(note("One step needs review", "The invented supplier check blocked the sorghum draft. The simulator did not retry, switch supplier or send an order.", true));
  else root.append(note("Two drafts prepared for review", "This is a completed simulation of draft preparation. Your stock and low-stock count have not changed."));
  root.append(table(["Business effect", "Observed in simulation"], [["Stock units moved", "0"],
    ["Purchase orders sent", "0"], ["External requests / database writes", "0 / 0"]]));
  if (state.stage === "SIMULATED") root.append(actionRow(button("Verify the evidence →", () => advance("verify")), "Recompute the complete scenario against the committed reference."));
}
function verificationView(root) {
  const outcomes = state.outcomes, measured = outcomes.observed_in_simulation, estimate = outcomes.illustrative_estimate;
  lead(root, "The evidence matches a fresh replay of the committed synthetic scenario. That verifies reproducibility; real business value still needs a measured customer pilot.");
  root.append(note("Synthetic replay verified", "Assessment, plan, simulation review, results and chained receipts match the source. This is not a signed approval, independent security assessment or proof of profitability."));
  const grid = node("div", "", "outcome-grid");
  for (const [label, value, description] of [
    ["OBSERVED IN SIMULATION", measured.drafts_prepared + " drafts", measured.steps_blocked + " blocked steps · 0 stock units moved"],
    ["ILLUSTRATIVE ESTIMATE", money(estimate.net_capacity_value_minor), "Net capacity value per run · not cash saved"]]) {
    const cell = node("div", "", "outcome-cell"), big = node("strong", value);
    if (label === "ILLUSTRATIVE ESTIMATE" && estimate.net_capacity_value_minor < 0) big.className = "negative";
    cell.append(node("span", label), big, node("p", description)); grid.append(cell);
  } root.append(grid);
  root.append(node("h3", "Inspect the per-run assumptions", "section-title"));
  root.append(table(["Input / result", "Illustrative value"], [
    ["Manual minutes per prepared draft", state.assumptions.manual_minutes_per_draft],
    ["Assisted minutes per prepared draft", state.assumptions.assisted_minutes_per_draft],
    ["Assumed staff hourly cost", money(state.assumptions.staff_hourly_cost_minor)],
    ["Modelled capacity released", estimate.capacity_minutes + " minutes"]]));
  const math = node("div", "", "math");
  [["Illustrative capacity value", estimate.capacity_value_minor], ["Less assumed delivery cost", -estimate.delivery_cost_minor],
    ["Net capacity value (not cash saved)", estimate.net_capacity_value_minor]].forEach(([label, val]) => {
      const row = node("div"); row.append(node("span", label), node("span", money(val))); math.append(row);
    }); root.append(math);
  root.append(node("p", "Formula: " + estimate.method + ". Blocked steps are excluded. " + estimate.notice, "small-note"));
  if (estimate.net_capacity_value_minor < 0) root.append(note("The model does not justify this cost", "With these invented inputs, delivery cost exceeds capacity value. Do not present this scenario as a positive return on investment.", true));
  root.append(note("What remains unproven", "Cash savings, recovered revenue and actual time saved are not measured. The next evidence is a consented pilot with a baseline, delivery costs and independently supported results."));
  root.append(actionRow(button("Download synthetic evidence ↓", download), "JSON includes sources, assumptions, results and receipts."));
}

$("restart").addEventListener("click", newRun);
$("scenario").addEventListener("change", newRun);
$("download").addEventListener("click", download);
window.addEventListener("resize", () => requestAnimationFrame(centerActiveStep));
newRun();
