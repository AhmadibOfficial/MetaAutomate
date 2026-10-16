/* P2-03o — Offline 12-module intelligence lab. No requests, storage, accounts or external effects. */
(() => {
  "use strict";
  const CATALOG = [
    ["objective","Objective Workspace","Translate objectives into measurable, reviewable business goals."],
    ["value","Business Value Intelligence","Follow changes in sales, identified costs and modeled contribution."],
    ["decision","Decision Intelligence","Explore hypothetical trade-offs without pretending to forecast earnings."],
    ["growth","Growth Autopilot","Review goal-specific workflow recommendations and safeguards."],
    ["crm","CRM Intelligence","Assess illustrative contact coverage and consent-first follow-up needs."],
    ["inventory","Inventory Intelligence","Identify sample reorder thresholds and working stock exposure."],
    ["finance","Financial Intelligence","Compare known expense categories against an illustrative budget."],
    ["marketing","Marketing Intelligence","Review content queues and engagement without inventing sales attribution."],
    ["commerce","Sales & Commerce Intelligence","Inspect orders, quotes and commerce activity, without false conversion claims."],
    ["workflow","Workflow Automation","Manage local review plans; nothing is approved for sending."],
    ["operations","Operations & Workforce Intelligence","Review workload and operational backlog without invented time savings."],
    ["executive","Executive Intelligence","See a single evidence-labeled operational snapshot."]
  ];
  const ENGINES = [
    ["01","Measurement","Facts, costs and period changes"],
    ["02","Decision","Transparent what-if arithmetic"],
    ["03","Recommendation","Ranked evidence needs"],
    ["04","Automation","Human review; no dispatch"],
    ["05","Learning","Descriptive comparisons, not causation"]
  ];
  const costs = ["variable_cost","marketing_spend","processing_fees",
                 "fulfillment_cost","software_cost","refunds"];
  const $ = id => document.getElementById(id);
  const data = window.MetaAutomateSuiteData;
  const growth = window.GrowthAutopilotPreviewData;
  if (!data || data.schema_version !== 1 || data.classification !== "SYNTHETIC_SOURCE_ONLY"
      || data.units !== "DEMO_CREDITS_NOT_USD"
      || !growth || growth.source !== "P2-03j_GOAL_ORCHESTRATION") {
    $("module-content").textContent = "Illustrative source evidence is unavailable. No figures will be displayed.";
    return;
  }
  let active = "objective";
  const state = {tasks:{academy_demo:[],bespoke_demo:[]},price:0,orders:0,unit:0};
  const nf = new Intl.NumberFormat("en-US",{maximumFractionDigits:0});
  const num = x => nf.format(x);
  const money = x => (x < 0 ? "−" : "") + num(Math.abs(x)) + " demo credits";
  const short = x => (x < 0 ? "−" : "") + num(Math.abs(x));
  const safe = x => String(x).replace(/[&<>"']/g, ch=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  })[ch]);
  const label = x => x.replaceAll("_"," ").replace(/\b\w/g, x=>x.toUpperCase());
  const el = (tag,cls,txt) => {const e=document.createElement(tag); if(cls)e.className=cls; e.textContent=txt;return e;};
  const selected = () => $("business").value;
  const scenario = () => data.workspaces[selected()];
  const totalCost = d => costs.reduce((sum,key)=>sum+d[key],0);
  const contribution = d => d.gross_sales - totalCost(d);
  const target = b => b==="academy_demo"?20000:15000;
  const percentage = (part,whole) => whole ? (100*part/whole).toFixed(1)+"%" : "Undefined (zero baseline)";
  const guard = (cond,message) => {if(!cond)throw new Error(message);};
  function source() {
    const ws = selected(), goal = $("goal").value, s = scenario();
    const src = growth.workspaces[ws].goals[goal];
    guard(src && src.metrics.gross_sales === s.current.gross_sales
      && src.metrics.variable_cost === s.current.variable_cost
      && src.metrics.marketing_spend === s.current.marketing_spend
      && src.metrics.completed_orders === s.current.completed_orders
      && src.metrics.repeat_orders === s.current.repeat_orders,
      "Financial source does not reconcile with the goal engine");
    guard(s.baseline.days===30 && s.current.days===30, "Incomparable periods");
    return src;
  }
  const card=(heading,amount,sub)=>'<div class="card"><small>'+safe(heading)+'</small><strong>'+
    safe(amount)+'</strong><p>'+safe(sub)+'</p></div>';
  const cards=items=>'<div class="cards">'+items.map(i=>card(...i)).join("")+'</div>';
  const line=(name,val,isTotal=false)=>'<div class="ledger-row'+(isTotal?' total':'')+'"><span>'+
    safe(name)+'</span><strong>'+safe(val)+'</strong></div>';
  const panel=(title,inner)=>'<div class="surface"><h3>'+safe(title)+'</h3>'+inner+'</div>';
  const note=text=>'<p class="callout">'+safe(text)+'</p>';
  const bars=(a,b,name)=> {
    const max = Math.max(1,Math.abs(a),Math.abs(b));
    return '<div class="bar-row"><div class="bar-label"><span>'+safe(name)+' · previous 30 days</span><b>'+safe(short(a))+'</b></div><div class="bar-track"><div class="bar-fill old" style="width:'+Math.round(100*Math.max(0,a)/max)+'%"></div></div></div>'+
      '<div class="bar-row"><div class="bar-label"><span>'+safe(name)+' · current 30 days</span><b>'+safe(short(b))+'</b></div><div class="bar-track"><div class="bar-fill" style="width:'+Math.round(100*Math.max(0,b)/max)+'%"></div></div></div>';
  };
  function recommendations(s) {
    const c=s.current,stock=s.inventory.filter(i=>i.on_hand<i.reorder_point).length;
    const out=[];
    if(contribution(c)<target(selected()))out.push(["TARGET_GAP","HIGH","Review contribution target gap","Verify complete expenses, overhead, customer receipts and the selected baseline."]);
    if(stock)out.push(["STOCK_REVIEW","HIGH","Review items below reorder thresholds","Confirm physical counts, supplier delivery dates and demand context."]);
    if(s.crm.followups_due)out.push(["CONSENTED_FOLLOWUP_REVIEW","MEDIUM","Review followups with verified permission","Confirm contact purpose, current marketing consent and opt-out controls."]);
    if(s.operations.tasks_overdue)out.push(["BACKLOG_REVIEW","MEDIUM","Review outstanding operational tasks","Confirm task owners, capacity and deadlines."]);
    if(s.marketing.drafts>s.marketing.reviewed)out.push(["CONTENT_REVIEW","LOW","Review unfinished content drafts","Check accuracy, brand approvals and publishing permissions."]);
    return out;
  }
  const recommendationsHtml=s=>{
    const items=recommendations(s);
    return '<div class="stack">'+items.map(([id,p,title,evidence])=>{
      const exists=state.tasks[selected()].some(t=>t.code===id);
      return '<div class="recommendation"><div><span class="chip '+p.toLowerCase()+'">'+safe(p)+' PRIORITY · SYNTHETIC</span><h3>'+safe(title)+'</h3><p>Evidence required: '+safe(evidence)+'</p></div><button class="action-button" type="button" data-add="'+safe(id)+'" '+(exists?'disabled':'')+'>'+(exists?'Added to local plan':'Add to local plan')+'</button></div>';
    }).join("")+'</div>'+note("Rankings are simple review rules over illustration data. They are not validated financial opportunities.");
  };
  function simulation(s) {
    const p=state.price,o=state.orders,u=state.unit,c=s.current;
    const gross=Math.floor(c.gross_sales*(10000+p)*(10000+o)/100000000);
    const variable=Math.floor(c.variable_cost*(10000+u)*(10000+o)/100000000);
    const other=totalCost(c)-c.variable_cost;
    return {gross,identifiedCosts:variable+other,contribution:gross-variable-other};
  }
  function slider(name,id,value){
    return '<label class="slider-field">'+safe(name)+'<output id="'+id+'-out">'+
      (value>0?'+':'')+ (value/100).toFixed(0)+'%</output><input id="'+id+
      '" aria-label="'+safe(name)+'" type="range" min="-5000" max="5000" step="500" value="'+value+'"></label>';
  }
  function moduleHtml(id,s,src) {
    const c=s.current,b=s.baseline,cost=totalCost(c),previous=contribution(b);
    const gap=Math.max(0,target(selected())-contribution(c));
    const wf=Object.values(src.decisions);
    const review=wf.filter(i=>i.state==="PROPOSED_HUMAN_REVIEW_ONLY").length;
    const suppressed=wf.filter(i=>i.state.startsWith("SUPPRESSED")).length;
    const deferred=wf.filter(i=>i.state.startsWith("DEFERRED")).length;
    switch(id) {
      case "objective":
        return cards([["Selected objective",$("goal").options[$("goal").selectedIndex].text,"Demonstration goal, not a live business setting"],
          ["Contribution target",short(target(selected())),"Illustrative 30-day target"],
          ["Gap to selected target",short(gap),"Modeled contribution vs. target"]])+
          note("Define the owner, metric, baseline, review date and cost coverage before treating a target as operational.");
      case "value":
        return '<div class="split">'+panel("Financial comparison",bars(b.gross_sales,c.gross_sales,"Gross sales")+
          bars(previous,contribution(c),"Contribution after identified costs"))+
          panel("Cost waterfall",'<div class="ledger">'+line("Gross sales",money(c.gross_sales))+
          costs.map(k=>line(label(k),money(c[k]))).join("")+
          line("Modeled contribution",money(contribution(c)),true)+'</div>')+'</div>'+
          note("Contribution is NOT net profit. Taxes, complete overhead and other unmeasured costs are excluded.");
      case "decision": {
        const sim=simulation(s);
        return '<div class="surface"><h3>Explore a decision scenario</h3><p>Adjust assumptions; results are arithmetic possibilities, not demand predictions.</p><div class="slider-grid">'+
          slider("Unit price change","price",state.price)+slider("Order quantity change","orders",state.orders)+slider("Variable unit cost change","unit",state.unit)+
          '</div></div><div class="cards" style="margin-top:14px">'+
          card("Illustrative sales",short(sim.gross),"No prediction of buyer behavior")+
          card("Illustrative known costs",short(sim.identifiedCosts),"Other known costs held constant")+
          card("Illustrative contribution",short(sim.contribution),"Difference vs. present: "+short(sim.contribution-contribution(c)))+
          '</div>'+note("Assumes independent price/order changes, scaled variable costs and fixed other identified costs. Omits elasticity, tax, overhead and causal effects.");
      }
      case "growth":
        return cards([["Reviewable proposals",String(review),"Requires human inspection"],["Suppressed proposals",String(suppressed),"Consent and provider ownership"],["Deferred proposals",String(deferred),"Outside selected goal"]])+
          panel("Safeguarded workflow decisions",'<div class="ledger">'+
          Object.entries(src.decisions).map(([event,decision])=>line(event,label(decision.state))).join("")+'</div>')+
          note("Zero messages sent, zero approved deliveries. Selar-owned reminders and unverified marketing consent remain suppressed.")+'<p class="callout"><strong>Facebook lead generation:</strong> Review the four-stage, permission-first <a href="/intelligence-lab/facebook/" style="text-decoration:underline;color:#0765a7">Facebook Lead Ads lab</a>, including the difference between an opened form and a submitted lead. No personal data is retrieved.</p>'+'<p class="callout"><strong>Instagram lead generation:</strong> Explore consent-first lead forms, inbound DMs, comment keywords and human handover in the <a href="/intelligence-lab/instagram/" style="text-decoration:underline;color:#0765a7">Instagram lead intelligence lab</a>. No DMs, ads or real customer leads are activated.</p>'+'<p class="callout"><strong>WhatsApp lead generation:</strong> Explore policy-screened acquisition, qualification and handover in our <a href="/intelligence-lab/whatsapp/" style="color:#0765a7;text-decoration:underline">four-step lead pipeline lab</a>. No messaging is enabled.</p>';
      case "crm":
        return cards([["Illustrative active contacts",String(s.crm.active_contacts),"No names or personal information"],
          ["Consented in sample",String(s.crm.consented_contacts),percentage(s.crm.consented_contacts,s.crm.active_contacts)+" of sample contacts"],
          ["Followups awaiting review",String(s.crm.followups_due),"No outreach enabled"]])+
          note("These are invented aggregate counts; actual consent, purpose limitation and unsubscribe compliance are not verified.")+'<p class="callout"><strong>Facebook lead generation:</strong> Review the four-stage, permission-first <a href="/intelligence-lab/facebook/" style="text-decoration:underline;color:#0765a7">Facebook Lead Ads lab</a>, including the difference between an opened form and a submitted lead. No personal data is retrieved.</p>'+'<p class="callout"><strong>Instagram lead generation:</strong> Explore consent-first lead forms, inbound DMs, comment keywords and human handover in the <a href="/intelligence-lab/instagram/" style="text-decoration:underline;color:#0765a7">Instagram lead intelligence lab</a>. No DMs, ads or real customer leads are activated.</p>'+'<p class="callout"><strong>WhatsApp lead generation:</strong> Explore policy-screened acquisition, qualification and handover in our <a href="/intelligence-lab/whatsapp/" style="color:#0765a7;text-decoration:underline">four-step lead pipeline lab</a>. No messaging is enabled.</p>';
      case "inventory":
        return '<div class="table-wrap"><table class="table"><caption>Illustrative inventory positions, not a live stock ledger</caption><thead><tr><th>Item</th><th>On hand</th><th>Threshold</th><th>Suggested review</th><th>Demo stock value</th></tr></thead><tbody>'+
          s.inventory.map(i=>'<tr><td>'+safe(i.sku)+'</td><td>'+short(i.on_hand)+'</td><td>'+short(i.reorder_point)+'</td><td>'+safe(i.on_hand<i.reorder_point?'Review '+short(i.reorder_point-i.on_hand)+' units':'Above threshold')+'</td><td>'+safe(short(i.on_hand*i.unit_cost))+'</td></tr>').join("")+'</tbody></table></div>'+
          note("Reorder thresholds are synthetic and do not constitute a demand forecast or purchasing authorization.");
      case "finance":
        return cards([["Gross sales",short(c.gross_sales),"Illustrative order gross"],["Identified expenses",short(cost),"Six explicit cost groups"],
          ["Cost vs. example budget",short(cost-s.identified_cost_budget),"Positive means above selected cost plan"]])+
          '<div class="split" style="margin-top:14px">'+panel("Financial ledger",'<div class="ledger">'+costs.map(k=>line(label(k),money(c[k]))).join("")+line("Total identified costs",money(cost),true)+'</div>')+
          panel("Financial coverage",'<p>Cash balance: not established.</p><p>Accounts payable: not established.</p><p>Tax and full fixed overhead: not established.</p><p>Verified profit: unavailable.</p>')+'</div>'+'<p class="callout"><strong>Business continuity and operating-cost intelligence:</strong> Explore the <a href="/intelligence-lab/continuity/" style="text-decoration:underline;color:#0765a7">90-day resilience and expenditure workspace</a> with transparent stress scenarios. All examples are synthetic.</p>';
      case "marketing":
        return cards([["Sample impressions",short(s.marketing.impressions),"Channel engagement, not buyers"],["Sample clicks",short(s.marketing.clicks),percentage(s.marketing.clicks,s.marketing.impressions)+" illustrative click-through"],
          ["Drafts awaiting review",short(s.marketing.drafts-s.marketing.reviewed),"No posts published"]])+
          note("Engagement is not revenue. No campaign attribution, verified conversions, consented audiences, publishing or scheduling.")+'<p class="callout"><strong>Facebook lead generation:</strong> Review the four-stage, permission-first <a href="/intelligence-lab/facebook/" style="text-decoration:underline;color:#0765a7">Facebook Lead Ads lab</a>, including the difference between an opened form and a submitted lead. No personal data is retrieved.</p>'+'<p class="callout"><strong>Instagram lead generation:</strong> Explore consent-first lead forms, inbound DMs, comment keywords and human handover in the <a href="/intelligence-lab/instagram/" style="text-decoration:underline;color:#0765a7">Instagram lead intelligence lab</a>. No DMs, ads or real customer leads are activated.</p>';
      case "commerce":
        return cards([["Completed sample orders",short(c.completed_orders),"Validated P2-03j source"],["Gross revenue",short(c.gross_sales),"Not net receipts or verified profit"],
          ["Sample quotes",short(s.sales.quotes),"Not a common conversion cohort"]])+
          '<div class="split" style="margin-top:14px">'+panel("Illustrative commerce signals",'<div class="ledger">'+
          line("Cart examples",short(s.sales.carts))+line("Handled sample returns",short(s.sales.returns_handled))+
          line("Refund deduction",money(c.refunds))+line("Repeat-order events",short(c.repeat_orders))+'</div>')+
          panel("What is not measured","<p>Funnel conversion rate, actual payment settlement, customer lifetime value and provider attribution require verified event definitions and real authorized inputs.</p>")+'</div>';
      case "workflow": {
        const tasks=state.tasks[selected()];
        return cards([["Reviewable workflow proposals",short(review),"Not permitted to send"],["Local plan tasks",short(tasks.length),"Ephemeral page state"],["Suppressed by policy",short(suppressed),"Controls cannot be overridden"]])+
        '<h3 style="margin-top:20px">Human-managed local plan</h3><div class="stack">'+
        (tasks.length?tasks.map((t,i)=>'<div class="recommendation"><div><strong>'+safe(label(t.code))+'</strong><p>Status: '+safe(t.state.replaceAll("_"," "))+' · This browser only</p></div>'+
          (t.state==="COMPLETED"||t.state==="DISMISSED"?"<span class='chip'>Closed</span>":
          '<button type="button" class="action-button secondary" data-step="'+i+'">'+safe(t.state==="PROPOSED"?"Mark reviewed":t.state==="REVIEWED"?"Start work":"Mark completed")+'</button>')+'</div>').join(""):
          '<div class="surface"><p>No local tasks yet. Choose a recommendation below to create one.</p></div>')+
          '</div><h3 style="margin-top:22px">Available review recommendations</h3>'+recommendationsHtml(s)+
          note("Local review states are not authenticated approvals. No real workflows, notifications or external jobs can be triggered.");
      }
      case "operations":
        return cards([["Open tasks",short(s.operations.tasks_open),"Illustrative workload"],["Completed tasks",short(s.operations.tasks_completed),"Illustrative period"],["Overdue tasks",short(s.operations.tasks_overdue),percentage(s.operations.tasks_overdue,s.operations.tasks_open)+" of open tasks"]])+
          note("Observed staff minutes do not prove automation saved time. No staff identities or employee records are stored.")+'<p class="callout"><strong>Business continuity and operating-cost intelligence:</strong> Explore the <a href="/intelligence-lab/continuity/" style="text-decoration:underline;color:#0765a7">90-day resilience and expenditure workspace</a> with transparent stress scenarios. All examples are synthetic.</p>';
      case "executive":
        return cards([["Contribution after known costs",short(contribution(c)),"Not net profit"],["Known-cost share",percentage(cost,c.gross_sales),"Of illustrative gross sales"],["Priority reviews",short(recommendations(s).length),"Rules need real-world evidence"]])+
          '<h3 style="margin-top:22px">Opportunities worth investigating</h3>'+recommendationsHtml(s)+
          note("Executive findings are descriptive across example data, with no real integrations or proven incremental income.")+'<p class="callout"><strong>Business continuity and operating-cost intelligence:</strong> Explore the <a href="/intelligence-lab/continuity/" style="text-decoration:underline;color:#0765a7">90-day resilience and expenditure workspace</a> with transparent stress scenarios. All examples are synthetic.</p>';
      default:return '<p>This module is not available in the current preview.</p>';
    }
  }
  function render() {
    try {
      const s=scenario(),src=source(),c=s.current,b=s.baseline,cc=contribution(c),prev=contribution(b);
      const kpi=[
        ["Gross sales",short(c.gross_sales),"Previous: "+short(b.gross_sales)],
        ["Identified costs",short(totalCost(c)),"Six known categories"],
        ["Modeled contribution",short(cc),"Previous: "+short(prev)],
        ["Completed orders",String(c.completed_orders),"Repeat-order events: "+c.repeat_orders],
      ];
      $("kpis").innerHTML=kpi.map(row=>'<div class="kpi"><small>'+safe(row[0])+'</small><strong>'+safe(row[1])+'</strong><span>'+safe(row[2])+'</span></div>').join("");
      const ix=CATALOG.findIndex(item=>item[0]===active);
      $("module-count").textContent="MODULE / "+String(ix+1).padStart(2,"0");
      $("module-title").textContent=CATALOG[ix][1];
      $("module-desc").textContent=CATALOG[ix][2];
      $("module-content").innerHTML=moduleHtml(active,s,src);
      for(const button of document.querySelectorAll(".module-nav")){
        const selected=button.dataset.module===active;
        button.classList.toggle("active",selected);
        button.setAttribute("aria-pressed",String(selected));
      }
      $("engines").innerHTML=ENGINES.map(row=>'<div class="engine"><span>'+row[0]+' / ENGINE</span><strong>'+safe(row[1])+'</strong><p>'+safe(row[2])+'</p></div>').join("");
    } catch(e) {
      $("kpis").textContent="";
      $("module-content").textContent="The source evidence did not reconcile. The dashboard is disabled.";
      console.error("Source validation failed:",e.message);
    }
  }
  const nav=$("modules");
  for(const [i,item] of CATALOG.entries()){
    const btn=el("button","module-nav","");btn.type="button";btn.dataset.module=item[0];
    btn.setAttribute("aria-pressed",String(i===0));
    btn.append(el("span","number",String(i+1).padStart(2,"0")),el("span","",item[1]));
    btn.addEventListener("click",()=>{active=item[0];render();$("module-title").focus({preventScroll:true});});
    nav.append(btn);
  }
  $("module-title").setAttribute("tabindex","-1");
  $("business").addEventListener("change",()=>{state.price=0;state.orders=0;state.unit=0;render();});
  $("goal").addEventListener("change",render);
  $("module-content").addEventListener("input",e=>{
    if(!["price","orders","unit"].includes(e.target.id))return;
    const n=Number(e.target.value);
    if(!Number.isInteger(n)||n<-5000||n>5000)return;
    state[e.target.id]=n;
    const out=$(e.target.id+"-out");
    if(out)out.textContent=(n>0?"+":"")+(n/100).toFixed(0)+"%";
  });
  $("module-content").addEventListener("change",e=>{
    if(["price","orders","unit"].includes(e.target.id))render();
  });
  $("module-content").addEventListener("click",e=>{
    const add=e.target.closest("[data-add]"),next=e.target.closest("[data-step]");
    if(add){
      const code=add.dataset.add;
      if(recommendations(scenario()).some(r=>r[0]===code) &&
         !state.tasks[selected()].some(t=>t.code===code))
        state.tasks[selected()].push({code,state:"PROPOSED"});
      render();
    }else if(next){
      const ix=Number(next.dataset.step),tasks=state.tasks[selected()],t=tasks[ix];
      if(!Number.isInteger(ix)||!t)return;
      const states={PROPOSED:"REVIEWED",REVIEWED:"IN_PROGRESS",IN_PROGRESS:"COMPLETED"};
      if(states[t.state])t.state=states[t.state];
      render();
    }
  });
  render();
})();
