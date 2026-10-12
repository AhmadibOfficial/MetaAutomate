"use strict";

/* MetaAutomate Objective Workspace: client code never persists access keys. */
const state = {session:null, authMode:"unknown", capabilities:[], objectives:[], objective:null, inFlightKey:null, graph:null};
const $ = id => document.getElementById(id);
const screens = ["overview","create","detail","brand"];
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
function applyIdentityMode() {
  const oidc = state.authMode === "oidc";
  for (const item of document.querySelectorAll(
    '#login-form label[for="login-key"], #login-key, #login-form .field-hint, #login-submit'
  )) item.hidden = oidc;
  const sso = $("oidc-login-button");
  sso.hidden = !oidc;
  sso.disabled = !oidc;
  $("login-environment-label").textContent = oidc ? "PRIVATE ORGANIZATION SSO" : "LOCAL DEVELOPMENT WORKSPACE";
  $("environment-label").textContent = oidc ? "PRIVATE CLOUD · SSO" : "LOCAL DEVELOPMENT";
  $("login-form").querySelector("p").textContent = oidc
    ? "Authenticate with your organization's trusted identity provider. Access is restricted to approved members."
    : "Sign in with the access key provisioned for your organization.";
  $("login-key").required = !oidc;
}

function isEditor() { return ["OWNER","ADMIN","OPERATOR"].includes(state.session?.role); }
function isReviewer() { return ["OWNER","ADMIN"].includes(state.session?.role); }
function updateShell() {
  visible("loading-view",false);
  visible("login-view",!state.session);
  visible("workspace-shell",!!state.session);
  if (!state.session) return;
  $("side-role").textContent = label(state.session.role) + " workspace";
  $("side-org").textContent = "Organization " + state.session.organization_id.slice(0,8);
  for (const element of document.querySelectorAll(".create-trigger, #nav-create")) {
    element.disabled = !isEditor();
    element.title = isEditor() ? "" : "Your role cannot create objectives";
  }
}
function changeView(view, {history=true, path=null}={}) {
  if (!screens.includes(view)) view = "overview";
  for (const screen of screens) visible(screen+"-view", screen === view);
  $("topbar-crumb").textContent = {overview:"Overview",create:"New objective",detail:"Objective detail",brand:"Mission & Vision"}[view];
  for (const nav of document.querySelectorAll(".nav-item")) nav.classList.toggle("active",nav.dataset.view === view);
  if (history) window.history.pushState({view}, "", path || (view==="overview"?"/":view==="create"?"/?new=1":view==="brand"?"/about":location.pathname));
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
function lostSession(){
  state.session=null;state.objective=null;state.objectives=[];state.capabilities=[];
  updateShell();showToast("Your session expired. Please sign in again.");
  history.replaceState({view:"login"},"","/");
}
async function login(event){
  event.preventDefault();
  if(state.authMode !== "dev_key") return failInto("login-error", "Local access-key sign-in is disabled. Use your organization's SSO.");clearError("login-error");
  const button=$("login-submit"),accessKey=$("login-key").value.trim();
  button.disabled=true;button.textContent="Checking access…";
  try{
    state.session=await api("/v1/workspace/login",{method:"POST",body:JSON.stringify({access_key:accessKey})});
    $("login-key").value="";updateShell();await enterWorkspace();
  }catch(err){failInto("login-error",err.message);}
  finally{button.disabled=false;button.textContent="Enter workspace ↗";}
}
async function enterWorkspace(){
  if(window.location.pathname==="/about") return changeView("brand",{history:false});
  const match=window.location.pathname.match(/^\/objectives\/([0-9a-f-]{36})$/i);
  if(match)return openObjective(match[1],{history:false});
  if(new URLSearchParams(location.search).get("new")==="1")return createView();
  return overview();
}
async function logout(){
  try{await api("/v1/workspace/logout",{method:"POST",body:"{}"});}
  catch(err){if(err.status!==401)showToast(err.message);}
  state.session=null;state.capabilities=[];state.objective=null;updateShell();
  history.replaceState({view:"login"},"","/");
}
async function initialize(){
  document.querySelectorAll(".create-trigger, #nav-create").forEach(x=>x.addEventListener("click",createView));
  $("nav-overview").addEventListener("click",overview);
  $("nav-brand").addEventListener("click",()=>changeView("brand"));
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
  try{
    const config = await api("/v1/workspace/config");
    state.authMode = config.mode;
    applyIdentityMode();
  }catch{
    state.authMode = "unknown";
    applyIdentityMode();
    failInto("login-error", "Workspace identity settings are unavailable. Try again later.");
  }
  try{
    state.session=await api("/v1/workspace/session");
    updateShell();await enterWorkspace();
  }catch{
    state.session=null;updateShell();
  }
}
document.addEventListener("DOMContentLoaded",initialize);
