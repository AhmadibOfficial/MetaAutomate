/* P2-03w: display existing validated synthetic governance map. No network. */
(() => {
"use strict";
const map=window.MetaAutomateGovernanceMap;
const $=id=>document.getElementById(id);
const EXPECTED_MODULES=[
 "objective","value","decision","growth","crm","inventory","finance",
 "marketing","commerce","workflow","operations","executive"
];
const EXPECTED_ENGINES=["measurement","decision","recommendation","automation","learning"];
const MODELS=["claude-opus-5-5","gpt-6-astra","gpt-6-luna","gpt-6.1-sol"];
const pretty=x=>x.replaceAll("_"," ").toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());
function safe(){
 if(!map||map.schema_version!==1||map.classification!=="SYNTHETIC_SOURCE_ONLY"||
    !Array.isArray(map.modules)||map.modules.length!==12||
    !Array.isArray(map.engines)||map.engines.length!==5||
    !Array.isArray(map.candidate_models)||map.candidate_models.length!==4||
    map.modules.some((m,i)=>m.id!==EXPECTED_MODULES[i]||
      m.status!=="SOURCE_ONLY_UNVERIFIED_CUSTOMER_DATA"||
      !Array.isArray(m.engines)||m.engines.some(e=>!EXPECTED_ENGINES.includes(e))||
      !Array.isArray(m.virtual_tools))||
    map.engines.some((e,i)=>e.id!==EXPECTED_ENGINES[i]||
      e.status!=="SOURCE_ONLY_NO_DISPATCH")||
    map.candidate_models.some((m,i)=>m.id!==MODELS[i]||
      m.evidence!=="OFFICIAL_MODEL_ID_NOT_EVALUATED"))return false;
 const guard=map.limitations;
 return guard&&guard.mfa_verified_with_live_idp===false&&
 guard.customer_data_connected===false&&guard.live_ai_model_calls===0&&
 guard.external_tools_enabled===false&&guard.actual_roi_verified===false&&
 guard.production_enabled===false&&guard.foundation_gates_verified===3&&
 guard.foundation_gates_total===9;
}
const create=(tag,className,text)=>{
 const node=document.createElement(tag);
 if(className)node.className=className;
 if(text!==undefined)node.textContent=String(text);
 return node;
};
if(!safe()){
 $("module-name").textContent="Source contract unavailable";
 $("module-status").textContent="Source-only safeguards did not validate. No architecture data can be displayed.";
 return;
}
$("module-count").textContent=String(map.modules.length);
$("engine-count").textContent=String(map.engines.length);
$("foundation").textContent=map.limitations.foundation_gates_verified+"/"+map.limitations.foundation_gates_total;
$("model-calls").textContent="0";
function select(id){
 const m=map.modules.find(row=>row.id===id);
 if(!m)return;
 $("module-name").textContent=m.name;
 $("module-status").textContent="Source only · customer data unverified · no live operations";
 $("module-engines").replaceChildren(...m.engines.map(x=>create("span","",pretty(x))));
 $("module-tools").replaceChildren(...m.virtual_tools.map(x=>create("span","",pretty(x)+" · virtual only")));
 $("module-eval").textContent="Future task rubric: "+pretty(m.evaluation_task)+
   ". Representative live model performance, safety, latency and cost have not been measured.";
 document.querySelectorAll("#module-list button").forEach(x=>{
  x.setAttribute("aria-pressed",String(x.dataset.module===id));
 });
}
const nav=$("module-list");
for(const [i,m] of map.modules.entries()){
 const button=create("button");
 button.type="button";button.dataset.module=m.id;
 button.setAttribute("aria-pressed","false");
 button.append(create("span","",String(i+1).padStart(2,"0")),
               create("strong","",m.name));
 button.addEventListener("click",()=>select(m.id));
 nav.append(button);
}
const details={
 measurement:"Reconciled synthetic metrics and named evidence gaps.",
 decision:"Explicit hypothetical choices, not predictions.",
 recommendation:"Ranked review opportunities without guaranteed impact.",
 automation:"Review-only planning. No sending, publishing or real tools.",
 learning:"Descriptive comparison without causal income claims."
};
const engines=$("engines");
for(const [i,e] of map.engines.entries()){
 const box=create("article");
 box.append(create("small","",String(i+1).padStart(2,"0")+" / SHARED ENGINE"),
            create("h3","",pretty(e.id)),
            create("p","",details[e.id]));
 engines.append(box);
}
const modelBox=$("models");
for(const m of map.candidate_models){
 const card=create("article");
 card.append(create("h3","",m.id),
             create("span","","Official ID · not evaluated"),
             create("p","",
               "No paid connection, quality score, production routing or benchmark claim."));
 modelBox.append(card);
}
select(map.modules[0].id);
})();