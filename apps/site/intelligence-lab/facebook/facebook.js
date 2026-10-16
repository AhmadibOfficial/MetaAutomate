/* P2-03r: Facebook Lead Ads review preview. No network, PII, payment or CRM writes. */
(() => {
"use strict";
const DATA=window.MetaAutomateFacebookLeads;
const $=id=>document.getElementById(id);
if(!DATA||DATA.schema_version!==1||DATA.classification!=="SYNTHETIC_SOURCE_ONLY"||
 DATA.platform!=="FACEBOOK"||!Array.isArray(DATA.examples)||
 DATA.examples.length!==2||DATA.real_contacts!==0||DATA.real_messages_sent!==0||
 DATA.lead_retrieval_enabled!==false){
 $("decision").textContent="Source contract unavailable";return;
}
const allowed=["event_ref","form_ref","form_submitted_in_example","lead_profile_retrieved",
 "marketing_consent_live_verified","outbound_allowed","source",
 "source_origin_verified_live","workspace"].join("|");
if(!DATA.examples.every(e=>Object.keys(e).sort().join("|")===allowed &&
 e.source==="FACEBOOK_INSTANT_FORM" &&
 /^SIM-[A-Z0-9-]+$/.test(e.event_ref) &&
 e.lead_profile_retrieved===false && e.marketing_consent_live_verified===false
 && e.outbound_allowed===false)){
 $("decision").textContent="Unsafe example data rejected";return;
}
function addLine(label,value){
 const row=document.createElement("div");row.className="ledger-row";
 const a=document.createElement("span");a.textContent=label;
 const b=document.createElement("strong");b.textContent=value;
 row.append(a,b);$("ledger").append(row);
}
function render(){
 const workspace=$("business").value;
 const item=DATA.examples.find(e=>e.workspace===workspace);
 if(!item){$("decision").textContent="No safe example";return;}
 const submitted=document.querySelector('input[name="formstage"]:checked').value==="SUBMITTED";
 const qualified=$("timeline").value!=="UNKNOWN";
 $("source").textContent="Demo form: "+item.form_ref;
 $("form-status").textContent=submitted?"Example submitted":"Opened but not submitted";
 $("crm-status").textContent=submitted?"Lead metadata · no personal data":"No submitted lead";
 $("route-status").textContent=submitted?"Human review queue":"Awaiting user submission";
 $("decision").textContent=submitted?"Review submitted lead metadata":"No lead until submission";
 $("reason").textContent=submitted?
    "A simulated signed leadgen event identifies the form but contains no customer profile. Authorized lead retrieval, purpose-specific privacy review and human action remain required.":
    "An opened prefilled form is not a submission. Do not create a CRM contact or begin messaging.";
 $("ledger").replaceChildren();
 addLine("Example Meta Page",workspace==="academy_demo"?"SIM-PAGE-ACADEMY":"SIM-PAGE-BESPOKE");
 addLine("Form ID",item.form_ref+" · synthetic");
 addLine("Lead notification",submitted?item.event_ref+" · sample":"Not generated");
 addLine("Qualification",qualified?"Timeline answer selected":"No timing answer");
 addLine("Lead profile retrieval","Disabled · not authorized");
 addLine("Actual marketing consent","Not verified");
 addLine("CRM persistence","Disabled");
 addLine("Real contact captured","None");
 addLine("Actual messages sent","0 · disabled");
}
$("business").addEventListener("change",()=>{
 $("interest").value=$("business").value==="academy_demo"?"TRAINING":"TAILORING";
 render();
});
for(const input of document.querySelectorAll('input[name="formstage"]'))
 input.addEventListener("change",render);
$("interest").addEventListener("change",render);
$("timeline").addEventListener("change",render);
render();
})();