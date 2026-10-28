/* P2-062c — truthful, local-only workflow planning with five industry entries.
   All data is volatile; no APIs, authentication bypass, external actions or model inference. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const engine = globalThis.MetaCampaign;
  const views = ["home", "work", "results", "settings"];
  const viewNames = {home:"Home",work:"My Work",results:"Results",settings:"Team & Settings"};
  const industries = {
    sales: {label:"Sales & Customers",desc:"Keep customer questions and follow-ups organized.",
      example:"A customer asked about a product, but nobody has replied.",
      steps:["Record the inquiry without personal identifiers","Prepare a possible reply for review","Check the information and approve the next action","Record whether a follow-up is needed"]},
    healthcare:{label:"Healthcare",desc:"Make appointments and administrative work easier to manage.",
      example:"An appointment request needs scheduling and staff review.",
      steps:["Describe the administrative task without patient information","Confirm the organization's scheduling requirements","Prepare a staff-review checklist","Record the next administrative follow-up"]},
    realestate:{label:"Real Estate",desc:"Keep property viewing and maintenance requests on track.",
      example:"A property viewing request has not been scheduled.",
      steps:["Record the type of property request","Review appropriate viewing or maintenance options","Prepare a message for agent approval","Record the required follow-up"]},
    retail:{label:"Retail & Stock",desc:"Find stock discrepancies and prepare actions for review.",
      example:"Some products are sitting in stock while others may be running low.",
      steps:["Check the source and age of your stock records","Review stock levels and sales movements","Choose a candidate for human review","Decide whether a follow-up or manual campaign is appropriate"]},
    cloud:{label:"Cloud & IT",desc:"Review technology spending and system issues safely.",
      example:"An approved usage report shows an unexplained change in cloud costs.",
      steps:["Define the cost or reliability question","Review only authorized, non-sensitive metrics","Record a proposed change and potential risks","Request engineering approval before any infrastructure change"]}
  };
  // P2-064: source-only extension choices from the reviewed domain-pack catalog.
  // This local UI does not activate domain packs or execute any external workflow.
  const extraIndustries = Object.freeze({"wholesale":{"label":"Wholesale & Distribution","desc":"Organize and review wholesale & distribution workflows.","example":"Draft stock replenishment and bulk order reviews","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"transportation":{"label":"Transportation","desc":"Organize and review transportation workflows.","example":"Review fleet capacity, assignment and service delays","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"logistics":{"label":"Logistics & Supply Chain","desc":"Organize and review logistics & supply chain workflows.","example":"Plan shipment exception and capacity workflows","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"tourism":{"label":"Tourism","desc":"Organize and review tourism workflows.","example":"Review guest inquiries and itinerary handoffs","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"hospitality":{"label":"Hotels & Hospitality","desc":"Organize and review hotels & hospitality workflows.","example":"Organize room inventory and guest-service requests","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"education":{"label":"Education & Training","desc":"Organize and review education & training workflows.","example":"Prepare class scheduling and enrollment process review","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"manufacturing":{"label":"Manufacturing","desc":"Organize and review manufacturing workflows.","example":"Evaluate production bottlenecks and maintenance plans","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"agriculture":{"label":"Agriculture & Agribusiness","desc":"Organize and review agriculture & agribusiness workflows.","example":"Review commodity inventory, procurement and farm operations","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"construction":{"label":"Construction & Facilities","desc":"Organize and review construction & facilities workflows.","example":"Review work orders, project delays and resource allocations","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"financial_operations":{"label":"Finance & Insurance Administration","desc":"Organize and review finance & insurance administration workflows.","example":"Plan account-service and reconciliation reviews","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"telecommunications":{"label":"Telecommunications","desc":"Organize and review telecommunications workflows.","example":"Review subscriber service operations and capacity planning","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"energy_utilities":{"label":"Energy & Utilities","desc":"Organize and review energy & utilities workflows.","example":"Review maintenance scheduling, asset and consumption reports","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"public_services":{"label":"Public Administration","desc":"Organize and review public administration workflows.","example":"Plan administrative request queues and case review","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"legal_professional":{"label":"Legal & Professional Services","desc":"Organize and review legal & professional services workflows.","example":"Organize document intake and matter follow-up workflows","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"media_marketing":{"label":"Media & Marketing","desc":"Organize and review media & marketing workflows.","example":"Review campaigns, content plans and publication approvals","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"nonprofit":{"label":"Nonprofits & Community Organizations","desc":"Organize and review nonprofits & community organizations workflows.","example":"Plan service request, donor communication and reporting","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"custom_operations":{"label":"Custom Organization Workflow","desc":"Organize and review custom organization workflow workflows.","example":"Capture a business problem outside existing sector templates","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]}});
  const objectiveFamilies = Object.freeze({"customer":{"name":"Customer experience","steps":["Map the customer request and service expectations","Identify the handoff or response bottleneck","Prepare a controlled follow-up proposal for review","Define how the customer outcome will be measured"]},"operations":{"name":"Business operations","steps":["Describe the current process and its constraints","Identify delays, dependencies and exceptions","Propose an accountable sequence of tasks and checks","Set a measurable operational review point"]},"finance":{"name":"Costs & finance","steps":["Define an authorized baseline and cost categories","Identify possible waste or unexpected changes","Prepare a cost review proposal with uncertainty noted","Set evidence requirements before claiming savings"]},"automation":{"name":"Intelligent automation","steps":["Identify a repetitive process and permitted inputs","Map actions, failure handling and human checkpoints","Specify the exact approval and security requirements","Define how execution would later be verified"]},"insights":{"name":"Business intelligence","steps":["Define the business question and useful metrics","Identify authorized data sources and data quality checks","Prepare an explainable analysis and decision proposal","Define outcome measures and evidence provenance"]}});
  let selectedGoal = "operations";
  Object.assign(industries, extraIndustries);
  const sectorLink = /(?:^|[?&])sector=(sales|healthcare|realestate|retail|cloud)(?:&|$)/.exec(location.search || "");
  let selectedIndustry = sectorLink ? sectorLink[1] : "sales", plans = [], selectedId = null, counter = 0;
  let records = null, analysis = null, exampleMode = false, planDraft = null, approvedDraft = false;
  let events = [], generation = 0, toastTimer = null;
  const safeText = value => String(value).trim();
  function announce(message) {
    const element = $("live-status");
    element.textContent = message;
    element.classList.add("visible");
    if (toastTimer !== null) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove("visible"), 4400);
  }
  function log(code) {
    events.push({event:code, clientTime:new Date().toISOString()});
    if (events.length > 100) events.shift();
    drawResults();
  }
  function save(filename, contents, mime) {
    const url = URL.createObjectURL(new Blob([contents], {type:mime}));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function closeMenu() {
    $("sidebar").classList.remove("open");
    $("menu-toggle").setAttribute("aria-expanded","false");
  }
  function navigate() {
    const hash = location.hash.slice(1);
    const name = views.includes(hash) ? hash : "home";
    for (const view of views) $("view-"+view).hidden = view!==name;
    for (const link of document.querySelectorAll(".sidebar-nav a[data-route]")) {
      if(link.dataset.route===name) link.setAttribute("aria-current","page");
      else link.removeAttribute("aria-current");
    }
    $("current-section").textContent=viewNames[name];
    document.title=viewNames[name]+" — MetaAutomate";
    closeMenu();
  }
  $("menu-toggle").addEventListener("click",()=>{
    const open=$("sidebar").classList.toggle("open");
    $("menu-toggle").setAttribute("aria-expanded",String(open));
  });
  document.addEventListener("keydown",e=>{if(e.key==="Escape")closeMenu();});
  window.addEventListener("hashchange",navigate);
  for (const link of document.querySelectorAll("a[data-route]")) {
    link.addEventListener("click",()=>{if(location.hash===link.getAttribute("href"))navigate();});
  }
  function chooseGoal(key) {
    if (!Object.hasOwn(objectiveFamilies,key)) return;
    selectedGoal=key;
    for(const button of document.querySelectorAll("[data-goal]"))
      button.setAttribute("aria-pressed", String(button.dataset.goal===key));
    $("challenge").placeholder = "Describe what you want to improve in "+objectiveFamilies[key].name.toLowerCase()+".";
  }
  for(const button of document.querySelectorAll("[data-goal]"))
    button.addEventListener("click",()=>chooseGoal(button.dataset.goal));
  $("more-industries").addEventListener("change",()=>{
    const choice=$("more-industries").value;
    if(choice && Object.hasOwn(extraIndustries,choice))chooseSector(choice);
    else if(!choice)chooseSector("sales");
  });
  function chooseSector(key) {
    if (!Object.hasOwn(industries,key)) return;
    selectedIndustry=key;
    const current=industries[key];
    if($("more-industries")) {
      $("more-industries").value = Object.hasOwn(extraIndustries,key)?key:"";
      $("industry-selection-status").textContent = Object.hasOwn(extraIndustries,key) ? current.label+" selected for workflow planning." : "Popular business area selected.";
    }
    for(const button of document.querySelectorAll("[data-sector]"))
      button.setAttribute("aria-pressed",String(button.dataset.sector===key));
    $("selected-sector-title").textContent=current.label;
    $("selected-sector-description").textContent=current.desc;
    $("selected-sector-example").textContent=current.example;
    $("challenge").placeholder = "For example: "+current.example;
  }
  for (const button of document.querySelectorAll("[data-sector]")) {
    button.addEventListener("click",()=>chooseSector(button.dataset.sector));
  }
  $("new-work-form").addEventListener("submit",event=>{
    event.preventDefault();
    const industry=industries[selectedIndustry];
    const note=safeText($("challenge").value);
    if (note.length>240 || /[\u0000-\u001f\u007f<>]/.test(note)) {
      announce("Please use plain text without control characters or angle brackets.");return;
    }
    if (plans.length>=15){announce("This local preview supports up to 15 plans. Clear the session to start over.");return;}
    const entry={id:++counter,industry:selectedIndustry,goal:selectedGoal,desc:note||industry.example,
      steps:objectiveFamilies[selectedGoal].steps.map(text=>({text,done:false})),reviewed:false};
    plans.push(entry);
    selectedId=entry.id;
    $("challenge").value="";
    log("LOCAL_PLAN_CREATED");
    renderWork();
    location.hash="#work";
    navigate();
    announce(industry.label+" plan created for your review. No external action occurred.");
  });
  function currentPlan(){return plans.find(p=>p.id===selectedId)||null;}
  function renderWork() {
    $("plan-count").textContent=String(plans.length);
    $("empty-plans").hidden=plans.length>0;
    const container=$("plan-list");
    container.replaceChildren();
    for (const plan of plans) {
      const button=document.createElement("button");
      button.type="button";button.className="plan-button";
      button.setAttribute("aria-pressed",String(plan.id===selectedId));
      const strong=document.createElement("strong");strong.textContent=industries[plan.industry].label;
      const small=document.createElement("small");
      small.textContent=(plan.reviewed?"Reviewed · ":"Needs review · ")+plan.desc.slice(0,75);
      button.append(strong,small);
      button.addEventListener("click",()=>{selectedId=plan.id;renderWork();});
      container.appendChild(button);
    }
    const selected=currentPlan();
    $("plan-detail").hidden=!selected;
    if (!selected) return;
    $("plan-detail-title").textContent=industries[selected.industry].label+" plan";
    $("plan-description").textContent=selected.desc;
    const list=$("plan-steps");list.replaceChildren();
    selected.steps.forEach((step,i)=>{
      const li=document.createElement("li");
      const label=document.createElement("label");label.className="step-check";
      const input=document.createElement("input");input.type="checkbox";input.checked=step.done;input.disabled=selected.reviewed;
      const span=document.createElement("span");span.textContent=step.text;
      input.addEventListener("change",checked=>{
        step.done=!!input.checked;
        selected.reviewed=false;
        $("plan-review").checked=false;
        updatePlanApproval();
        log("LOCAL_CHECKLIST_STEP_CHANGED");
      });
      label.append(input,span);li.appendChild(label);list.appendChild(li);
    });
    $("plan-review").checked=selected.reviewed;
    $("plan-review").disabled=selected.reviewed;
    $("plan-status").textContent=selected.reviewed?"Plan reviewed locally. No real-world task was executed.":"Checklist awaiting internal review.";
    updatePlanApproval();
  }
  function updatePlanApproval(){
    const plan=currentPlan();
    $("complete-plan").disabled=!plan||plan.reviewed||!plan.steps.every(step=>step.done)||!$("plan-review").checked;
  }
  $("plan-review").addEventListener("change",updatePlanApproval);
  $("complete-plan").addEventListener("click",()=>{
    const plan=currentPlan();
    if (!plan||plan.reviewed||!$("plan-review").checked||!plan.steps.every(step=>step.done))return;
    plan.reviewed=true;
    log("LOCAL_PLAN_REVIEW_RECORDED");
    renderWork();
    announce("Review recorded. No customer, clinical, financial or IT action was performed.");
  });
  function dropDraft() {
    planDraft=null;approvedDraft=false;
    $("draft-output").hidden=true;
    $("review-check").checked=false;
    $("copy-draft").disabled=true;
    $("save-draft").disabled=true;
    $("draft-status").textContent="Not reviewed. No publishing is available.";
    $("draft-text").value="";
  }
  function clearInventory() {
    generation++;records=analysis=null;exampleMode=false;
    $("inventory-file").value="";
    $("inventory-results").hidden=true;
    $("inventory-table").replaceChildren();
    $("candidate-select").replaceChildren();
    dropDraft();
    drawResults();
  }
  $("clear-inventory").addEventListener("click",()=>{clearInventory();log("LOCAL_INVENTORY_CLEARED");announce("Inventory cleared from this tab.");});
  $("inventory-file").addEventListener("change",()=>{
    // Invalidate prior analysis but leave the newly selected file intact.
    generation++;records=analysis=null;exampleMode=false;
    $("inventory-results").hidden=true;
    $("inventory-table").replaceChildren();
    $("candidate-select").replaceChildren();
    $("draft-form").hidden=true;
    dropDraft();drawResults();
  });
  $("download-sample").addEventListener("click",()=>{
    save("metaautomate-example-stock.csv",
      "sku,name,stock,weekly_sales,unit_price_kobo\nCAP-01,Example Cap,18,0,850000\nKAF-02,Example Kaftan,24,3,3500000\nSHO-03,Example Shoes,0,5,1200000\n",
      "text/csv;charset=utf-8");
    announce("Sample inventory CSV downloaded.");
  });
  $("inventory-form").addEventListener("submit",async event=>{
    event.preventDefault();
    if(!engine){announce("Inventory tool unavailable.");return;}
    const file=$("inventory-file").files?.[0],token=++generation;
    if(!file||file.size===0||file.size>engine.MAX_BYTES){announce("Choose a nonempty CSV under 128 KB.");return;}
    try {
      const bytes=await file.arrayBuffer();
      if(!bytes.byteLength||bytes.byteLength>engine.MAX_BYTES)throw new Error("CSV size exceeds limit.");
      const text=new TextDecoder("utf-8",{fatal:true}).decode(bytes);
      const data=engine.parseCSV(text),result=engine.analyze(data);
      if(token!==generation || $("inventory-file").files?.[0]!==file)return;
      records=data;analysis=result;exampleMode=false;
      dropDraft();
      renderInventory();
      log("LOCAL_INVENTORY_ANALYZED");
      announce("Stock analyzed locally. Check the results before acting.");
    }catch(error){
      if(token!==generation || $("inventory-file").files?.[0]!==file)return;
      records=analysis=null;dropDraft();$("inventory-results").hidden=true;
      drawResults();announce(error instanceof Error ? "Import rejected: "+error.message : "Import rejected.");
    }
  });
  function renderInventory() {
    if(!analysis)return;
    $("inventory-results").hidden=false;
    $("inventory-summary").textContent=analysis.totalItems+" products checked · "+analysis.flaggedCount+" stock opportunities for review";
    $("inventory-caveat").textContent=exampleMode?"Sample records only. Not customer evidence.":"User-provided records are not independently verified.";
    const table=$("inventory-table");table.replaceChildren();
    for(const item of analysis.evaluated){
      const tr=document.createElement("tr");
      for(const value of [item.name,item.stock,item.weeklySales,item.signal.title]){
        const td=document.createElement("td");td.textContent=String(value);tr.appendChild(td);
      }
      table.appendChild(tr);
    }
    const select=$("candidate-select");select.replaceChildren();
    for(const item of analysis.opportunities){
      const option=document.createElement("option");
      option.value=item.sku;option.textContent=item.name+" · "+item.signal.title;
      select.appendChild(option);
    }
    $("draft-form").hidden=analysis.opportunities.length===0;
  }
  $("draft-form").addEventListener("submit",event=>{
    event.preventDefault();
    const item=analysis?.opportunities.find(candidate=>candidate.sku===$("candidate-select").value);
    if(!engine||!item)return;
    try{
      const draft=engine.makeCampaign(item,$("brand-name").value,$("channel-select").value);
      dropDraft();
      planDraft=draft;
      $("draft-output").hidden=false;
      $("draft-text").value=draft.post;
      $("draft-reason").textContent=draft.reason+". "+draft.recommendation;
      log("LOCAL_MARKETING_DRAFT_CREATED");
      announce("Draft prepared. Approval required before copying or downloading.");
    }catch(error){dropDraft();announce(error instanceof Error ? error.message:"Draft could not be created.");}
  });
  function revokeDraft(){
    if(!planDraft)return;
    const wasApproved=approvedDraft;
    approvedDraft=false;
    $("review-check").checked=false;
    $("copy-draft").disabled=true;$("save-draft").disabled=true;
    $("draft-status").textContent="Draft changed. Review again before using it.";
    if(wasApproved)log("LOCAL_DRAFT_REVIEW_REVOKED");
  }
  ["candidate-select","channel-select","brand-name"].forEach(id=>{
    $(id).addEventListener(id==="brand-name"?"input":"change",()=>{if(planDraft){dropDraft();log("LOCAL_DRAFT_INPUT_CHANGED");}});
  });
  $("draft-text").addEventListener("input",revokeDraft);
  $("review-check").addEventListener("change",()=>{if(!$("review-check").checked)revokeDraft();});
  $("record-review").addEventListener("click",()=>{
    if(!planDraft||!$("review-check").checked||!$("draft-text").value.trim()){
      announce("Review the text and tick the confirmation box first.");return;
    }
    approvedDraft=true;
    $("copy-draft").disabled=false;$("save-draft").disabled=false;
    $("draft-status").textContent="Reviewed for manual copy/download only. Nothing was published.";
    log("LOCAL_DRAFT_REVIEWED");
  });
  $("copy-draft").addEventListener("click",async()=>{
    if(!planDraft||!approvedDraft)return;
    try{await navigator.clipboard.writeText($("draft-text").value);log("LOCAL_DRAFT_COPIED");announce("Text copied. No post sent.");}
    catch{announce("Clipboard unavailable. Download the text instead.");}
  });
  $("save-draft").addEventListener("click",()=>{
    if(!planDraft||!approvedDraft)return;
    save("metaautomate-reviewed-post.txt",$("draft-text").value+"\n","text/plain;charset=utf-8");
    log("LOCAL_DRAFT_DOWNLOADED");
  });
  function drawResults(){
    $("results-plans").textContent=String(plans.length);
    $("results-reviewed").textContent=String(plans.filter(p=>p.reviewed).length);
    $("results-steps").textContent=String(plans.reduce((n,p)=>n+p.steps.filter(s=>s.done).length,0));
    $("results-products").textContent=String(analysis?.totalItems||0);
    $("export-evidence").disabled=plans.length===0&&!analysis;
    const list=$("activity-list");
    list.replaceChildren();
    if(!events.length){const p=document.createElement("p");p.textContent="No activity yet.";list.appendChild(p);}
    for(const entry of events.slice(-20).reverse()){
      const p=document.createElement("p");p.textContent=entry.event.replaceAll("_"," ")+" · "+entry.clientTime+" (device clock)";
      list.appendChild(p);
    }
  }
  $("export-evidence").addEventListener("click",()=>{
    if(!plans.length&&!analysis)return;
    const record={
      schema:"metaautomate.local-work-v1",
      generatedAtUntrustedClientClock:new Date().toISOString(),
      independentlyVerified:false,sourceAuthenticated:false,
      customerTractionVerified:false,revenueVerified:false,
      aiModelUsed:false,externalPublishingPerformed:false,
      outsideActionsPerformed:false,signed:false,
      localPlanCount:plans.length,localReviewedPlanCount:plans.filter(p=>p.reviewed).length,
      completedChecklistsNotExecuted:plans.map(p=>({area:p.industry,reviewed:p.reviewed,checkedSteps:p.steps.filter(s=>s.done).length})),
      inventory:{source:analysis?(exampleMode?"SYNTHETIC_EXAMPLE":"USER_DECLARED_UNVERIFIED"):"NONE",
        products:analysis?.totalItems||0,candidates:analysis?.flaggedCount||0},
      marketingDraftReviewedForManualUse:approvedDraft,
      recentLocalEvents:events.slice(-20)
    };
    save("metaautomate-local-activity-not-verified.json",JSON.stringify(record,null,2)+"\n","application/json");
    log("LOCAL_ACTIVITY_REPORT_DOWNLOADED");
    announce("Self-declared activity record downloaded. No outside results verified.");
  });
  $("clear-session").addEventListener("click",()=>{
    // Deliberately volatile only; clear all locally held state and revoke approvals.
    generation++;plans=[];selectedId=null;counter=0;
    records=analysis=null;exampleMode=false;events=[];dropDraft();
    $("inventory-file").value="";$("inventory-results").hidden=true;
    $("draft-form").hidden=true;$("inventory-table").replaceChildren();$("candidate-select").replaceChildren();
    $("challenge").value="";
    $("plan-review").checked=false;
    renderWork();drawResults();
    announce("All in-memory workspace content cleared.");
  });
  chooseSector(selectedIndustry);
  chooseGoal(selectedGoal);
  renderWork();drawResults();navigate();
})();