/* P2-03p WhatsApp lead-generation policy lab: strictly local, synthetic, no dispatch. */
(() => {
  "use strict";
  const source = window.MetaAutomateWhatsAppScenario;
  const $ = id => document.getElementById(id);
  const options = {
    CTWA_AD:"Click-to-WhatsApp advertisement (simulated)",
    WEBSITE_LINK:"Website chat link (simulated)",
    QR_CODE:"QR code (simulated)",
    OWNED_LINK:"Owned business link (simulated)"
  };
  if (!source || source.schema_version !== 1 ||
      source.classification !== "SYNTHETIC_SOURCE_ONLY" ||
      !Array.isArray(source.leads)) {
    $("decision-status").textContent = "Source unavailable";
    return;
  }
  const allowed = new Set(["workspace","lead_id","entry","source_reference",
    "last_user_message_at","qualification","message_purpose","optin","opted_out",
    "template_state","agent_available"]);
  const safeLeads = source.leads.every(l =>
    Object.keys(l).length === allowed.size &&
    Object.keys(l).every(k=>allowed.has(k)) &&
    /^SIM-LEAD-[A-Z0-9-]+$/.test(l.lead_id) &&
    Object.keys(l.qualification).sort().join("|") ===
      ["budget_band","interest","location_band","timeline"].join("|") &&
    !("phone_number" in l) && !("email" in l));
  if (!safeLeads) {
    $("decision-status").textContent = "Unsafe source fields rejected";
    return;
  }
  let current = null;
  const copiedAnswers = {};
  const named = s => (s || "UNKNOWN").replaceAll("_"," ").toLowerCase();
  const readable = s => named(s).replace(/\b\w/g,x=>x.toUpperCase());
  const addLine=(label,value)=>{
    const row=document.createElement("div");row.className="ledger-row";
    const a=document.createElement("span");a.textContent=label;
    const b=document.createElement("strong");b.textContent=value;
    row.append(a,b);$("policy-ledger").append(row);
  };
  const within24h = lead => {
    if (!lead.last_user_message_at)return false;
    const elapsed=Date.parse(source.evaluated_at)-Date.parse(lead.last_user_message_at);
    return Number.isFinite(elapsed) && elapsed >= 0 && elapsed < 24*60*60*1000;
  };
  const qualification = lead => {
    const answers=copiedAnswers[lead.lead_id] || lead.qualification;
    return Object.values(answers).every(v=>v!=="UNKNOWN");
  };
  function decision(lead) {
    if (!lead.last_user_message_at)
      return {status:"No conversation yet",reason:"A link or advertisement click is not an inbound WhatsApp message.",route:"NOT_A_LEAD",code:"NO_MESSAGE_NO_CONTACT"};
    if (lead.opted_out)
      return {status:"Communication suppressed",reason:"Opt-out has priority over qualification, templates and all marketing follow-ups.",route:"SUPPRESSED",code:"SUPPRESS_OPT_OUT"};
    const qualified=qualification(lead);
    const route=(qualified && lead.agent_available)?"HUMAN_HANDOVER_REVIEW":"HUMAN_QUEUE_REVIEW";
    if(lead.message_purpose==="SERVICE" && within24h(lead))
      return {status:"Service reply review",reason:"The illustrative last inbound message is inside the 24-hour window. Human review remains required.",route,code:"REVIEW_IN_WINDOW_SERVICE_REPLY"};
    const appropriateConsent=lead.message_purpose==="MARKETING"?
      lead.optin.marketing:lead.message_purpose==="UTILITY"?lead.optin.utility:false;
    if(appropriateConsent && lead.template_state==="APPROVED")
      return {status:"Approved-template review",reason:"This illustrative case has matching opt-in and approved-template flags. Live validity is not verified.",route,code:"REVIEW_APPROVED_TEMPLATE_ONLY"};
    return {status:"Hold · no approved messaging path",reason:"Outside the service window or without appropriate opt-in and template approval. Do not send follow-ups.",route,code:"HOLD_NO_AUTHORIZED_MESSAGE_PATH"};
  }
  function refreshLeads() {
    const ws=$("business-select").value;
    const select=$("lead-select"); select.replaceChildren();
    source.leads.filter(l=>l.workspace===ws).forEach(l=>{
      const opt=document.createElement("option");
      opt.value=l.lead_id;
      opt.textContent=l.lead_id+" · "+readable(l.entry);
      select.append(opt);
    });
    refreshCase();
  }
  function refreshCase() {
    current=source.leads.find(l=>l.lead_id===$("lead-select").value &&
      l.workspace===$("business-select").value);
    if(!current){
      $("decision-status").textContent="No invented scenario available";
      return;
    }
    copiedAnswers[current.lead_id]={...current.qualification};
    for (const name of ["interest","budget_band","location_band","timeline"])
      $(name).value=copiedAnswers[current.lead_id][name];
    render();
  }
  function render() {
    if(!current)return;
    const verdict=decision(current);
    const answer=copiedAnswers[current.lead_id];
    $("entry-value").textContent=options[current.entry] || "Unsupported entry";
    $("qualification-value").textContent=(qualification(current)?"Four answers recorded":"Needs qualification")+" · simulated";
    $("consent-value").textContent=current.opted_out?"Opt-out · do not contact":
      current.optin.marketing?"Marketing opt-in illustrated":"No marketing opt-in proven";
    $("route-value").textContent=readable(verdict.route);
    $("decision-status").textContent=verdict.status;
    $("decision-text").textContent=verdict.reason;
    const ledger=$("policy-ledger");ledger.replaceChildren();
    addLine("Source tag",current.source_reference+" (unverified)");
    addLine("User-initiated message",current.last_user_message_at?"Simulated yes":"No");
    addLine("Customer service window",within24h(current)?"Illustratively open":"Closed / never opened");
    addLine("Message purpose",readable(current.message_purpose));
    addLine("Marketing consent",current.optin.marketing?"Illustrative only":"Not present");
    addLine("Template status",readable(current.template_state)+" · not live-verified");
    addLine("Suggested action",readable(verdict.code)+" (review only)");
    addLine("Messages sent","0 · disabled");
    addLine("Provider attribution","Not verified");
    addLine("Identity verification","Not established");
    const missing=Object.entries(answer).filter(([,val])=>val==="UNKNOWN").length;
    $("qualification-value").textContent=(missing===0?"4 of 4 fields":"Needs "+missing+" answer"+(missing===1?"":"s"))+" · simulated";
  }
  $("business-select").addEventListener("change",refreshLeads);
  $("lead-select").addEventListener("change",refreshCase);
  for(const key of ["interest","budget_band","location_band","timeline"]){
    $(key).addEventListener("change",e=>{
      if(!current)return;
      copiedAnswers[current.lead_id][key]=e.target.value;
      render();
    });
  }
  $("restore").addEventListener("click",()=>{
    if(!current)return;
    copiedAnswers[current.lead_id]={...current.qualification};
    for(const key of ["interest","budget_band","location_band","timeline"])
      $(key).value=current.qualification[key];
    render();
  });
  refreshLeads();
})();
