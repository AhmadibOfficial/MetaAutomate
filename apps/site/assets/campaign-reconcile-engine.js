/* P2-060g | Synthetic-safe inventory snapshot reconciliation.
   Pure deterministic domain functions; no network/storage/AI or provider proof.
   Arithmetic can be checked, business source data cannot be authenticated. */
(function (root, factory) {
  "use strict";
  const campaign = typeof module === "object" && module.exports
    ? require("./campaign-engine.js") : root.MetaCampaign;
  const api = factory(campaign);
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.MetaReconcile = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function (campaign) {
  "use strict";
  if (!campaign) throw new Error("Inventory decision engine unavailable");
  const MOVEMENT_HEADER = [
    "sku", "period_start", "period_end", "received_units",
    "customer_returns_units", "adjustment_units", "sold_units"
  ];
  const MAX_INTERVAL_DAYS = 90, CURRENT_MAX_AGE_DAYS = 7;
  class ReconciliationError extends Error {
    constructor(message) { super(message); this.name = "ReconciliationError"; }
  }
  const fail = message => { throw new ReconciliationError(message); };
  function day(value, label) {
    if (typeof value !== "string" || !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(value))
      fail(label + " must be a YYYY-MM-DD UTC calendar date");
    const time = Date.parse(value + "T00:00:00Z");
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== value)
      fail(label + " is not a real calendar date");
    return time;
  }
  const dateFrom = time => new Date(time).toISOString().slice(0, 10);
  const daysBetween = (a, b) => Math.round((day(b, "End date") - day(a, "Start date")) / 86400000);
  const integer = (value, label, signed = false) => {
    const pattern = signed ? /^(0|[1-9][0-9]*|-[1-9][0-9]*)$/ : /^(0|[1-9][0-9]*)$/;
    if (typeof value !== "string" || !pattern.test(value)) fail(label + " must be a whole number");
    const number = Number(value);
    if (!Number.isSafeInteger(number) || Math.abs(number) > 1000000)
      fail(label + " exceeds the supported one-million-unit limit");
    return number;
  };
  function parseSnapshot(text, label) {
    if (typeof text !== "string") fail(label + " must be CSV text");
    const first = text.replace(/^\uFEFF/, "").split(/\r\n|\n/)[0];
    if (first !== campaign.DATED_HEADER.join(","))
      fail(label + " requires the exact ten-column dated inventory CSV format");
    let records;
    try { records = campaign.parseCSV(text); }
    catch (error) { fail(label + ": " + error.message); }
    for (const record of records) {
      if (typeof record.stockObservedOn !== "string" ||
          typeof record.salesPeriodStart !== "string" ||
          typeof record.salesPeriodEnd !== "string")
        fail(label + " has an incomplete dated inventory record");
      day(record.stockObservedOn, label + " stock observation");
      day(record.salesPeriodStart, label + " sales period start");
      day(record.salesPeriodEnd, label + " sales period end");
    }
    return records;
  }
  function parseMovementLedger(text) {
    if (typeof text !== "string" || !text.length ||
        new TextEncoder().encode(text).length > campaign.MAX_BYTES)
      fail("Movement ledger must be a nonempty CSV at most 128 KB");
    const rows = text.replace(/^\uFEFF/, "").split(/\r\n|\n/);
    if (rows.at(-1) === "") rows.pop();
    if (!rows.length || rows[0] !== MOVEMENT_HEADER.join(","))
      fail("Movement ledger requires the exact seven-column movement header");
    if (rows.length <= 1 || rows.length > campaign.MAX_ROWS + 1)
      fail("Movement ledger must contain between 1 and 400 records");
    const found = new Set();
    return rows.slice(1).map((line, i) => {
      const label = "Movement row " + (i + 2);
      if (!line || /[\r"<>]/.test(line)) fail(label + " contains malformed characters");
      const values = line.split(",");
      if (values.length !== MOVEMENT_HEADER.length) fail(label + " has wrong column count");
      const [sku, periodStart, periodEnd, received, returned, adjusted, sold] = values;
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{1,35}$/.test(sku))
        fail(label + " has invalid SKU");
      const key = sku.toLowerCase();
      if (found.has(key)) fail(label + " duplicates SKU " + sku);
      found.add(key);
      day(periodStart, label + " period_start");
      day(periodEnd, label + " period_end");
      if (day(periodEnd, label + " end") < day(periodStart, label + " start"))
        fail(label + " period ends before it starts");
      return {
        sku, periodStart, periodEnd,
        receivedUnits: integer(received, label + " received_units"),
        returnedUnits: integer(returned, label + " customer_returns_units"),
        adjustmentUnits: integer(adjusted, label + " adjustment_units", true),
        soldUnits: integer(sold, label + " sold_units")
      };
    });
  }
  const lookup = records => new Map(records.map(item => [item.sku.toLowerCase(), item]));
  function reconcile(previousCsv, currentCsv, movementCsv, referenceDate) {
    const asOfDate = referenceDate === undefined ?
      new Date().toISOString().slice(0, 10) : referenceDate;
    const asOfTime = day(asOfDate, "Assessment as-of date");
    const previous = parseSnapshot(previousCsv, "Previous snapshot");
    const current = parseSnapshot(currentCsv, "Current snapshot");
    const movement = parseMovementLedger(movementCsv);
    const old = lookup(previous), now = lookup(current), ledger = lookup(movement);
    for (const key of ledger.keys()) {
      if (!old.has(key) || !now.has(key))
        fail("Ledger SKU " + ledger.get(key).sku +
          " must exist in both dated snapshots; reconcile new or removed products separately");
    }
    const keys = [...new Set([...old.keys(), ...now.keys()])].sort();
    const rows = keys.map(key => {
      const p = old.get(key), c = now.get(key), m = ledger.get(key);
      const sku = c?.sku ?? p.sku;
      const issues = [];
      const row = {
        sku, product: c?.name ?? p?.name,
        previousStock: p?.stock ?? null, currentStock: c?.stock ?? null,
        previousObservedOn: p?.stockObservedOn ?? null,
        currentObservedOn: c?.stockObservedOn ?? null,
        currentWeeklySales: c?.weeklySales ?? null,
        movement: m ? {
          periodStart: m.periodStart, periodEnd: m.periodEnd,
          receivedUnits: m.receivedUnits, returnedUnits: m.returnedUnits,
          adjustmentUnits: m.adjustmentUnits, soldUnits: m.soldUnits
        } : null,
        expectedStock: null, differenceUnits: null, comparedWeeklySales: false,
        status: "", issues
      };
      if (!p || !c) {
        row.status = p ? "MISSING_CURRENT_SKU" : "NEW_CURRENT_SKU";
        issues.push("SKU absent from one dated snapshot; do not interpret as a sale or zero inventory");
        return row;
      }
      if (!m) {
        row.status = "MISSING_MOVEMENT_LEDGER";
        issues.push("No declared movement ledger row for this SKU");
        return row;
      }
      const prevTime = day(p.stockObservedOn, "Previous observation");
      const currTime = day(c.stockObservedOn, "Current observation");
      const span = Math.round((currTime - prevTime) / 86400000);
      if (p.name !== c.name) issues.push("Product name changed between snapshots; inspect source records");
      if (span <= 0 || span > MAX_INTERVAL_DAYS)
        issues.push("Stock observation interval must be 1 to 90 calendar days");
      if (prevTime > asOfTime || currTime > asOfTime)
        issues.push("Snapshot observation occurs after the UTC assessment date");
      if (Math.round((asOfTime - currTime) / 86400000) > CURRENT_MAX_AGE_DAYS)
        issues.push("Current snapshot is older than seven calendar days");
      if (p.stockCountStatus !== "counted" || c.stockCountStatus !== "counted")
        issues.push("Both inventory observations must be self-declared counted");
      const expectedStart = dateFrom(prevTime + 86400000);
      if (m.periodStart !== expectedStart || m.periodEnd !== c.stockObservedOn)
        issues.push("Movement ledger dates do not cover exactly the intervening stock dates");
      if (issues.some(issue => !issue.startsWith("Product name changed"))) {
        row.status = "INPUTS_NOT_COMPARABLE";
        return row;
      }
      row.expectedStock = p.stock + m.receivedUnits + m.returnedUnits +
        m.adjustmentUnits - m.soldUnits;
      row.differenceUnits = c.stock - row.expectedStock;
      if (row.expectedStock < 0) issues.push("Declared movements imply negative expected inventory");
      if (row.differenceUnits !== 0)
        issues.push("Observed current stock differs from the declared movement arithmetic");
      const salesComparable = c.salesCoverageStatus === "complete" &&
        c.salesPeriodStart === m.periodStart && c.salesPeriodEnd === m.periodEnd &&
        daysBetween(m.periodStart, m.periodEnd) === 6;
      row.comparedWeeklySales = salesComparable;
      if (salesComparable && c.weeklySales !== m.soldUnits)
        issues.push("Declared weekly sales contradict movement ledger sold units for the same period");
      if (!salesComparable)
        issues.push("Weekly sales are not comparable: declared period or coverage differs from ledger");
      row.status = row.expectedStock < 0 || row.differenceUnits !== 0
        ? "STOCK_ARITHMETIC_CONFLICT" : salesComparable && c.weeklySales !== m.soldUnits
          ? "SALES_COUNT_CONFLICT" : !salesComparable
            ? "ARITHMETIC_ONLY_SALES_NOT_COMPARABLE"
            : "DECLARED_ARITHMETIC_MATCH";
      return row;
    });
    const counts = {
      totalSkus: rows.length, declaredArithmeticMatches: rows.filter(
        r => r.status === "DECLARED_ARITHMETIC_MATCH").length,
      stockConflicts: rows.filter(r => r.status === "STOCK_ARITHMETIC_CONFLICT").length,
      salesConflicts: rows.filter(r => r.status === "SALES_COUNT_CONFLICT").length,
      reviewRequired: rows.filter(r => r.status !== "DECLARED_ARITHMETIC_MATCH").length
    };
    return {
      schemaVersion: 1, milestone: "P2-060g",
      kind: "STOCK_SNAPSHOT_RECONCILIATION",
      asOfDate, classification: "USER_SUPPLIED_UNVERIFIED",
      method: "Previous stock + received + customer returns + signed adjustments - sold = expected stock",
      coverage: "Movement days strictly after previous observation through current observation",
      sourceIntegrity: "UNAUTHENTICATED_USER_IMPORTS",
      counts, rows,
      safeguards: {
        published: false, aiModelUsed: false, sourceRecordsVerified: false,
        businessRevenueVerified: false, marketingAttributionVerified: false,
        arithmeticCheckedOnly: true, reportDigitallySigned: false
      }
    };
  }
  function canonicalJson(result) {
    if (!result || result.kind !== "STOCK_SNAPSHOT_RECONCILIATION")
      fail("Expected a reconciliation report");
    return JSON.stringify(result, null, 2) + "\n";
  }
  return Object.freeze({
    MOVEMENT_HEADER, MAX_INTERVAL_DAYS, CURRENT_MAX_AGE_DAYS,
    ReconciliationError, parseSnapshot, parseMovementLedger, reconcile, canonicalJson
  });
});
