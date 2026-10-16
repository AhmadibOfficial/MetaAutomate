/* P2-03u: rules-only, synthetic and zero-network Intelligence Workbench. */
(() => {
  "use strict";
  const LIB = window.MetaAutomateIntelligenceTemplates;
  const $ = id => document.getElementById(id);
  const SCENARIO_IDS = [
    "LEAD_QUALIFICATION","INVENTORY_RESILIENCE","CONTENT_OPERATIONS","SECURITY_TRIAGE"
  ];
  const ORDER=["INTAKE","VALIDATE","ASSESS","REVIEW","EXTERNAL"];
  const TYPE=["INPUT","QUALITY","ANALYSIS","HUMAN_REVIEW","EXTERNAL_ACTION"];
  const BOUNDS=["SAMPLE_ONLY","MISSING","APPROVED_SOURCE_CLAIM"];
  const SENSITIVITY=["NONE","PERSONAL","CONFIDENTIAL"];
  const ACTIONS=["DESIGN_ONLY","REQUEST_EXTERNAL_WORKFLOW"];
  const suffix=" — illustrative only";
  function el(tag, className, content) {
    const n=document.createElement(tag);
    if(className)n.className=className;
    if(content!==undefined)n.textContent=String(content);
    return n;
  }
  function clean(value) {
    return typeof value==="string" && value.length>=8 && value.length<=180
      && !/[<>{}\r\n]/.test(value);
  }
  function validate(src) {
    if(!src || src.schema_version!==1 || src.classification!=="SYNTHETIC_SOURCE_ONLY"
       || !Array.isArray(src.scenarios) || src.scenarios.length!==4) return false;
    const ids = new Set();
    for(const scenario of src.scenarios) {
      if(!scenario || !SCENARIO_IDS.includes(scenario.id) || ids.has(scenario.id)
        || !["label","sector","objective","description","success_metric"].every(k=>clean(scenario[k]))
        || scenario.metric_unit!=="COUNT"
        || !Number.isInteger(scenario.sample_baseline)
        || scenario.sample_baseline<0 || scenario.sample_baseline>10000
        || !Array.isArray(scenario.steps) || scenario.steps.length!==5) return false;
      ids.add(scenario.id);
      for(let i=0;i<5;i++){
        const step=scenario.steps[i];
        if(!step || step.id!==ORDER[i] || step.type!==TYPE[i]
          || !clean(step.description) || step.requires_review!==(i>=3)
          || step.external_effect!==(i===4)
          || !Array.isArray(step.depends_on)
          || JSON.stringify(step.depends_on)!==JSON.stringify(i?[ORDER[i-1]]:[]))
          return false;
      }
    }
    return ids.size===4;
  }
  if(!validate(LIB)){
    $("plan-heading").textContent="Validated examples unavailable";
    $("plan-description").textContent="The workbench has not loaded safe source contracts. No simulation can run.";
    $("simulate").disabled=true;$("download").disabled=true;return;
  }
  let current=null;
  const values=()=>({
    scenario_id:$("scenario").value,
    data_state:$("data-state").value,
    sensitivity:$("sensitivity").value,
    requested_action:$("request").value
  });
  function buildPlan(){
    const selection=values();
    if(!SCENARIO_IDS.includes(selection.scenario_id)
      || !BOUNDS.includes(selection.data_state)
      || !SENSITIVITY.includes(selection.sensitivity)
      || !ACTIONS.includes(selection.requested_action)) return null;
    const scene=LIB.scenarios.find(s=>s.id===selection.scenario_id);
    if(!scene) return null;
    const blockers=[];
    if(selection.data_state==="MISSING")
      blockers.push("Define a lawful, representative data source and baseline");
    if(selection.data_state==="APPROVED_SOURCE_CLAIM")
      blockers.push("Verify source ownership, minimization, provenance and authorization");
    if(selection.sensitivity!=="NONE")
      blockers.push("Security and privacy review required before handling sensitive information");
    blockers.push(
      "Authenticate the real workflow owner and independent security reviewer",
      "Validate source quality, measured baseline and approval evidence",
      "Complete private-staging identity, audit, recovery and release verification"
    );
    if(selection.requested_action==="REQUEST_EXTERNAL_WORKFLOW")
      blockers.push("External platform permissions, consent and publication approvals not verified");
    return {
      classification:"SYNTHETIC_SOURCE_ONLY",
      milestone:"P2_03U_INTELLIGENCE_PROJECT_ARCHITECT",
      project:{
        id:scene.id,name:scene.label,sector:scene.sector,objective:scene.objective,
        metric:scene.success_metric,metric_unit:scene.metric_unit,
        illustrative_baseline:scene.sample_baseline,baseline_verified:false
      },
      choices:{
        data_state:selection.data_state,sensitivity:selection.sensitivity,
        requested_action:selection.requested_action
      },
      workflow:scene.steps.map((s,i)=>({
        id:s.id,type:s.type,description:s.description,
        depends_on:[...s.depends_on],
        status:i===4?"BLOCKED_EXTERNAL":i===3?"HUMAN_REVIEW_REQUIRED":"SAFE_SYNTHETIC_PREVIEW",
        actual_execution_authorized:false,provider_calls:0
      })),
      blockers,
      evidence:{
        fixture_classification:"SYNTHETIC_SOURCE_ONLY",
        real_model_or_agent_connected:false,
        live_customer_data:false,
        external_actions_attempted:0,
        actual_financial_value_verified:false,
        live_identity_provider_connected:false,
        real_approval_verified:false,production_ready:false
      }
    };
  }
  function render() {
    current=buildPlan();
    if(!current){$("plan-heading").textContent="Invalid source selection";return;}
    const p=current.project;
    $("plan-heading").textContent=p.name;
    const scene=LIB.scenarios.find(x=>x.id===p.id);
    $("plan-description").textContent=scene.description;
    $("objective").textContent=p.objective;
    $("measure").textContent=p.metric;
    $("baseline").textContent=p.illustrative_baseline+" example records"+suffix;
    const graph=$("graph");graph.replaceChildren();
    for(const [i,s] of current.workflow.entries()){
      const node=el("li");
      node.append(el("span","index",String(i+1).padStart(2,"0")));
      const copy=el("div","node-copy");
      copy.append(el("strong","",s.id==="EXTERNAL"?"External action (disabled)":
        s.id==="REVIEW"?"Human decision required":
        s.id==="INTAKE"?"Scope the input":s.id==="VALIDATE"?"Check data quality":
        "Assess the objective"));
      copy.append(el("p","",s.description));
      node.append(copy);
      const state=el("span","state"+
        (i===3?" review":i===4?" blocked":""),i<3?"Synthetic preview":
        i===3?"Review required":"Blocked");
      node.append(state);graph.append(node);
    }
    const blockers=$("blockers");blockers.replaceChildren();
    for(const reason of current.blockers)blockers.append(el("li","",reason));
    const message=$("simulation");message.replaceChildren(
      el("strong","","Ready to simulate"),
      el("p","","No workflow steps have run. No external operations are available.")
    );
  }
  function simulate() {
    if(!current){return;}
    // The only local transitions are fictional document-processing states;
    // two approval/external nodes are ALWAYS stopped regardless of input.
    $("simulation").replaceChildren(
      el("strong","","Three fictional steps simulated"),
      el("p","","INTAKE → VALIDATE → ASSESS completed within this page. "+
        "REVIEW halted: no authenticated owner or security reviewer. "+
        "EXTERNAL never ran. 0 provider calls, 0 AI model calls, 0 CRM writes.")
    );
  }
  function download() {
    if(!current) return;
    const text=JSON.stringify({
      ...current,
      readme:"Fictional example only. Not approved to handle customer data or execute any external workflow."
    },null,2);
    // Static browser download initiated directly by the visitor.
    const url=URL.createObjectURL(new Blob([text],{type:"application/json"}));
    const a=document.createElement("a");
    a.href=url;a.download="metaautomate-intelligence-example-plan.json";
    a.hidden=true;document.body.append(a);a.click();a.remove();
    URL.revokeObjectURL(url);
  }
  for(const name of ["scenario","data-state","sensitivity","request"])
    $(name).addEventListener("change",render);
  $("simulate").addEventListener("click",simulate);
  $("download").addEventListener("click",download);
  render();
})();