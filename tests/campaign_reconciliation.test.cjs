"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const engine = require("../apps/site/assets/campaign-reconcile-engine.js");
const dated = require("../apps/site/assets/campaign-engine.js").DATED_HEADER.join(",");
const movements = engine.MOVEMENT_HEADER.join(",");
const prev = ["CAP-01,Branded Cap,10,2,850000,counted,complete,2026-10-18,2026-10-12,2026-10-18"];
const now = ["CAP-01,Branded Cap,11,3,850000,counted,complete,2026-10-25,2026-10-19,2026-10-25"];
const ledger = ["CAP-01,2026-10-19,2026-10-25,4,1,-1,3"];
const inventory = rows => [dated,...rows].join("\n")+"\n";
const journal = rows => [movements,...rows].join("\n")+"\n";
const make = (a=prev,b=now,c=ledger,date="2026-10-25") =>
  engine.reconcile(inventory(a),inventory(b),journal(c),date);

test("matches only deterministic arithmetic and comparable seven-day self-declared sales", () => {
  const r = make();
  assert.equal(r.kind, "STOCK_SNAPSHOT_RECONCILIATION");
  assert.equal(r.classification, "USER_SUPPLIED_UNVERIFIED");
  assert.equal(r.counts.declaredArithmeticMatches, 1);
  assert.equal(r.counts.reviewRequired, 0);
  assert.equal(r.rows[0].status, "DECLARED_ARITHMETIC_MATCH");
  assert.equal(r.rows[0].expectedStock, 11);
  assert.equal(r.rows[0].differenceUnits, 0);
  assert.equal(r.rows[0].comparedWeeklySales, true);
  assert.equal(r.safeguards.sourceRecordsVerified, false);
  assert.equal(r.safeguards.businessRevenueVerified, false);
  assert.equal(r.safeguards.reportDigitallySigned, false);
});

test("stock discrepancies remain visible even if a sale number agrees", () => {
  const r=make(prev,["CAP-01,Branded Cap,12,3,850000,counted,complete,2026-10-25,2026-10-19,2026-10-25"]);
  assert.equal(r.rows[0].status,"STOCK_ARITHMETIC_CONFLICT");
  assert.equal(r.rows[0].differenceUnits,1);
  assert.equal(r.counts.stockConflicts,1);
  assert.match(r.rows[0].issues.join(" "),/differs/);
});

test("conflicting comparable weekly sales are flagged, not turned into campaign lift", () => {
  const r=make(prev,["CAP-01,Branded Cap,11,4,850000,counted,complete,2026-10-25,2026-10-19,2026-10-25"]);
  assert.equal(r.rows[0].status,"SALES_COUNT_CONFLICT");
  assert.equal(r.rows[0].comparedWeeklySales,true);
  assert.equal(r.counts.salesConflicts,1);
  assert.match(r.rows[0].issues.join(" "),/contradict/);
});

test("overlapping but non-identical weekly period must not be compared", () => {
  const r=make(prev,["CAP-01,Branded Cap,11,500,850000,counted,complete,2026-10-25,2026-10-18,2026-10-24"]);
  assert.equal(r.rows[0].status,"ARITHMETIC_ONLY_SALES_NOT_COMPARABLE");
  assert.equal(r.rows[0].comparedWeeklySales,false);
  assert.equal(r.rows[0].differenceUnits,0);
  assert.equal(r.counts.salesConflicts,0);
});

test("incomplete self-declared sales coverage prevents comparable sales assertion", () => {
  const r=make(prev,["CAP-01,Branded Cap,11,3,850000,counted,partial,2026-10-25,2026-10-19,2026-10-25"]);
  assert.equal(r.rows[0].status,"ARITHMETIC_ONLY_SALES_NOT_COMPARABLE");
  assert.equal(r.rows[0].comparedWeeklySales,false);
});

test("missing movement ledger and missing SKU are NOT assumed zero inventory or sold", () => {
  const p=[...prev,"FAB-02,Kaftan,8,1,3500000,counted,complete,2026-10-18,2026-10-12,2026-10-18"];
  const c=[...now,"SHOE-03,Shoes,4,2,1000000,counted,complete,2026-10-25,2026-10-19,2026-10-25"];
  const rows=make(p,c).rows;
  assert.deepEqual(rows.map(row=>row.sku),["CAP-01","FAB-02","SHOE-03"]);
  assert.equal(rows[1].status,"MISSING_CURRENT_SKU");
  assert.equal(rows[2].status,"NEW_CURRENT_SKU");
  assert.equal(rows[1].differenceUnits,null);
  assert.equal(rows[2].expectedStock,null);
  assert.equal(make([...prev,"FAB-02,Kaftan,8,1,3500000,counted,complete,2026-10-18,2026-10-12,2026-10-18"],
    [...now,"FAB-02,Kaftan,8,1,3500000,counted,complete,2026-10-25,2026-10-19,2026-10-25"]).rows[1].status,
    "MISSING_MOVEMENT_LEDGER");
});

test("misaligned movement dates, future observations and stale snapshots cannot match", () => {
  assert.equal(make(prev,now,["CAP-01,2026-10-18,2026-10-25,4,1,-1,3"]).rows[0].status,
    "INPUTS_NOT_COMPARABLE");
  assert.equal(make(prev,now,ledger,"2026-10-24").rows[0].status,"INPUTS_NOT_COMPARABLE");
  assert.equal(make(prev,now,ledger,"2026-11-02").rows[0].status,"INPUTS_NOT_COMPARABLE");
  const old=["CAP-01,Branded Cap,10,2,850000,counted,complete,2026-07-01,2026-06-25,2026-07-01"];
  assert.equal(make(old,now,ledger).rows[0].status,"INPUTS_NOT_COMPARABLE");
});

test("unchecked stock declarations and impossible negative expected stock stay unresolved", () => {
  const unknown=["CAP-01,Branded Cap,11,3,850000,unknown,complete,2026-10-25,2026-10-19,2026-10-25"];
  assert.equal(make(prev,unknown).rows[0].status,"INPUTS_NOT_COMPARABLE");
  const excessive=["CAP-01,2026-10-19,2026-10-25,0,0,0,100"];
  const result=make(prev,now,excessive);
  assert.equal(result.rows[0].status,"STOCK_ARITHMETIC_CONFLICT");
  assert.ok(result.rows[0].expectedStock<0);
});

test("ledger rejects invalid numeric formats, duplicate SKU and orphan rows", () => {
  for(const [value,col] of [["1e4",3],["-1",3],["+2",3],["2.5",6],["1000001",6]]){
    const parts=ledger[0].split(",");parts[col]=value;
    assert.throws(()=>make(prev,now,[parts.join(",")]),engine.ReconciliationError);
  }
  assert.throws(()=>make(prev,now,[...ledger,...ledger]),/duplicates SKU/);
  assert.throws(()=>make(prev,now,["BAD-10,2026-10-19,2026-10-25,1,0,0,1"]),/must exist in both/);
  assert.throws(()=>engine.parseMovementLedger(movements+"\n"),/between 1 and 400/);
  assert.throws(()=>engine.parseMovementLedger(movements+"\n"+ledger[0].replace("2026-10-19","2026-02-30")+"\n"),/calendar date/);
  assert.throws(()=>engine.parseMovementLedger(movements+"\n"+ledger[0].replace("2026-10-19","2026-10-26")+"\n"),/ends before/);
});

test("reconciliation requires exact dated 10-column snapshots and precise UTC as-of", () => {
  const legacy=["sku,name,stock,weekly_sales,unit_price_kobo","CAP-01,Branded Cap,11,3,850000"].join("\n")+"\n";
  assert.throws(()=>engine.reconcile(legacy,inventory(now),journal(ledger),"2026-10-25"),/ten-column dated/);
  assert.throws(()=>make(prev,now,ledger,"2026-02-30"),/calendar date/);
  assert.throws(()=>make(prev,now,ledger,"bad"),/YYYY-MM-DD/);
});

test("canonical report is reproducible across row order, independent of input line order", () => {
  const p=[...prev,"FAB-02,Kaftan,8,1,3500000,counted,complete,2026-10-18,2026-10-12,2026-10-18"];
  const c=[...now,"FAB-02,Kaftan,8,1,3500000,counted,complete,2026-10-25,2026-10-19,2026-10-25"];
  const m=[...ledger,"FAB-02,2026-10-19,2026-10-25,2,0,0,1"];
  const a=engine.canonicalJson(make(p,c,m)), b=engine.canonicalJson(make([...p].reverse(),[...c].reverse(),[...m].reverse()));
  assert.equal(a,b);
  assert.match(a,/"sourceIntegrity": "UNAUTHENTICATED_USER_IMPORTS"/);
  assert.equal(crypto.createHash("sha256").update(a,"utf8").digest("hex").length,64);
  assert.throws(()=>engine.canonicalJson({kind:"OTHER"}),engine.ReconciliationError);
});

test("domain module cannot silently introduce network, storage or model behavior", () => {
  const fs=require("node:fs");
  const src=fs.readFileSync(require("node:path").join(__dirname,"../apps/site/assets/campaign-reconcile-engine.js"),"utf8");
  assert.doesNotMatch(src,/\b(fetch|XMLHttpRequest|localStorage|sessionStorage|WebSocket)\s*[(.]/);
  assert.doesNotMatch(src,/model\.infer|provider\.publish/);
});


test("reused SKU with a different product name requires review, not a clean match", () => {
  const renamed = ["CAP-01,Entirely Different Product,11,3,850000,counted,complete,2026-10-25,2026-10-19,2026-10-25"];
  const r = make(prev, renamed);
  assert.equal(r.rows[0].status, "INPUTS_NOT_COMPARABLE");
  assert.equal(r.rows[0].expectedStock, null);
  assert.equal(r.counts.declaredArithmeticMatches, 0);
  assert.match(r.rows[0].issues.join(" "), /Product name changed/);
});
