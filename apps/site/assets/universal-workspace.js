/* P2-064 — interactive, browser-local problem-first workspace.
 * No remote provider calls, storage, code execution, account creation or external side effects.
 * Domain options are derived from reviewed P2-063 metadata at build time.
 * Catalog options are navigation labels only; they DO NOT activate domain packs.
 */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const SECTORS = Object.freeze([{"value":"sales_customer_service","label":"Sales & Customer Service"},{"value":"healthcare_administration","label":"Healthcare Administration"},{"value":"real_estate","label":"Real Estate"},{"value":"retail","label":"Retail"},{"value":"wholesale","label":"Wholesale & Distribution"},{"value":"cloud_it","label":"Cloud & Enterprise IT"},{"value":"transportation","label":"Transportation"},{"value":"logistics","label":"Logistics & Supply Chain"},{"value":"tourism","label":"Tourism"},{"value":"hospitality","label":"Hotels & Hospitality"},{"value":"education","label":"Education & Training"},{"value":"manufacturing","label":"Manufacturing"},{"value":"agriculture","label":"Agriculture & Agribusiness"},{"value":"construction","label":"Construction & Facilities"},{"value":"financial_operations","label":"Finance & Insurance Administration"},{"value":"telecommunications","label":"Telecommunications"},{"value":"energy_utilities","label":"Energy & Utilities"},{"value":"public_services","label":"Public Administration"},{"value":"legal_professional","label":"Legal & Professional Services"},{"value":"media_marketing","label":"Media & Marketing"},{"value":"nonprofit","label":"Nonprofits & Community Organizations"},{"value":"custom_operations","label":"Custom Organization Workflow"}]);
  const GOALS = Object.freeze({
    customers: {
      name:"Customer experience",
      tasks:["Identify the service journey and current bottleneck","Draft a customer response or follow-up process","Review the proposal and responsible team","Define a measurable improvement in service quality"]
    },
    operations:{
      name:"Business operations",
      tasks:["Describe the existing operational process","Identify delays, dependencies and exceptions","Prepare a clearer sequence of responsibilities","Define how operational efficiency could be measured"]
    },
    costs:{
      name:"Costs & finance",
      tasks:["Identify cost categories and a suitable approved baseline","Review potential sources of overspending or waste","Prepare recommendations for authorized review","Specify the evidence needed to measure any savings"]
    },
    automation:{
      name:"Intelligent automation",
      tasks:["Identify the repetitive task and its required inputs","Outline a proposed workflow with necessary safeguards","Specify human approval and authorization gates before execution","Define how completed actions would be verified"]
    },
    insights:{
      name:"Business intelligence",
      tasks:["Define the decision to make and the relevant metrics","Identify approved data sources and quality checks","Prepare an explainable business analysis plan","Set criteria for evaluating the recommendation"]
    }
  });
  const ROUTES=Object.freeze({home:"Home",work:"My Work",results:"Results",settings:"Team & Settings"});
  const industryLabels = new Map(SECTORS.map(s=>[s.value,s.label]));
  let goal="operations", items=[], selectedId=null, nextId=0, events=[], toastToken=null;
  const browserScope = "LOCAL_TAB_ONLY";
  const safeInput = (text,max) => typeof text==="string" && text.trim().length<=max &&
    !/[\u0000-\u001f\u007f<>]/.test(text) && !/^\s*[=+@]/.test(text);
  const announce = message => {
    const node=$("live-status");
    node.textContent=message;node.classList.add("visible");
    if(toastToken!==null)clearTimeout(toastToken);
    toastToken=setTimeout(()=>node.classList.remove("visible"),4200);
  };
  function navigate(){
    const route=location.hash.substring(1);
    const active=Object.hasOwn(ROUTES,route)?route:"home";
    for(const key of Object.keys(ROUTES))$("view-"+key).hidden=key!==active;
    for(const nav of document.querySelectorAll(".side-links a[data-route]")){
      nav.dataset.route===active?nav.setAttribute("aria-current","page"):nav.removeAttribute("aria-current");
    }
    $("route-name").textContent=ROUTES[active];
    document.title=ROUTES[active]+" — MetaAutomate";
    closeMenu();
  }
  function closeMenu(){
    $("sidebar").classList.remove("open");
    $("menu-toggle").setAttribute("aria-expanded","false");
  }
  $("menu-toggle").addEventListener("click",()=>{
    const open=$("sidebar").classList.toggle("open");
    $("menu-toggle").setAttribute("aria-expanded",String(open));
  });
  window.addEventListener("hashchange",navigate);
  document.addEventListener("keydown",event=>{if(event.key==="Escape")closeMenu();});
  for(const anchor of document.querySelectorAll('a[data-route]'))
    anchor.addEventListener("click",()=>{if(location.hash===anchor.getAttribute("href"))navigate();});
  function selectGoal(key){
    if(!Object.hasOwn(GOALS,key))return;
    goal=key;
    for(const button of document.querySelectorAll("[data-goal]"))
      button.setAttribute("aria-pressed",String(button.dataset.goal===goal));
  }
  for(const button of document.querySelectorAll("[data-goal]"))
    button.addEventListener("click",()=>selectGoal(button.dataset.goal));
  const selector=$("industry");
  for(const entry of SECTORS){
    const option=document.createElement("option");
    option.value=entry.value;
    option.textContent=entry.label;
    selector.appendChild(option);
  }
  const selectedGoalFromUrl = new URLSearchParams(location.search).get("goal");
  selectGoal(Object.hasOwn(GOALS,selectedGoalFromUrl)?selectedGoalFromUrl:"operations");
  selector.value=industryLabels.has(new URLSearchParams(location.search).get("sector"))
    ?new URLSearchParams(location.search).get("sector"):"sales_customer_service";
  function toggleCustom(){
    const custom=selector.value==="custom_operations";
    $("custom-sector-group").hidden=!custom;
    $("custom-sector").required=custom;
    if(!custom)$("custom-sector").value="";
  }
  selector.addEventListener("change",toggleCustom);
  toggleCustom();
  const current = () => items.find(plan=>plan.id===selectedId)||null;
  function trace(code){events.push({event:code,clientTimeUnverified:new Date().toISOString()});events=events.slice(-40);renderResults();}
  $("project-form").addEventListener("submit",event=>{
    event.preventDefault();
    const sector=selector.value;
    const note=$("challenge").value.trim();
    const custom=$("custom-sector").value.trim();
    if(!industryLabels.has(sector)){announce("Choose an industry from the list.");return;}
    if(!safeInput(note,240) || (sector==="custom_operations"&&(!custom || !safeInput(custom,70)))){
      announce("Use short, non-sensitive plain text without control characters or formulas.");return;
    }
    if(items.length>=12){announce("This local session has reached the twelve-workflow limit. Clear the session when finished.");return;}
    const industry=sector==="custom_operations"?custom:industryLabels.get(sector);
    const id=++nextId;
    items.push({id,goal,industry,description:note||"Improve this business process",
      steps:GOALS[goal].tasks.map(title=>({title,done:false})),reviewed:false});
    selectedId=id;$("challenge").value="";
    trace("WORKFLOW_CREATED");
    renderWork();renderResults();
    location.hash="#work";
    navigate();announce("Workflow created for your review. No external action was performed.");
  });
  function renderWork(){
    const list=$("workflow-list");
    list.replaceChildren();
    $("work-count").textContent=String(items.length);
    $("nav-count").textContent=String(items.length);
    $("nav-count").hidden=items.length===0;
    $("empty-work").hidden=items.length>0;
    for(const plan of items){
      const button=document.createElement("button");
      button.type="button";button.className="workflow-choice";
      button.setAttribute("aria-pressed",String(plan.id===selectedId));
      const name=document.createElement("strong");name.textContent=GOALS[plan.goal].name;
      const sub=document.createElement("span");
      sub.textContent=plan.industry+" · "+(plan.reviewed?"Reviewed":"Needs review");
      button.append(name,sub);
      button.addEventListener("click",()=>{selectedId=plan.id;renderWork();});
      list.appendChild(button);
    }
    const plan=current();
    $("workflow-detail").hidden=!plan;
    if(!plan)return;
    $("workflow-title").textContent=GOALS[plan.goal].name;
    $("workflow-description").textContent=plan.industry+" · "+plan.description;
    $("workflow-status").textContent=plan.reviewed?"Reviewed":"Awaiting review";
    $("workflow-status").classList.toggle("done",plan.reviewed);
    const steps=$("workflow-steps");steps.replaceChildren();
    plan.steps.forEach((step,index)=>{
      const li=document.createElement("li");
      const label=document.createElement("label");
      const input=document.createElement("input");input.type="checkbox";input.checked=step.done;input.disabled=plan.reviewed;
      const span=document.createElement("span");span.textContent=step.title;
      input.addEventListener("change",()=>{
        step.done=input.checked;plan.reviewed=false;$("review-confirm").checked=false;
        updateReviewState();trace("STEP_REVIEW_CHANGED");
      });
      label.append(input,span);li.appendChild(label);steps.appendChild(li);
    });
    $("review-confirm").checked=plan.reviewed;
    $("review-confirm").disabled=plan.reviewed;
    $("review-message").textContent=plan.reviewed?
      "Review recorded locally. No business action has been executed.":"Review is required before completion is recorded.";
    updateReviewState();
  }
  function updateReviewState(){
    const plan=current(),count=plan?plan.steps.filter(s=>s.done).length:0;
    $("progress-fill").style.width=(count*25)+"%";
    $("progress-count").textContent=count+" of 4";
    $("complete-workflow").disabled=!plan||plan.reviewed||count!==4||!$("review-confirm").checked;
  }
  $("review-confirm").addEventListener("change",updateReviewState);
  $("complete-workflow").addEventListener("click",()=>{
    const plan=current();
    if(!plan||plan.reviewed||!$("review-confirm").checked||!plan.steps.every(s=>s.done))return;
    plan.reviewed=true;trace("WORKFLOW_REVIEW_RECORDED");
    renderWork();announce("Human review recorded locally. No business operation was executed.");
  });
  function renderResults(){
    $("metric-created").textContent=String(items.length);
    $("metric-reviewed").textContent=String(items.filter(p=>p.reviewed).length);
    $("metric-steps").textContent=String(items.reduce((sum,p)=>sum+p.steps.filter(s=>s.done).length,0));
    $("export-report").disabled=items.length===0;
    const records=$("activity-record");records.replaceChildren();
    if(!events.length){
      const p=document.createElement("p");p.textContent="Activity will appear after you create your first workflow.";records.appendChild(p);
    }
    for(const event of events.slice(-8).reverse()){
      const p=document.createElement("p");
      p.textContent=event.event.replaceAll("_"," ")+" · "+event.clientTimeUnverified+" (unverified browser clock)";
      records.appendChild(p);
    }
  }
  function download(name,text,contentType){
    const blob=new Blob([text],{type:contentType}),url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1200);
  }
  $("export-report").addEventListener("click",()=>{
    if(!items.length)return;
    const report={
      schema:"metaautomate.local-activity-v2",
      scope:browserScope,
      generatedAtUnverifiedClientClock:new Date().toISOString(),
      userProvidedInformationUnverified:true,
      independentVerification:false,
      financialSavingsVerified:false,
      externalExecutionPerformed:false,
      aiProviderUsed:false,
      authenticatedCustomerDataUsed:false,
      planCount:items.length,reviewCount:items.filter(p=>p.reviewed).length,
      workflows:items.map(p=>({goal:p.goal,industryCode:"USER_CHOSEN",
        stepsChecked:p.steps.filter(s=>s.done).length,reviewed:p.reviewed})),
      activity:events.slice(-20)
    };
    download("metaautomate-local-workflow-activity.json",JSON.stringify(report,null,2)+"\n","application/json");
    trace("ACTIVITY_REPORT_EXPORTED");
    announce("Local activity record downloaded. No business outcomes have been verified.");
  });
  $("clear-session").addEventListener("click",()=>{
    items=[];selectedId=null;nextId=0;events=[];
    $("challenge").value="";$("custom-sector").value="";
    $("review-confirm").checked=false;
    $("workflow-steps").replaceChildren();
    renderWork();renderResults();
    announce("Local workflow session cleared. No external records were affected.");
  });
  renderWork();renderResults();navigate();
})();