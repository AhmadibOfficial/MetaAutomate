/* P2-03s: offline scenario arithmetic only; no predictions, accounts or dispatch. */
(() => {
"use strict";
const DATA = window.MetaAutomateContinuityData;
const $ = id => document.getElementById(id);
const SCENARIOS = Object.freeze({
  UNCHANGED:[0,0], DEMAND_DOWN_25:[2500,0],
  OPERATIONAL_COST_UP_20:[0,2000], COMBINED_STRESS:[2500,2000]
});
const N = new Intl.NumberFormat("en-US",{maximumFractionDigits:0});
const num = value => (value<0?"−":"")+N.format(Math.abs(value));
const label = text => String(text).toLowerCase().replaceAll("_"," ")
  .replace(/\b\w/g,ch=>ch.toUpperCase());
function element(tag,klass,text){
 const node=document.createElement(tag);
 if(klass)node.className=klass;
 node.textContent=text;
 return node;
}
function row(name,value){
 const div=element("div","ledger-row","");
 div.append(element("span","",name),element("strong","",value));
 return div;
}
function metric(name,value,detail){
 const div=element("div","kpi","");
 div.append(element("small","",name),element("strong","",value),
            element("span","",detail));
 return div;
}
if(!DATA||DATA.schema_version!==1||DATA.classification!=="SYNTHETIC_SOURCE_ONLY"||
   DATA.units!=="DEMO_CREDITS_NOT_CURRENCY" ||
   !DATA.workspaces||Object.keys(DATA.workspaces).sort().join("|")!=="academy_demo|bespoke_demo"){
 $("risk-list").textContent="Validated synthetic evidence unavailable";return;
}
function render(){
 const ws=$("business").value;
 const data=DATA.workspaces[ws];
 if(!data||!data.financial||!Array.isArray(data.risks)){
   $("risk-list").textContent="No approved example";return;
 }
 const f=data.financial,o=data.operational;
 if(f.gross_sales-f.identified_costs!==f.modeled_contribution ||
    typeof f.identified_cost_to_sales_bps!=="number" ||
    f.identified_cost_to_sales_bps!==
      Math.floor(f.identified_costs*10000/f.gross_sales)){
   $("risk-list").textContent="Financial evidence reconciliation failed";
   $("kpis").replaceChildren();return;
 }
 const kpis=$("kpis");kpis.replaceChildren(
   metric("Illustrative gross sales",num(f.gross_sales),"Demo credits · not verified sales"),
   metric("Identified costs",num(f.identified_costs),"Known example expense categories"),
   metric("Modeled contribution",num(f.modeled_contribution),"Not verified net profit"),
   metric("Cost-to-sales ratio",(f.identified_cost_to_sales_bps/100).toFixed(1)+"%",
          "Identified costs only; coverage incomplete")
 );
 const list=$("risk-list");list.replaceChildren();
 for(const item of data.risks){
   const card=element("article","risk-card","");
   card.append(
     element("small","", "REVIEW PRIORITY · "+item.priority+" / 25 (ORDINAL)"),
     element("h3","",label(item.code)),
     element("p","","") // replaced below for strict text-only DOM
   );
   card.lastChild.textContent="Human action: "+item.manual_action;
   card.append(element("p","", "Illustrative exposure: "+num(item.exposure_example)+
        " · example mitigation cost: "+num(item.mitigation_example)+" demo credits"),
        element("strong","", "No incident probability or verified savings"));
   list.append(card);
 }
 const signals=$("signals");signals.replaceChildren(
   row("Service downtime (example hours)",num(o.service_downtime_hours)),
   row("Supplier deliveries needing review",num(o.late_supplier_deliveries)),
   row("Expense entries needing reconciliation",num(o.unreconciled_cost_entries)),
   row("Unused software seats to investigate",num(o.unused_tool_seats)),
   row("Identified costs above sample budget",num(f.cost_over_budget)+" demo credits")
 );
 const [salesDrop,costIncrease]=SCENARIOS[$("scenario").value]||SCENARIOS.UNCHANGED;
 const gross=Math.floor(f.gross_sales*(10000-salesDrop)/10000);
 const costs=Math.floor(f.identified_costs*(10000+costIncrease)/10000);
 const contribution=gross-costs;
 $("scenario-results").replaceChildren(
   metric("Scenario gross sales",num(gross),"Assumption only · demo credits"),
   metric("Scenario identified costs",num(costs),"Other costs not separately modeled"),
   metric("Scenario contribution",num(contribution),
      "Difference vs. example baseline: "+num(contribution-f.modeled_contribution))
 );
}
$("business").addEventListener("change",render);
$("scenario").addEventListener("change",render);
render();
})();