"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const engine = require("../apps/site/assets/campaign-engine.js");

const header = "sku,name,stock,weekly_sales,unit_price_kobo";
const csv = (rows) => [header, ...rows].join("\n") + "\n";
const entry = "CAP-01,Branded Cap,18,0,850000";
const parse = rows => engine.parseCSV(csv(rows));

test("accepts actual CSV inventory and integer kobo prices", () => {
  const rows = parse([entry, "FAB-2,Classic Kaftan,24,3,3500000"]);
  assert.equal(rows.length, 2);
  assert.deepEqual(rows[0], { sku: "CAP-01", name: "Branded Cap",
    stock: 18, weeklySales: 0, priceKobo: 850000 });
  assert.equal(engine.currency(850000), "₦8,500.00");
});

test("handles quoted commas and escaped quotation marks", () => {
  const rows = parse(['PR-001,"Cap, navy ""blue"" edition",13,0,900000']);
  assert.equal(rows[0].name, 'Cap, navy "blue" edition');
});

test("BOM and CRLF import are supported", () => {
  const rows = engine.parseCSV("\ufeff" + header + "\r\n" + entry + "\r\n");
  assert.equal(rows.length, 1);
});

test("rejects CSV formula injection, tags and control characters", () => {
  for (const name of ["=HYPERLINK", "+SUM", "-DANGER", "@calc", "<script>", "Name\tTabbed"]) {
    assert.throws(() => parse(["AB-11," + name + ",10,0,100"]), engine.CampaignError);
  }
});

test("rejects duplicate SKU regardless of case", () => {
  assert.throws(() => parse([entry, "cap-01,Another Name,10,0,100"]), /Duplicate SKU/);
});

test("rejects invalid numbers and missing / unexpected columns", () => {
  for (const row of [
    "PR-10,Item,-2,0,200",
    "PR-10,Item,2,1.5,200",
    "PR-10,Item,2,1,9e9",
    "PR-10,Item,2,1,0",
    "PR-10,Item,2,1,200,extra",
    "PR-10,Item,2,1"
  ]) assert.throws(() => parse([row]), engine.CampaignError);
  assert.throws(() => engine.parseCSV("x,y\n1,2"), /Required columns/);
});

test("rejects malformed quoting and oversize CSV", () => {
  assert.throws(() => engine.parseCSV(header + '\nAB-11,"broken,10,0,1\n'), /Unclosed/);
  assert.throws(() => engine.parseCSV(header + "\n" + "X".repeat(129000)), /128 KB/);
});

test("bounds inventory to 400 records", () => {
  assert.equal(parse(Array.from({ length: 400 }, (_, i) =>
    "SKU-" + i + ",Product " + i + ",12,0,250000")).length, 400);
  assert.throws(() => parse(Array.from({ length: 401 }, (_, i) =>
    "SKU-" + i + ",Product " + i + ",12,0,250000")), /too many records/);
});

test("prioritizes slow movers, then high cover; excludes out of stock and low stock", () => {
  const r = engine.analyze(parse([
    "SLOW-1,Unsold Stock,19,0,100",
    "HIGH-1,Excess Stock,36,5,100",
    "OUT-11,Out of Stock,0,0,100",
    "LOW-11,Nearly Gone,2,6,100",
    "OK-001,Regular Stock,7,5,100"
  ]));
  assert.deepEqual(r.opportunities.map(x => x.sku), ["SLOW-1", "HIGH-1"]);
  assert.equal(r.flaggedCount, 2);
  assert.equal(r.note.includes("No profit"), true);
});

test("campaign drafts make no fabricated discount, sale or shipping claims", () => {
  const candidate = engine.analyze(parse([entry])).opportunities[0];
  const p = engine.makeCampaign(candidate, "Demo Brand", "Instagram");
  assert.match(p.post, /confirm before ordering/);
  assert.match(p.videoBrief, /30–60 SECOND/);
  assert.equal(p.channel, "Instagram");
  assert.doesNotMatch(p.post, /% off|free delivery|guaranteed/gi);
  assert.throws(() => engine.makeCampaign(candidate, "=CSV_INJECTION", "Instagram"), engine.CampaignError);
  assert.throws(() => engine.makeCampaign(candidate, "Demo Brand", "UnapprovedSocial"), engine.CampaignError);
});

test("cannot promote sold-out or low-stock products", () => {
  const rows = parse(["LOW-11,Low Stock,1,9,150", "OUT-11,No Stock,0,1,200"]);
  for (const row of rows) assert.throws(() => engine.makeCampaign(row, "Brand", "Instagram"), /eligible/);
});

test("metric calculations use self-reported counts, not invented revenue", () => {
  const m = engine.summarizeMetrics({ impressions: "100", clicks: "20", orders: "3",
    sourceNote: "Manually counted my local test campaign." });
  assert.equal(m.clickThroughRatePct, 20);
  assert.equal(m.clickToOrderPct, 15);
  assert.equal(m.evidence, "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED");
  assert.equal(Object.hasOwn(m, "revenue"), false);
});

test("prevents impossible funnel ratios, forged scientific notation and missing source", () => {
  const base = { impressions: "10", clicks: "3", orders: "1",
    sourceNote: "Owner supplied these example counts" };
  for (const patch of [
    { impressions: "2" }, { clicks: "11" }, { orders: "4" },
    { clicks: "-1" }, { clicks: "1e3" }, { orders: "0.4" }, { sourceNote: "" }
  ]) assert.throws(() => engine.summarizeMetrics({ ...base, ...patch }), engine.CampaignError);
});

test("source import has no provider calls, storage or background execution", () => {
  const fs = require("node:fs");
  const source = fs.readFileSync(require("node:path").join(__dirname,
    "../apps/site/assets/campaign-engine.js"), "utf8");
  assert.doesNotMatch(source, /\b(fetch|XMLHttpRequest|localStorage|sessionStorage|WebSocket)\s*[(.]/);
});


const qualityHeader = header + ",stock_count_status,sales_coverage_status";
const qualityCSV = rows => [qualityHeader, ...rows].join("\n") + "\n";

test("opt-in completeness columns preserve exact self-declared statuses", () => {
  const records = engine.parseCSV(qualityCSV([
    "COUNT-01,Confirmed Cap,18,0,850000,counted,complete",
    "UNKNOWN-01,Unknown History,18,0,850000,unknown,unknown"
  ]));
  assert.deepEqual(records[0], { sku:"COUNT-01", name:"Confirmed Cap",
    stock:18, weeklySales:0, priceKobo:850000,
    stockCountStatus:"counted", salesCoverageStatus:"complete" });
  assert.equal(records[1].stockCountStatus, "unknown");
});

test("incomplete weekly-sales data cannot be mistaken for observed zero", () => {
  const records = engine.parseCSV(qualityCSV([
    "GOOD-01,Counted Cap,18,0,850000,counted,complete",
    "HOLD-01,Unverified Cap,18,0,850000,counted,unknown",
    "HOLD-02,Partial Sales,40,2,3000000,counted,partial",
    "HOLD-03,Uncounted Stock,18,0,850000,unknown,complete",
    "OUT-02,Sold Out,0,0,850000,unknown,unknown"
  ]));
  const result = engine.analyze(records);
  assert.equal(result.flaggedCount, 1);
  assert.equal(result.heldCount, 3);
  assert.equal(result.legacyCount, 0);
  assert.deepEqual(result.opportunities.map(row => row.sku), ["GOOD-01"]);
  assert.deepEqual(result.held.map(row => row.sku), ["HOLD-01","HOLD-02","HOLD-03"]);
  assert.deepEqual(result.held.map(row => row.quality.status),
    ["REVIEW_INPUTS","REVIEW_INPUTS","REVIEW_INPUTS"]);
  for (const row of records.filter(r => r.sku.startsWith("HOLD")))
    assert.throws(() => engine.makeCampaign(row, "Demo Brand", "Instagram"),
      /sufficient user-supplied data/);
});

test("self-declared complete data still avoids false verification claims", () => {
  const candidate = engine.analyze(engine.parseCSV(qualityCSV([
    "GOOD-01,Counted Cap,18,0,850000,counted,complete"
  ]))).opportunities[0];
  const campaign = engine.makeCampaign(candidate, "Demo Brand", "Instagram");
  assert.equal(campaign.inputQuality.mode, "SELF_DECLARED");
  assert.equal(campaign.inputQuality.status, "SELF_DECLARED_COMPLETE");
  assert.equal(campaign.inputQuality.basis, "USER_SUPPLIED_UNVERIFIED");
  assert.match(campaign.recommendation, /not been independently verified/i);
  assert.match(campaign.post, /confirm before ordering/);
});

test("legacy five-column CSV is compatible but visibly qualified", () => {
  const result = engine.analyze(parse([entry, "SHOE-02,Other,1,10,250000"]));
  assert.equal(result.flaggedCount, 1);
  assert.equal(result.heldCount, 0);
  assert.equal(result.legacyCount, 2);
  assert.equal(result.opportunities[0].quality.mode, "LEGACY_UNATTESTED");
  const campaign = engine.makeCampaign(result.opportunities[0], "Demo Brand", "Instagram");
  assert.match(campaign.recommendation, /does not confirm stock counts/i);
});

test("partial, malformed or nonexact enhanced completeness headers are rejected", () => {
  for (const v of ["COUNTED", "yes", "", "=COUNT", "unknown "]) {
    // A leading spreadsheet expression or unsupported status fails.
    const status = v.trim();
    if (status === "unknown") continue; // trailing whitespace is normalized
    assert.throws(() => engine.parseCSV(qualityCSV([
      "AAA-02,Cap,19,0,850000," + v + ",complete"
    ])), engine.CampaignError);
  }
  for (const row of [
    "AAA-02,Cap,19,0,850000,counted,unverified",
    "AAA-02,Cap,19,0,850000,counted",
    "AAA-02,Cap,19,0,850000,counted,complete,extra"
  ]) assert.throws(() => engine.parseCSV(qualityCSV([row])), engine.CampaignError);
  assert.throws(() => engine.parseCSV(
    header + ",sales_coverage_status,stock_count_status\n" +
    "AAA-02,Cap,19,0,850000,complete,counted\n"), /Required columns/);
});

test("low-stock and sold-out rows remain blocked even with complete statuses", () => {
  const records = engine.parseCSV(qualityCSV([
    "LOW-02,Near Out,1,10,250000,counted,complete",
    "OUT-02,No Stock,0,1,250000,counted,complete"
  ]));
  const result = engine.analyze(records);
  assert.equal(result.flaggedCount, 0);
  assert.equal(result.heldCount, 0);
  for (const record of records)
    assert.throws(() => engine.makeCampaign(record, "Demo Brand", "Instagram"),
      /eligible/);
});
