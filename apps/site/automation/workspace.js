/* P2-03k free explorer: consumes source-generated review decisions without network requests, stored customer data or execution. */
(() => {
  "use strict";
  const DEMOS = Object.freeze({
    academy_demo: {
      label: "Academy scenario",
      kind: "Education",
      target: 20000,
      marketing: 2500,
      products: [
        {id:"DEMO-COURSE-ALPHA",price:10000,cost:3000},
        {id:"DEMO-COURSE-BETA",price:15000,cost:5000}
      ],
      orders: [
        {id:"DEMO-ORDER-EDU01",product:"DEMO-COURSE-ALPHA",journey:"DEMO-JOURNEY-EDU01",units:1},
        {id:"DEMO-ORDER-EDU02",product:"DEMO-COURSE-BETA",journey:"DEMO-JOURNEY-EDU01",units:1}
      ],
      events: [
        {id:"DEMO-EVENT-EDU01",kind:"LEAD_OPT_IN",consent:true,title:"Welcome a new learner",detail:"Prepare an introductory learning resource."},
        {id:"DEMO-EVENT-EDU02",kind:"CHECKOUT_ABANDONED",consent:true,title:"Checkout recovery",detail:"Selar's native reminder should own checkout recovery; MetaAutomate suppresses duplicates."},
        {id:"DEMO-EVENT-EDU03",kind:"PURCHASE_COMPLETED",consent:true,title:"Help after course purchase",detail:"Suggest course access and onboarding guidance for staff review."},
        {id:"DEMO-EVENT-EDU04",kind:"LEARNING_COMPLETED",consent:true,title:"Explore a next learning step",detail:"Prepare an optional related-course recommendation for human review."},
        {id:"DEMO-EVENT-EDU05",kind:"PURCHASE_COMPLETED",consent:true,title:"Support another course purchase",detail:"Prepare onboarding guidance for the next course."},
        {id:"DEMO-EVENT-EDU06",kind:"LEAD_OPT_IN",consent:false,title:"Unverified marketing permission",detail:"Do not draft a marketing send without verified consent."}
      ],
      opportunity:"Review a learner engagement workflow with clear approval, consent and connection requirements."
    },
    bespoke_demo: {
      label: "Bespoke scenario",
      kind: "Apparel",
      target: 15000,
      marketing: 1500,
      products: [
        {id:"DEMO-GARMENT-ALPHA",price:30000,cost:21000},
        {id:"DEMO-ACCESSORY-BETA",price:5000,cost:2500}
      ],
      orders: [
        {id:"DEMO-ORDER-FAS01",product:"DEMO-GARMENT-ALPHA",journey:"DEMO-JOURNEY-FAS01",units:1},
        {id:"DEMO-ORDER-FAS02",product:"DEMO-ACCESSORY-BETA",journey:"DEMO-JOURNEY-FAS01",units:1}
      ],
      events: [
        {id:"DEMO-EVENT-FAS01",kind:"LEAD_OPT_IN",consent:true,title:"Respond to a fashion enquiry",detail:"Prepare an optional garment-fit guide for staff review."},
        {id:"DEMO-EVENT-FAS02",kind:"CHECKOUT_ABANDONED",consent:true,title:"Checkout recovery",detail:"Selar's native recovery owns this step. Suppress extra reminders."},
        {id:"DEMO-EVENT-FAS03",kind:"PURCHASE_COMPLETED",consent:true,title:"Share garment aftercare",detail:"Propose a helpful care and delivery explanation, never auto-send."},
        {id:"DEMO-EVENT-FAS04",kind:"GARMENT_DELIVERED",consent:true,title:"Suggest a matching style",detail:"Prepare a coordinated-accessory idea for independent review."},
        {id:"DEMO-EVENT-FAS05",kind:"PURCHASE_COMPLETED",consent:true,title:"Support an accessory purchase",detail:"Propose a product care note for this purchase journey."},
        {id:"DEMO-EVENT-FAS06",kind:"LEAD_OPT_IN",consent:false,title:"Unverified marketing permission",detail:"Suppress outreach until a legitimate opt-in is verified."}
      ],
      opportunity:"Explore a post-delivery care journey supported by consent and business-owner oversight."
    }
  });
  const byId = id => document.getElementById(id);
  // Source figures remain DEMO_CREDITS: $ is a fictional display convention, not USD or FX conversion.
  const shortMoney = n => "$" + new Intl.NumberFormat("en-US", {maximumFractionDigits:0}).format(n);
  const business = byId("business-select");
  const goal = byId("goal-select");
  const target = byId("target-slider");
  const queue = byId("automation-queue");
  const tabs = Array.from(document.querySelectorAll("[data-view]"));
  let activeView = "overview";
  let selectedWorkspace = business.value;
  let demoTarget = DEMOS[selectedWorkspace].target;
  let lastInspected = null;

  // Exact browser projection of the validated P2-03j decisions; no parallel policy.
  const ENGINE = window.GrowthAutopilotPreviewData;
  const GOAL_TYPES = Object.freeze({contribution:"CONTRIBUTION",repeat:"RETENTION",orders:"COMPLETED_ORDERS"});
  if (!ENGINE || ENGINE.schema_version !== 1 ||
      ENGINE.access !== "FREE_EXPLORER_NO_ACCOUNT" ||
      ENGINE.source !== "P2-03j_GOAL_ORCHESTRATION") {
    throw new Error("Growth Automation Engine contract unavailable");
  }
  function evaluate(data) {
    const plan = ENGINE.workspaces[selectedWorkspace].goals[GOAL_TYPES[goal.value]];
    if (!plan) throw new Error("Selected business goal is unavailable");
    const states = Object.freeze({
      PROPOSED_HUMAN_REVIEW_ONLY:"REVIEW_REQUIRED",
      SUPPRESSED_PROVIDER_OWNS:"SUPPRESSED_PROVIDER_OWNS",
      SUPPRESSED_CONSENT_UNVERIFIED:"SUPPRESSED_NO_MARKETING_CONSENT",
      DEFERRED_NOT_GOAL_RELEVANT:"DEFERRED_NOT_GOAL_RELEVANT"
    });
    const proposals = data.events.map(event => {
      const decision = plan.decisions[event.id];
      if (!decision || !Object.hasOwn(states,decision.state)) {
        throw new Error("Missing or unauthorized workflow policy");
      }
      return {...event,state:states[decision.state],reason:decision.reason};
    });
    const m=plan.metrics;
    return {
      sales:m.gross_sales,cost:m.variable_cost,marketing:m.marketing_spend,
      contribution:m.modeled_contribution,repeat:m.repeat_orders,proposals,
      drafts:proposals.filter(p=>p.state==="REVIEW_REQUIRED").length,
      deferred:proposals.filter(p=>p.state==="DEFERRED_NOT_GOAL_RELEVANT").length,
      suppressed:proposals.filter(p=>p.state.startsWith("SUPPRESSED_")).length
    };
  }

  function text(id, value) {
    const element = byId(id);
    if (element) element.textContent = String(value);
  }

  function setView(view, focus) {
    activeView = view;
    for (const tab of tabs) {
      const current = tab.dataset.view === view;
      tab.setAttribute("aria-selected",String(current));
      tab.setAttribute("tabindex",current ? "0" : "-1");
      tab.classList.toggle("is-active",current);
      if (current && focus) tab.focus();
    }
    for (const panel of document.querySelectorAll("[role=tabpanel]")) {
      panel.hidden = panel.id !== "panel-" + view;
    }
  }

  for (const tab of tabs) {
    tab.addEventListener("click", () => setView(tab.dataset.view,false));
    tab.addEventListener("keydown", event => {
      const at = tabs.indexOf(tab);
      let next = at;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (at+1)%tabs.length;
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (at-1+tabs.length)%tabs.length;
      else if (event.key === "Home") next=0;
      else if (event.key === "End") next=tabs.length-1;
      else return;
      event.preventDefault();
      setView(tabs[next].dataset.view,true);
    });
  }

  function inspectProposal(proposal) {
    lastInspected = proposal.id;
    const status = proposal.state === "REVIEW_REQUIRED" ? "Draft for review" :
      proposal.state === "DEFERRED_NOT_GOAL_RELEVANT" ? "Outside current goal" : "Suppressed";
    text("inspection-panel",
      status + ": " + proposal.title + ". " + proposal.detail + " " +
      proposal.reason + " No network request, approval, delivery or saved change occurred.");
    byId("inspection-panel").focus();
  }

  function queueRow(proposal) {
    const row = document.createElement("article");
    row.className="queue-row";
    const body = document.createElement("div");
    const code = document.createElement("small");
    code.textContent = proposal.kind.replaceAll("_"," ") + " · WORKFLOW SCENARIO";
    const title = document.createElement("h3");
    title.textContent = proposal.title;
    const desc = document.createElement("p");
    desc.textContent = proposal.detail;
    body.append(code,title,desc);

    const side = document.createElement("div");
    side.className="queue-side";
    const badge=document.createElement("strong");
    badge.textContent=proposal.state === "REVIEW_REQUIRED" ? "REVIEW NEEDED" :
      proposal.state === "DEFERRED_NOT_GOAL_RELEVANT" ? "OUTSIDE GOAL" : "SUPPRESSED";
    if (proposal.state === "DEFERRED_NOT_GOAL_RELEVANT") badge.className="deferred";
    else if (proposal.state !== "REVIEW_REQUIRED") badge.className="suppressed";
    const button=document.createElement("button");
    button.type="button";
    button.textContent="View workflow";
    button.setAttribute("aria-label","Inspect " + proposal.title + " workflow");
    button.addEventListener("click",()=>inspectProposal(proposal));
    side.append(badge,button);
    row.append(body,side);
    return row;
  }

  function render() {
    const data = DEMOS[selectedWorkspace];
    const metrics = evaluate(data);
    text("stat-sales",shortMoney(metrics.sales));
    text("stat-contribution",shortMoney(metrics.contribution));
    text("stat-repeat",metrics.repeat);
    text("stat-queue",metrics.drafts);
    text("nav-count",metrics.drafts);
    text("ledger-sales",shortMoney(metrics.sales));
    text("ledger-cost","− "+shortMoney(metrics.cost));
    text("ledger-spend","− "+shortMoney(metrics.marketing));
    text("ledger-result",shortMoney(metrics.contribution));
    text("opportunity-copy",data.opportunity);
    text("queue-ready",metrics.drafts + " for review");
    text("queue-suppressed",metrics.suppressed + " suppressed");
    text("queue-deferred",metrics.deferred + " outside goal");
    text("goal-target",shortMoney(demoTarget));
    text("goal-current",shortMoney(metrics.contribution) + " modeled");
    const delta=demoTarget-metrics.contribution;
    text("goal-gap",delta > 0 ? shortMoney(delta) + " to goal" : "Target reached in this scenario");
    const percent=Math.min(100,Math.max(0,Math.round(metrics.contribution/demoTarget*100)));
    byId("goal-bar").style.width=percent+"%";
    byId("goal-progress").setAttribute("aria-valuenow",String(percent));
    byId("goal-progress").setAttribute("aria-valuetext",percent+" percent of synthetic target");
    const explanatory={
      contribution:"Explore how revenue, direct costs and marketing spend affect contribution.",
      repeat:"Explore how repeat-order signals are identified. Customer retention requires real verified purchase data.",
      orders:"Explore completed-order insights. Real checkout reporting requires an authorized commerce connection."
    };
    text("goal-explainer",explanatory[goal.value]);
    queue.replaceChildren(...metrics.proposals.map(queueRow));
    if (lastInspected !== null) {
      lastInspected=null;
      text("inspection-panel","Business view updated. Select a workflow to explore its approval requirements. No actions have been executed.");
    }
  }

  business.addEventListener("change",()=>{
    if (!Object.hasOwn(DEMOS,business.value)) return;
    selectedWorkspace=business.value;
    demoTarget=DEMOS[selectedWorkspace].target;
    target.value=String(demoTarget);
    target.min=selectedWorkspace==="academy_demo"?"5000":"5000";
    target.max=selectedWorkspace==="academy_demo"?"50000":"30000";
    render();
  });
  goal.addEventListener("change",render);
  target.addEventListener("input",()=>{
    demoTarget=Number(target.value);
    render();
  });
  byId("open-queue").addEventListener("click",()=>{
    setView("automations",false);
    byId("tab-automations").focus();
  });
  byId("inspection-panel").setAttribute("tabindex","-1");
  render();
  setView(activeView,false);
})();
