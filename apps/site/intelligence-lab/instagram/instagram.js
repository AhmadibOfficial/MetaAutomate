/* P2-03q: strictly invented Instagram scenarios; browser cannot send or store messages. */
(() => {
"use strict";
const DATA=window.MetaAutomateInstagramScenario;
const $=id=>document.getElementById(id);
const CHANNELS={
 INSTANT_FORM:"Instagram Lead Ad · instant form",
 ORGANIC_DM:"User-initiated organic DM",
 CLICK_TO_DIRECT:"Click-to-Direct advertisement",
 COMMENT_KEYWORD:"Comment keyword on owned media",
 LINK_IN_BIO:"Profile link-in-bio click"
};
if(!DATA || DATA.schema_version!==1 || DATA.classification!=="SYNTHETIC_SOURCE_ONLY" || !Array.isArray(DATA.records)){
  $("decision").textContent="Synthetic source unavailable";return;
}
const expected=["agent_available","channel","comment_at","event_id","first_ad_message_at","has_marketing_optin",
 "keyword_match","last_user_message_at","opted_out","private_reply_used","qualification","source_ref","submitted","workspace"];
if(!DATA.records.every(x=>Object.keys(x).sort().join("|")===expected.join("|") &&
 /^[A-Z0-9-]+$/.test(x.event_id) && x.event_id.startsWith("SIM-IG-") &&
 !("email" in x) && !("phone" in x) && !("access_token" in x))){
 $("decision").textContent="Unsafe source fields rejected";return;
}
let current=null;
let edits={};
const questionIds=["interest","budget_band","location_band","timeline"];
const label=x=>String(x).replaceAll("_"," ").toLowerCase().replace(/\b\w/g,c=>c.toUpperCase());
const days=7*86400*1000;
const service=24*3600*1000;
function within(time,limit){
 if(!time)return false;
 const ms=Date.parse(DATA.evaluated_at)-Date.parse(time);
 return Number.isFinite(ms)&&ms>=0&&ms<limit;
}
function outcome(r){
 if(r.opted_out)return ["SUPPRESS_OPT_OUT","Do not contact. The example opted out of further communication."];
 if(r.channel==="INSTANT_FORM")
   return r.submitted?["LEAD_FORM_CRM_REVIEW","A submitted instant form needs authorized lead retrieval and secure CRM review; it does not open a DM."]:
     ["NO_SUBMISSION_NO_LEAD","Opening an instant form alone does not create a submitted lead."];
 if(r.channel==="LINK_IN_BIO")return ["NO_SUBMISSION_NO_CHAT","A bio link click alone provides neither consent nor an inbound conversation."];
 if(r.channel==="COMMENT_KEYWORD")
   return (r.keyword_match&&!r.private_reply_used&&within(r.comment_at,days))?
    ["REVIEW_SINGLE_PRIVATE_REPLY_ONLY","A single restricted private reply may be reviewed for eligible owned-media comments. No ongoing DM permission is assumed."]:
    ["HOLD_COMMENT_REPLY_INELIGIBLE","The comment window expired, the reply was already used, or the keyword did not match."];
 if(within(r.last_user_message_at,service))
   return ["REVIEW_INBOUND_DM_WITHIN_24H","The simulated inbound DM is inside the standard 24-hour window; independent account permission and human review are still required."];
 if(r.channel==="CLICK_TO_DIRECT"&&within(r.first_ad_message_at,days))
   return ["REVIEW_AD_WINDOW_ONLY_IF_ORIGIN_VERIFIED","Meta may allow up to seven days for qualifying ad-origin conversations; the real event provenance and policy eligibility must be independently verified."];
 return ["HOLD_DM_WINDOW_CLOSED","The ordinary reply window is closed and no verified eligible exception is available."];
}
function add(labelText,value){
 const row=document.createElement("div");row.className="ledger-row";
 const a=document.createElement("span");a.textContent=labelText;
 const b=document.createElement("strong");b.textContent=value;
 row.append(a,b);$("checks").append(row);
}
function render(){
 if(!current)return;
 const q=edits[current.event_id]||current.qualification;
 const [status,reason]=outcome(current);
 const qualified=questionIds.every(k=>q[k]!=="UNKNOWN");
 $("entry").textContent=CHANNELS[current.channel]||"Unknown source";
 $("qualification").textContent=qualified?"Four sample answers":"More detail needed";
 $("capture").textContent=current.submitted?"Example form submitted":
    current.last_user_message_at?"Inbound DM in example":"Engagement only · no CRM capture";
 $("handover").textContent=current.opted_out?"Opted out":
    qualified&&current.agent_available?"Human review priority":"Manual queue only";
 $("decision").textContent=label(status);
 $("reason").textContent=reason;
 $("checks").replaceChildren();
 add("Example source",current.source_ref+" · unverified");
 add("Acquisition path",CHANNELS[current.channel]);
 add("Submitted lead form",current.submitted?"Example yes":"No");
 add("Inbound DM",current.last_user_message_at?"Example yes":"No");
 add("Ordinary DM window",within(current.last_user_message_at,service)?"Illustratively open":"Closed / unavailable");
 add("Single private reply",current.channel==="COMMENT_KEYWORD"?
   (current.keyword_match&&!current.private_reply_used&&within(current.comment_at,days)?"Potentially reviewable":"Unavailable"):"Not applicable");
 add("Marketing opt-in",current.has_marketing_optin?"Invented flag · not verified":"Not proven");
 add("Ad attribution","Not verified");
 add("Actual messages sent","0 · disabled");
 add("CRM records written","0 · disabled");
}
function reset(){
 if(!current)return;
 edits[current.event_id]={...current.qualification};
 for(const id of questionIds)$(id).value=edits[current.event_id][id];
 render();
}
function load(){
 const ws=$("business").value,select=$("case");
 select.replaceChildren();
 for(const r of DATA.records.filter(r=>r.workspace===ws)){
   const opt=document.createElement("option");opt.value=r.event_id;
   opt.textContent=r.event_id+" · "+(CHANNELS[r.channel]||r.channel);
   select.append(opt);
 }
 choose();
}
function choose(){
 current=DATA.records.find(x=>x.workspace===$("business").value&&x.event_id===$("case").value);
 if(!current){$("decision").textContent="No example found";return;}
 reset();
}
$("business").addEventListener("change",load);
$("case").addEventListener("change",choose);
for(const id of questionIds)$(id).addEventListener("change",e=>{
 if(!current)return;
 edits[current.event_id][id]=e.target.value;render();
});
$("reset").addEventListener("click",reset);
load();
})();
