"use strict";

/* MetaAutomate Objective Workspace: client code never persists access keys. */
const state = {session:null, authMode:"dev_key", capabilities:[], objectives:[], objective:null, inFlightKey:null, graph:null,
  assessmentQuestions:null, assessment:null, assessmentInFlightKey:null};
const $ = id => document.getElementById(id);
const screens = ["overview","create","detail","assessment","assessment-history","assessment-detail","data-lab"];
let localDataLabEnabled = false;
const sleep = ms => new Promise(resolve => setTimeout(resolve,ms));

function visible(id, show) { $(id).hidden = !show; }
function failInto(target, message) {
  const item = $(target);
  item.textContent = message;
  item.hidden = false;
}
function clearError(target) { $(target).hidden = true; $(target).textContent = ""; }
function safeText(x, fallback = "") { return x === undefined || x === null ? fallback : String(x); }
function label(str) { return safeText(str).replaceAll("_"," ").toLowerCase().replace(/\b\w/g, x => x.toUpperCase()); }
function dateLabel(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.valueOf()) ? "" : new Intl.DateTimeFormat("en-GB",{day:"numeric",month:"short",year:"numeric"}).format(d);
}
function csrfToken() {
  return document.cookie.split("; ").find(x => x.startsWith("mat_csrf="))?.slice(9) || "";
}
async function api(url, options = {}) {
  const method = options.method || "GET";
  const headers = {"Accept":"application/json", ...(options.headers || {})};
  if (method !== "GET" && method !== "HEAD") {
    headers["X-CSRF-Token"] = csrfToken();
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(url, {credentials:"same-origin", ...options, headers});
  let result;
  try { result = await response.json(); } catch { result = {}; }
  if (!response.ok) {
    const detail = result.detail;
    let message = typeof detail === "string" ? detail
      : Array.isArray(detail) ? detail.map(x=>x.msg || "Invalid input").join("; ")
      : detail && typeof detail === "object" ? JSON.stringify(detail) : "Request could not be completed.";
    const err = new Error(message);
    err.status = response.status;
    throw err;
  }
  return result;
}
function showToast(message) {
  $("toast").textContent = message;
  visible("toast",true);
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(()=>visible("toast",false),4300);
}
async function configureSignIn(){
  const config=await api("/v1/workspace/config");
  if(!["dev_key","oidc"].includes(config.mode))throw new Error("Invalid workspace identity mode");
  const sso=config.mode==="oidc";
  state.authMode=config.mode;
  localDataLabEnabled = config.local_data_lab_available === true;
  $("login-environment-label").textContent=sso?"PRIVATE ORGANIZATION SSO":"PRIVATE DEVELOPMENT WORKSPACE";
  for(const selector of ['#login-form label[for="login-key"]','#login-key','#login-form .field-hint','#login-submit']){
    const node=document.querySelector(selector);
    node.hidden=sso;
    node.style.display=sso?"none":"";
  }
  const button=$("oidc-login-button");
  button.hidden=!sso;
  button.style.display=sso?"":"none";
  $("login-key").required=!sso;
  const intro=$("login-form").querySelector("p:not(.field-hint)");
  if(intro)intro.textContent=sso
    ?"Sign in with your approved organization's identity provider."
    :"Sign in with the access key provisioned for your organization.";
}
function isEditor() { return ["OWNER","ADMIN","OPERATOR"].includes(state.session?.role); }
function isReviewer() { return ["OWNER","ADMIN"].includes(state.session?.role); }
function updateShell() {
  visible("loading-view",false);
  visible("login-view",!state.session);
  visible("workspace-shell",!!state.session);
  $("nav-data-lab").hidden = !state.session || !localDataLabEnabled || !["OWNER","ADMIN","OPERATOR"].includes(state.session.role);
  if (!state.session) return;
  $("side-role").textContent = label(state.session.role) + " workspace";
  $("side-org").textContent = "Organization " + state.session.organization_id.slice(0,8);
  for (const element of document.querySelectorAll(".create-trigger, #nav-create, #nav-assessment, .assessment-new-trigger")) {
    element.disabled = !isEditor();
    element.title = isEditor() ? "" : "Your role cannot create objectives or assessments";
  }
}
function changeView(view, {history=true, path=null}={}) {
  if (!screens.includes(view)) view = "overview";
  if (view !== "data-lab") clearLabPreview();
  for (const screen of screens) visible(screen+"-view", screen === view);
  $("topbar-crumb").textContent = {overview:"Overview",create:"New objective",detail:"Objective detail",assessment:"Digital assessment","assessment-history":"Reports","assessment-detail":"Verified report","data-lab":"Inventory vault"}[view];
  for (const nav of document.querySelectorAll(".nav-item")) nav.classList.toggle("active",nav.dataset.view === view || (view==="assessment-detail" && nav.dataset.view==="assessment-history"));
  if (history) window.history.pushState({view}, "", path || (view==="overview"?"/":view==="create"?"/?new=1":location.pathname));
  window.scrollTo({top:0,behavior:"instant"});
  if(view==="detail") requestAnimationFrame(()=>drawGraph());
}
function el(tag, {cls="",text="",attrs={}} = {}) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  node.textContent = safeText(text);
  for (const [key,val] of Object.entries(attrs)) node.setAttribute(key,val);
  return node;
}
function statusBadge(status) {
  const value = safeText(status,"PENDING");
  return el("span",{cls:"status-badge "+(value==="APPROVED"?"approved":value==="REJECTED"?"rejected":""),text:label(value)});
}
async function overview() {
  changeView("overview");
  try {
    const data = await api("/v1/objective-operations?limit=100");
    state.objectives = data.items || [];
    renderOverview();
  } catch (err) {
    if (err.status === 401) return lostSession();
    showToast(err.message);
  }
}
function renderOverview() {
  const list = $("objectives-list");
  list.replaceChildren();
  const all = state.objectives;
  $("metric-total").textContent = all.length;
  $("metric-pending").textContent = all.filter(x=>!x.review_status || x.review_status==="PENDING").length;
  $("metric-approved").textContent = all.filter(x=>x.review_status==="APPROVED").length;
  visible("empty-overview", all.length===0);
  for (const objective of all) {
    const row = el("div",{cls:"objective-row",attrs:{role:"button",tabindex:"0","aria-label":"Open "+objective.title}});
    row.append(el("span",{cls:"objective-symbol",text:"◎"}));
    const body = el("div",{cls:"objective-description"});
    body.append(el("h3",{text:objective.title}));
    body.append(el("p",{text:"Created "+dateLabel(objective.created_at)+" · Draft plan"}));
    row.append(body,statusBadge(objective.review_status || "PENDING"),el("span",{cls:"row-chevron",text:"→"}));
    const open = () => openObjective(objective.id);
    row.addEventListener("click",open);
    row.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();open();}});
    list.append(row);
  }
}
async function loadCapabilities() {
  if(state.capabilities.length) return state.capabilities;
  const response = await api("/v1/objective-operations/capabilities");
  state.capabilities=response.items || [];
  renderCapabilities();
  return state.capabilities;
}
function renderCapabilities() {
  const root = $("capability-picker");root.replaceChildren();
  const sorted=[...state.capabilities].sort((a,b)=>(a.domain==="BIZ"?0:1)-(b.domain==="BIZ"?0:1)||a.capability_id.localeCompare(b.capability_id));
  for (const c of sorted) {
    const box=el("label",{cls:"cap-option"});
    const check=el("input",{attrs:{type:"checkbox",name:"capability",value:c.capability_id}});
    if (["BIZ-003","BIZ-005"].includes(c.capability_id)) check.checked=true;
    const labelText=el("span");
    labelText.append(el("strong",{text:c.name}),el("small",{text:c.capability_id+" · "+c.domain+" · Draft"}));
    box.append(check,labelText);
    root.append(box);
  }
}
async function createView() {
  if(!isEditor())return showToast("Your organization role cannot create objectives.");
  changeView("create");
  clearError("create-error");
  try{await loadCapabilities();}catch(err){failInto("create-error",err.message);}
}
async function saveObjective(event) {
  event.preventDefault();
  clearError("create-error");
  const selected=[...document.querySelectorAll('input[name="capability"]:checked')].map(i=>i.value);
  if(!selected.length || selected.length>10)return failInto("create-error","Select between one and ten capabilities.");
  const constraints=$("objective-constraints").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
  if(constraints.length>20)return failInto("create-error","Please use no more than 20 constraints.");
  const payload={
    title:$("objective-title").value.trim(),
    description:$("objective-description").value.trim(),
    success_criteria:[{
      metric:$("criterion-metric").value.trim(),
      target:$("criterion-target").value.trim(),
      timeframe_days:Number($("criterion-days").value)
    }],
    constraints,
    requested_capability_ids:selected
  };
  const submit=$("create-submit");submit.disabled=true;submit.textContent="Saving your plan…";
  if(!state.inFlightKey)state.inFlightKey=crypto.randomUUID();
  try{
    const created=await api("/v1/objective-operations",{
      method:"POST",
      headers:{"Idempotency-Key":state.inFlightKey},
      body:JSON.stringify(payload)
    });
    state.inFlightKey=null;
    $("objective-form").reset();
    state.capabilities=[]; // reload defaults when opening next time
    showToast("Objective saved. Your plan is ready for review.");
    await openObjective(created.objective_id);
  }catch(err){
    if(err.status===401){lostSession();return;}
    failInto("create-error",err.message);
  }finally{
    submit.disabled=false;submit.replaceChildren(document.createTextNode("Create and save plan  →"));
  }
}
async function openObjective(id,{history=true}={}) {
  try{
    const data=await api("/v1/objective-operations/"+encodeURIComponent(id));
    state.objective=data;
    renderObjective();
    changeView("detail",{history,path:"/objectives/"+id});
  }catch(err){
    if(err.status===401)return lostSession();
    showToast(err.status===404?"Objective not found in your organization.":err.message);
    await overview();
  }
}
function renderObjective() {
  const data=state.objective, objective=data.objective,review=data.review;
  $("detail-title").textContent=objective.title;
  $("detail-description").textContent=objective.description || "No additional context was provided.";
  $("detail-reference").textContent=String(objective.id).slice(0,13).toUpperCase();
  $("detail-review-state").textContent=label(review?.status||"PENDING");
  const badge=statusBadge(review?.status || "PENDING");
  $("detail-badge").className=badge.className;
  $("detail-badge").textContent=badge.textContent;
  const outcomes=$("detail-outcomes");outcomes.replaceChildren();
  for(const criterion of (objective.desired_outcome?.success_criteria||[])) {
    const row=el("div",{cls:"outcome-item"});
    row.append(el("div",{cls:"outcome-icon",text:"↗"}));
    const content=el("div");
    content.append(el("strong",{text:criterion.target+" "+criterion.metric}),
      el("small",{text:"Within "+criterion.timeframe_days+" days"}));
    row.append(content);outcomes.append(row);
  }
  if(!outcomes.children.length) outcomes.append(el("div",{cls:"outcome-item",text:"No success criteria saved."}));
  const constraints=$("detail-constraints");constraints.replaceChildren();
  const values=objective.input_context?.constraints || [];
  for(const item of values) constraints.append(el("li",{text:item}));
  if(!values.length)constraints.append(el("li",{text:"No additional constraints."}));
  const writable=!!review&&review.status==="PENDING"&&isReviewer();
  visible("review-form",writable);
  visible("review-readonly",!writable);
  $("review-reason").value="";
  clearError("review-error");
  if(!writable){
    $("review-readonly").textContent=review?.status==="APPROVED"
      ? "✓ Plan reviewed and approved. Proposed work remains blocked until execution is separately authorized."
      : review?.status==="REJECTED"
      ? "Plan rejected. "+(review.decision_reason||"No reason supplied.")
      : "Review is available to organization owners and administrators. Execution remains disabled.";
  }
  $("review-explanation").textContent=review?.status==="PENDING"
    ?"An owner or administrator can approve or reject this proposal."
    :"Review decision recorded in the objective history.";
  drawNodes(data.tasks||[],data.task_dependencies||[]);
}
function drawNodes(tasks,links) {
  state.graph={tasks,links};
  const root=$("graph-nodes");root.replaceChildren();
  if(!tasks.length){
    root.append(el("p",{text:"No proposed work steps available."}));
    $("graph-lines").replaceChildren();return;
  }
  for(const task of tasks){
    const node=el("div",{cls:"graph-node",attrs:{"data-task":task.id}});
    const top=el("small");
    top.append(el("span",{text:"STEP "+(Number(task.sequence_no)+1)}),el("span",{text:task.capability_key||"STRUCTURE"}));
    node.append(top,el("strong",{text:task.name}),el("div",{cls:"node-foot",text:"◯ Proposed · "+label(task.state)}));
    root.append(node);
  }
  requestAnimationFrame(()=>drawGraph());
}
function drawGraph() {
  if(!$("detail-view")||$("detail-view").hidden||!state.graph)return;
  const svg=$("graph-lines"),stage=$("graph-stage");
  svg.replaceChildren();
  const width=stage.scrollWidth,height=stage.scrollHeight;
  svg.setAttribute("width",width);svg.setAttribute("height",height);
  svg.setAttribute("viewBox","0 0 "+width+" "+height);
  const ns="http://www.w3.org/2000/svg";
  const defs=document.createElementNS(ns,"defs"),marker=document.createElementNS(ns,"marker");
  for(const [k,v] of Object.entries({id:"arrow-head",markerWidth:"8",markerHeight:"8",refX:"7",refY:"4",orient:"auto"}))marker.setAttribute(k,v);
  const arrow=document.createElementNS(ns,"path");arrow.setAttribute("d","M0 0L8 4L0 8Z");arrow.setAttribute("fill","#a9c1e3");
  marker.append(arrow);defs.append(marker);svg.append(defs);
  const stageRect=stage.getBoundingClientRect();
  const byId=new Map([...$("graph-nodes").querySelectorAll("[data-task]")].map(x=>[x.dataset.task,x]));
  for(const edge of state.graph.links){
    const from=byId.get(String(edge.depends_on_task_id)),to=byId.get(String(edge.task_id));
    if(!from||!to)continue;
    const a=from.getBoundingClientRect(),b=to.getBoundingClientRect();
    const x1=a.left+a.width/2-stageRect.left+stage.scrollLeft;
    const y1=a.bottom-stageRect.top+stage.scrollTop;
    const x2=b.left+b.width/2-stageRect.left+stage.scrollLeft;
    const y2=b.top-stageRect.top+stage.scrollTop;
    const path=document.createElementNS(ns,"path");
    const bend=Math.max(20,Math.abs(y2-y1)/2);
    path.setAttribute("d","M"+x1+","+y1+" C"+x1+","+(y1+bend)+" "+x2+","+(y2-bend)+" "+x2+","+y2);
    path.setAttribute("stroke","#aac4e7");path.setAttribute("stroke-width","2");
    path.setAttribute("fill","none");path.setAttribute("marker-end","url(#arrow-head)");
    svg.append(path);
  }
}
async function reviewObjective(event){
  event.preventDefault();
  clearError("review-error");
  const submitter=event.submitter;
  const decision=submitter?.value || "APPROVED";
  const reason=$("review-reason").value.trim();
  if(reason.length<5)return failInto("review-error","Enter at least five characters explaining your decision.");
  const id=state.objective?.objective?.id;
  if(!id)return;
  const actions=$("review-form").querySelectorAll("button");
  actions.forEach(b=>b.disabled=true);
  try{
    await api("/v1/objective-operations/"+id+"/review",{
      method:"POST",body:JSON.stringify({decision,reason})
    });
    showToast("Review recorded. No execution has started.");
    await openObjective(id,{history:false});
  }catch(err){
    if(err.status===401)return lostSession();
    failInto("review-error",err.message);
  }finally{actions.forEach(b=>b.disabled=false);}
}

/* Operational Core v1: browser workflow for self-assessment execution.
   All persistence, roles, scoring and verification are server-authoritative. */
async function assessmentView() {
  if (!isEditor()) return assessmentHistoryView();
  changeView("assessment",{path:"/assessments"});
  clearError("assessment-error");
  try {
    if (!state.assessmentQuestions) {
      state.assessmentQuestions=await api("/v1/assessments/questions");
    }
    renderAssessmentQuestions();
  } catch(err) {
    if(err.status===401)return lostSession();
    failInto("assessment-error",err.message);
  }
}
function renderAssessmentQuestions() {
  const catalog=state.assessmentQuestions;
  if(!catalog)return;
  const root=$("assessment-questions");
  root.replaceChildren();
  for(const domain of catalog.domains){
    const section=el("fieldset",{cls:"assessment-domain"});
    section.append(el("legend",{text:domain.name}));
    for(const q of domain.questions){
      const wrap=el("div",{cls:"assessment-question"});
      const id="rating-"+q.id;
      const labelNode=el("label",{text:q.prompt,attrs:{for:id}});
      const select=el("select",{attrs:{id,name:q.id,required:"",class:"assessment-rating"}});
      select.append(el("option",{text:"Choose a rating…",attrs:{value:""}}));
      for(const rating of catalog.scale)select.append(el("option",{
        text:rating.value+" — "+rating.label,attrs:{value:String(rating.value)}
      }));
      wrap.append(labelNode,select);section.append(wrap);
    }
    root.append(section);
  }
  $("assessment-submit").disabled=!isEditor();
}
async function assessmentHistoryView(){
  changeView("assessment-history",{path:"/assessments/reports"});
  const list=$("assessment-report-list");
  list.replaceChildren(el("p",{text:"Loading saved reports…"}));
  try{
    const records=await api("/v1/assessments?limit=50");
    list.replaceChildren();
    visible("assessment-history-empty",!records.items?.length);
    for(const record of records.items||[]){
      const button=el("button",{cls:"assessment-record",attrs:{type:"button"}});
      const name=el("span",{cls:"assessment-record-main"});
      name.append(el("strong",{text:record.business_label}),
        el("small",{text:record.objective}));
      button.append(name,el("span",{cls:"assessment-record-date",text:dateLabel(record.created_at)+" ↗"}));
      button.addEventListener("click",()=>openAssessment(record.assessment_id));
      list.append(button);
    }
  }catch(err){
    if(err.status===401)return lostSession();
    list.replaceChildren(el("p",{text:err.message}));
  }
}
async function submitAssessment(event){
  event.preventDefault();
  clearError("assessment-error");
  if(!isEditor())return failInto("assessment-error","Your role cannot generate reports.");
  const form=$("assessment-form");
  if(!form.checkValidity()){form.reportValidity();return;}
  const q=state.assessmentQuestions;
  if(!q)return failInto("assessment-error","Assessment questions are not ready.");
  const answers=[];
  for(const domain of q.domains){
    for(const question of domain.questions){
      const field=$("rating-"+question.id);
      if(field.value==="")return failInto("assessment-error","Answer every assessment statement.");
      answers.push({question_id:question.id,score:Number(field.value)});
    }
  }
  const payload={
    business_label:$("assessment-business").value.trim(),
    objective:$("assessment-goal").value.trim(),answers
  };
  if(!state.assessmentInFlightKey)state.assessmentInFlightKey="assessment-"+crypto.randomUUID();
  const submit=$("assessment-submit");
  submit.disabled=true;submit.textContent="Generating and verifying…";
  try{
    const saved=await api("/v1/assessments",{
      method:"POST",
      headers:{"Idempotency-Key":state.assessmentInFlightKey,
        "X-Assessment-Consent":"generate-report"},
      body:JSON.stringify(payload)
    });
    state.assessmentInFlightKey=null;
    form.reset();
    showToast("Assessment completed. The saved calculation has been verified.");
    state.assessment=saved;
    renderAssessmentResult(saved);
    changeView("assessment-detail",{path:"/assessments/"+saved.assessment_id});
  }catch(err){
    if(err.status===401)return lostSession();
    failInto("assessment-error",err.message);
  }finally{
    submit.disabled=!isEditor();
    submit.textContent="Generate verified report →";
  }
}
async function openAssessment(id,{history=true}={}){
  try{
    const saved=await api("/v1/assessments/"+encodeURIComponent(id));
    state.assessment=saved;
    renderAssessmentResult(saved);
    changeView("assessment-detail",{history,path:"/assessments/"+saved.assessment_id});
  }catch(err){
    if(err.status===401)return lostSession();
    showToast(err.status===404?"Report not found in this organization.":err.message);
    return assessmentHistoryView();
  }
}
function renderAssessmentResult(saved){
  const report=saved.report;
  $("assessment-report-title").textContent=report.business_label;
  $("assessment-report-goal").textContent=report.objective;
  $("assessment-overall-score").textContent=report.overall_score+"/100";
  $("assessment-overall-level").textContent=report.maturity_level+" maturity · Self-reported";
  const domains=$("assessment-domain-results");domains.replaceChildren();
  for(const result of report.domain_results){
    const item=el("div",{cls:"assessment-score-row"});
    const head=el("div",{cls:"assessment-score-row-head"});
    head.append(el("strong",{text:result.name}),el("span",{text:result.score+"/100"}));
    const track=el("div",{cls:"assessment-track",attrs:{role:"meter",
      "aria-label":result.name+" maturity","aria-valuemin":"0","aria-valuemax":"100",
      "aria-valuenow":String(result.score)}});
    const bar=el("div",{cls:"assessment-progress"});
    bar.style.width=Math.max(0,Math.min(100,Number(result.score)))+"%";
    track.append(bar);
    item.append(head,track,el("small",{text:result.earned_points+" of "+result.max_points+
      " points from your three ratings"}));
    domains.append(item);
  }
  const actions=$("assessment-prioritized-actions");
  actions.replaceChildren();
  if(!report.prioritized_actions.length){
    actions.append(el("p",{text:"No gaps were self-reported. Continue measuring outcomes and checking evidence."}));
  }
  for(const action of report.prioritized_actions){
    const card=el("article",{cls:"assessment-action"});
    const heading=el("div",{cls:"assessment-action-heading"});
    heading.append(el("span",{cls:"assessment-rank",text:String(action.rank).padStart(2,"0")}),
      el("strong",{text:action.recommended_action}));
    card.append(heading,
      el("p",{text:"Based on "+action.rank_source_question+
        " (self-rating "+action.self_reported_score+"/4) · Domain score "+
        action.priority_domain_score+"/100"}),
      el("small",{text:"Suggested measure: "+action.measurement}));
    actions.append(card);
  }
  const receipt=$("assessment-receipt");receipt.replaceChildren();
  for(const [key,value] of [
    ["Status",saved.status],["Verification",saved.verification_status],
    ["Assessment ID",saved.assessment_id],
    ["Algorithm version",saved.receipt.scoring_version],
    ["Generated",dateLabel(saved.receipt.created_at)],
    ["Input fingerprint",saved.receipt.input_sha256],
    ["Report fingerprint",saved.receipt.report_sha256],
    ["Verification scope",saved.receipt.verification_scope],
    ["External actions","None"]
  ]){
    receipt.append(el("dt",{text:key}),el("dd",{text:String(value)}));
  }
}
function downloadAssessment(){
  if(!state.assessment)return;
  const report=JSON.stringify(state.assessment,null,2)+"\n";
  const blob=new Blob([report],{type:"application/json;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const link=document.createElement("a");
  link.href=url;
  link.download="metaautomate-assessment-"+state.assessment.assessment_id+".json";
  document.body.append(link);
  link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}


/* P2-061: local, authenticated inventory lab; never available on the public website. */
function clearLabPreview(){
  const display=$("lab-detail"),pre=$("lab-preview");
  if(display)display.hidden=true;
  if(pre)pre.textContent="";
}
function labMessage(value){ $("lab-message").textContent=String(value); }
async function labRequest(url, options={}){
  const method=options.method || "GET";
  const headers={"Accept":"application/json",...(options.headers||{})};
  if(method!=="GET" && method!=="HEAD")headers["X-CSRF-Token"]=csrfToken();
  const response=await fetch(url,{credentials:"same-origin",...options,headers});
  const result=await response.json().catch(()=>({}));
  if(!response.ok){
    const err=new Error(typeof result.detail==="string"?result.detail:"Local inventory request failed.");
    err.status=response.status;throw err;
  }
  return result;
}
async function dataLabView(){
  if(!localDataLabEnabled || !state.session)return;
  changeView("data-lab",{path:"/data-lab"});
  await loadDataLab();
}
async function loadDataLab(){
  if(!state.session || !localDataLabEnabled)return;
  const list=$("lab-items");list.replaceChildren();clearLabPreview();
  try{
    const reply=await labRequest("/v1/data-lab/inventory");
    if(!reply.items?.length){
      list.append(el("p",{text:"No active inventory documents in this organization."}));
      labMessage("Encrypted rehearsal storage. No production access enabled.");
      return;
    }
    for(const item of reply.items){
      const row=el("div",{cls:"lab-document"});
      const details=el("div",{cls:"lab-document-name"});
      details.append(el("strong",{text:item.record_count+" inventory rows"}),
        el("small",{text:"Reference: "+item.document_id.slice(0,8)+" · SHA-256: "+item.source_sha256.slice(0,12)+
              " · Retention deadline: "+new Date(item.retained_until*1000).toLocaleDateString()}));
      const actions=el("div",{cls:"lab-actions"});
      const open=el("button",{cls:"button subtle",text:"View inventory"});
      open.type="button";
      open.addEventListener("click",()=>viewDataLab(item.document_id));
      const remove=el("button",{cls:"button danger",text:"Delete"});
      remove.type="button";
      remove.disabled=!isReviewer();
      remove.addEventListener("click",()=>deleteDataLab(item.document_id));
      actions.append(open,remove);row.append(details,actions);list.append(row);
    }
    labMessage(reply.items.length+" encrypted document(s) in this workspace. No cross-tenant listing available.");
  }catch(err){
    if(err.status===401){lostSession();return;}
    labMessage(err.status===404?"Local data lab is disabled.":err.message);
  }
}
async function importDataLab(event){
  event.preventDefault();
  if(!localDataLabEnabled || !isReviewer())return labMessage("Owner or admin permission required.");
  const form=$("lab-import-form"),file=$("lab-file").files?.[0],button=$("lab-submit");
  if(!form.reportValidity() || !file)return;
  if(file.size===0 || file.size>65536)return labMessage("Choose a CSV file under 64 KB.");
  button.disabled=true;clearLabPreview();
  try{
    const reply=await labRequest("/v1/data-lab/inventory?retention_days="+encodeURIComponent($("lab-retention").value),{
      method:"POST",
      headers:{"Content-Type":"text/csv","X-Inventory-Data-Claim":"OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA"},
      body:await file.arrayBuffer()
    });
    form.reset();
    await loadDataLab();
    labMessage("Encrypted "+reply.record_count+" inventory rows locally. Ownership remains self-declared.");
  }catch(err){
    if(err.status===401){lostSession();return;}
    labMessage(err.message);
  }finally{button.disabled=false;}
}
async function viewDataLab(id){
  clearLabPreview();
  try{
    const result=await labRequest("/v1/data-lab/inventory/"+encodeURIComponent(id));
    $("lab-preview").textContent=JSON.stringify(result.records,null,2);
    $("lab-detail").hidden=false;
    labMessage("Decrypted in your current session. Close the preview after inspection.");
  }catch(err){
    if(err.status===401){lostSession();return;}
    labMessage(err.message);
  }
}
async function deleteDataLab(id){
  if(!isReviewer())return;
  if(!window.confirm("Delete this locally stored inventory record? Audit metadata remains; backups cannot be verified deleted."))return;
  try{
    await labRequest("/v1/data-lab/inventory/"+encodeURIComponent(id),{method:"DELETE"});
    await loadDataLab();labMessage("Active encrypted inventory record deleted; audit tombstone retained.");
  }catch(err){if(err.status===401)lostSession();else labMessage(err.message);}
}
async function purgeDataLab(){
  if(!isReviewer())return labMessage("Owner/admin permission required for purging.");
  if(!window.confirm("Purge expired inventory records for your organization from this active local store?"))return;
  try{
    const report=await labRequest("/v1/data-lab/inventory/purge-expired",{method:"POST"});
    await loadDataLab();labMessage(report.purged+" expired record(s) removed from active storage only.");
  }catch(err){if(err.status===401)lostSession();else labMessage(err.message);}
}
async function verifyDataLabAudit(){
  try{
    const result=await labRequest("/v1/data-lab/audit");
    labMessage("Local HMAC chain: "+result.events+" events, "+result.integrity+". Not externally anchored.");
  }catch(err){if(err.status===401)lostSession();else labMessage(err.message);}
}

function lostSession(){
  clearLabPreview();
  state.session=null;state.objective=null;state.objectives=[];state.capabilities=[];
  state.assessment=null;state.assessmentQuestions=null;state.assessmentInFlightKey=null;
  updateShell();showToast("Your session expired. Please sign in again.");
  history.replaceState({view:"login"},"","/");
}
async function login(event){
  event.preventDefault();clearError("login-error");
  const button=$("login-submit"),accessKey=$("login-key").value.trim();
  button.disabled=true;button.textContent="Checking access…";
  try{
    state.session=await api("/v1/workspace/login",{method:"POST",body:JSON.stringify({access_key:accessKey})});
    $("login-key").value="";updateShell();await enterWorkspace();
  }catch(err){failInto("login-error",err.message);}
  finally{button.disabled=false;button.textContent="Enter workspace ↗";}
}
async function enterWorkspace(){
  const assessmentMatch=window.location.pathname.match(/^\/assessments\/([0-9a-f-]{36})$/i);
  if(assessmentMatch)return openAssessment(assessmentMatch[1],{history:false});
  if(window.location.pathname==="/assessments/reports")return assessmentHistoryView();
  if(window.location.pathname==="/data-lab" && localDataLabEnabled)return dataLabView();
  if(window.location.pathname==="/assessments")return assessmentView();
  const match=window.location.pathname.match(/^\/objectives\/([0-9a-f-]{36})$/i);
  if(match)return openObjective(match[1],{history:false});
  if(new URLSearchParams(location.search).get("new")==="1")return createView();
  return overview();
}
async function logout(){
  try{await api("/v1/workspace/logout",{method:"POST",body:"{}"});}
  catch(err){if(err.status!==401)showToast(err.message);}
  clearLabPreview();
  state.session=null;state.capabilities=[];state.objective=null;state.assessment=null;
  state.assessmentQuestions=null;state.assessmentInFlightKey=null;updateShell();
  history.replaceState({view:"login"},"","/");
}
async function initialize(){
  document.querySelectorAll(".create-trigger, #nav-create").forEach(x=>x.addEventListener("click",createView));
  $("nav-overview").addEventListener("click",overview);
  $("nav-assessment").addEventListener("click",assessmentView);
  $("nav-assessment-history").addEventListener("click",assessmentHistoryView);
  $("nav-data-lab").addEventListener("click",dataLabView);
  $("lab-refresh").addEventListener("click",loadDataLab);
  $("lab-import-form").addEventListener("submit",importDataLab);
  $("lab-purge").addEventListener("click",purgeDataLab);
  $("lab-audit").addEventListener("click",verifyDataLabAudit);
  $("lab-close-detail").addEventListener("click",clearLabPreview);
  $("assessment-show-history").addEventListener("click",assessmentHistoryView);
  $("assessment-refresh").addEventListener("click",assessmentHistoryView);
  $("assessment-detail-back").addEventListener("click",assessmentHistoryView);
  document.querySelectorAll(".assessment-new-trigger").forEach(x=>x.addEventListener("click",assessmentView));
  $("assessment-form").addEventListener("submit",submitAssessment);
  $("assessment-download").addEventListener("click",downloadAssessment);
  $("cancel-create").addEventListener("click",overview);
  $("back-to-overview").addEventListener("click",overview);
  $("refresh-overview").addEventListener("click",overview);
  $("login-form").addEventListener("submit",login);
  $("oidc-login-button").addEventListener("click",()=>window.location.assign("/v1/workspace/oidc/login"));
  $("objective-form").addEventListener("submit",saveObjective);
  $("review-form").addEventListener("submit",reviewObjective);
  $("logout-button").addEventListener("click",logout);
  window.addEventListener("resize",()=>requestAnimationFrame(drawGraph));
  window.addEventListener("popstate",()=>{if(state.session)enterWorkspace();});
  try{ await configureSignIn(); }
  catch { failInto("login-error","Private workspace sign-in configuration unavailable."); state.session=null; updateShell(); return; }
  try{
    state.session=await api("/v1/workspace/session");
    updateShell();await enterWorkspace();
  }catch{
    state.session=null;updateShell();
  }
}
document.addEventListener("DOMContentLoaded",initialize);
