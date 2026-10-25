/* P2-060 | Local inventory-to-campaign decision engine.
   Pure functions: no DOM, network, persistence, provider calls or model inference.
   Exposed as MetaCampaign in browser and CommonJS for offline tests. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.MetaCampaign = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const HEADER = ["sku", "name", "stock", "weekly_sales", "unit_price_kobo"];
  // Two additional self-declarations are optional; they do not authenticate
  // provenance. Older five-column CSVs remain supported but are flagged.
  const QUALITY_HEADER = [...HEADER, "stock_count_status", "sales_coverage_status"];
  // Dated data is an optional stricter self-declaration, not provider proof.
  const DATED_HEADER = [...QUALITY_HEADER, "stock_observed_on", "sales_period_start", "sales_period_end"];
  const MAX_AGE_DAYS = 7;
  const STOCK_STATES = ["counted", "unknown"];
  const SALES_STATES = ["complete", "partial", "unknown"];
  const MAX_BYTES = 128000, MAX_ROWS = 400;
  const CHANNELS = ["Instagram", "Facebook", "TikTok", "WhatsApp", "Other"];
  class CampaignError extends Error { constructor(message) { super(message); this.name = "CampaignError"; } }
  const fail = text => { throw new CampaignError(text); };
  const safeText = (value, max, label) => {
    if (typeof value !== "string") fail(label + " must be text");
    const v = value.trim();
    if (!v || v.length > max || /[\u0000-\u001f\u007f<>]/.test(v) ||
        /^[\s]*[=+\-@]/.test(v)) fail("Unsafe or invalid " + label);
    return v;
  };
  const whole = (value, label, max) => {
    if (!/^(0|[1-9][0-9]*)$/.test(value)) fail(label + " must be a nonnegative integer");
    const n = Number(value);
    if (!Number.isSafeInteger(n) || n > max) fail(label + " is outside allowed range");
    return n;
  };
  function utcDay() { return new Date().toISOString().slice(0, 10); }
  function calendarDay(value, label) {
    if (typeof value !== "string" || !/^20[0-9]{2}-[0-9]{2}-[0-9]{2}$/.test(value))
      fail(label + " must be a valid YYYY-MM-DD date between 2000 and 2099");
    const time = Date.parse(value + "T00:00:00Z");
    if (!Number.isFinite(time) || new Date(time).toISOString().slice(0, 10) !== value)
      fail(label + " is not a real calendar date");
    return time;
  }
  function assessAsOf(value) {
    const day = value === undefined ? utcDay() : value;
    calendarDay(day, "Assessment as-of date");
    return day;
  }
  function parseCSV(text) {
    if (typeof text !== "string" || !text.length || new TextEncoder().encode(text).length > MAX_BYTES)
      fail("Choose a nonempty CSV smaller than 128 KB");
    text = text.replace(/^\uFEFF/, "");
    const rows = [];
    let row = [], cell = "", inQuote = false, justClosed = false;
    function pushCell() {
      if (cell.length > 200) fail("CSV cell exceeds 200 characters");
      row.push(cell); cell = ""; justClosed = false;
      if (row.length > DATED_HEADER.length) fail("Unexpected CSV columns");
    }
    function pushRow() {
      pushCell();
      if (!(row.length === 1 && row[0] === "")) rows.push(row);
      row = [];
      if (rows.length > MAX_ROWS + 1) fail("CSV has too many records (maximum 400)");
    }
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (inQuote) {
        if (c === '"') {
          if (text[i + 1] === '"') { cell += '"'; i++; } else { inQuote = false; justClosed = true; }
        } else cell += c;
      } else if (c === ",") { pushCell(); }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        pushRow();
      } else if (c === '"' && cell === "" && !justClosed) { inQuote = true; }
      else if (c === '"' || justClosed) fail("Malformed CSV quoting");
      else cell += c;
      if (cell.length > 200) fail("CSV cell exceeds 200 characters");
    }
    if (inQuote) fail("Unclosed CSV quote");
    if (cell.length || row.length || justClosed) pushRow();
    const columns = rows.length ? rows[0].map(v => v.trim()) : [];
    const matches = header => columns.length === header.length &&
      columns.every((column, i) => column === header[i]);
    const dated = matches(DATED_HEADER);
    const enhanced = matches(QUALITY_HEADER) || dated;
    if (!matches(HEADER) && !enhanced) {
      fail("Required columns: " + HEADER.join(", ") +
        " (or append stock_count_status,sales_coverage_status, then optionally " +
        "stock_observed_on,sales_period_start,sales_period_end)");
    }
    if (rows.length <= 1) fail("Include at least one inventory row");
    const found = new Set();
    return rows.slice(1).map((cells, i) => {
      if (cells.length !== (dated ? DATED_HEADER.length :
          enhanced ? QUALITY_HEADER.length : HEADER.length))
        fail("Row " + (i + 2) + " has the wrong number of columns");
      const sku = safeText(cells[0], 36, "SKU at row " + (i + 2));
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{1,35}$/.test(sku)) fail("Invalid SKU at row " + (i + 2));
      if (found.has(sku.toLowerCase())) fail("Duplicate SKU: " + sku);
      found.add(sku.toLowerCase());
      const name = safeText(cells[1], 90, "product name at row " + (i + 2));
      const stock = whole(cells[2].trim(), "Stock", 1000000);
      const weeklySales = whole(cells[3].trim(), "Weekly sales", 1000000);
      const priceKobo = whole(cells[4].trim(), "Unit price (kobo)", 100000000000);
      if (priceKobo === 0) fail("Unit price must be greater than zero");
      if (!enhanced) return { sku, name, stock, weeklySales, priceKobo };
      const stockCountStatus = cells[5].trim();
      const salesCoverageStatus = cells[6].trim();
      if (!STOCK_STATES.includes(stockCountStatus) || !SALES_STATES.includes(salesCoverageStatus))
        fail("Row " + (i + 2) + " requires stock_count_status=counted|unknown " +
          "and sales_coverage_status=complete|partial|unknown");
      const record = { sku, name, stock, weeklySales, priceKobo,
        stockCountStatus, salesCoverageStatus };
      if (dated) {
        record.stockObservedOn = cells[7].trim();
        record.salesPeriodStart = cells[8].trim();
        record.salesPeriodEnd = cells[9].trim();
        // Reject invalid or impossible dates even for rows currently held.
        calendarDay(record.stockObservedOn, "stock_observed_on at row " + (i + 2));
        calendarDay(record.salesPeriodStart, "sales_period_start at row " + (i + 2));
        calendarDay(record.salesPeriodEnd, "sales_period_end at row " + (i + 2));
      }
      return record;
    });
  }
  function classify(item) {
    if (item.stock === 0) return { code: "out", title: "Out of stock", actionable: false, rank: 9 };
    if (item.weeklySales === 0 && item.stock >= 5)
      return { code: "no-sales", title: "No recorded weekly sales", actionable: true, rank: 1 };
    if (item.weeklySales > 0 && item.stock >= Math.max(10, item.weeklySales * 4))
      return { code: "high-cover", title: "At least four weeks of cover", actionable: true, rank: 2 };
    if (item.weeklySales > 0 && item.stock < item.weeklySales)
      return { code: "low-stock", title: "Low stock — do not promote", actionable: false, rank: 8 };
    return { code: "normal", title: "No promotion signal", actionable: false, rank: 7 };
  }
  function assess(item, asOfDate = utcDay()) {
    const asOfTime = calendarDay(asOfDate, "Assessment as-of date");
    const quality = { basis: "USER_SUPPLIED_UNVERIFIED", mode: "LEGACY_UNATTESTED",
      status: "REVIEW_INPUTS", issues: [], heldForReview: false, asOfDate,
      inventoryAgeDays: null, salesEndAgeDays: null };
    const extended = Object.hasOwn(item, "stockCountStatus") &&
      Object.hasOwn(item, "salesCoverageStatus");
    if (extended) {
      const dated = ["stockObservedOn", "salesPeriodStart", "salesPeriodEnd"]
        .every(key => Object.hasOwn(item, key));
      quality.mode = dated ? "DATED_SELF_DECLARED" : "SELF_DECLARED";
      if (item.stockCountStatus !== "counted")
        quality.issues.push("Stock quantity not self-declared as counted");
      if (item.salesCoverageStatus !== "complete")
        quality.issues.push("Weekly-sales coverage is partial or unknown");
      if (dated) {
        const stockTime = calendarDay(item.stockObservedOn, "stock_observed_on");
        const startTime = calendarDay(item.salesPeriodStart, "sales_period_start");
        const endTime = calendarDay(item.salesPeriodEnd, "sales_period_end");
        const dayMs = 86400000;
        quality.inventoryAgeDays = Math.round((asOfTime - stockTime) / dayMs);
        quality.salesEndAgeDays = Math.round((asOfTime - endTime) / dayMs);
        if (quality.inventoryAgeDays < 0)
          quality.issues.push("Stock observation occurs after the assessment date");
        else if (quality.inventoryAgeDays > MAX_AGE_DAYS)
          quality.issues.push("Stock observation is older than seven calendar days");
        if ((endTime - startTime) / dayMs !== 6)
          quality.issues.push("Weekly sales require an inclusive seven-calendar-day period");
        if (quality.salesEndAgeDays < 0)
          quality.issues.push("Sales period ends after the assessment date");
        else if (quality.salesEndAgeDays > MAX_AGE_DAYS)
          quality.issues.push("Sales period ended more than seven calendar days ago");
      } else {
        quality.issues.push("No stock observation date or sales period supplied");
      }
      // Seven-column files remain compatible and usable, but not dated.
      quality.heldForReview = quality.issues.length > 0;
      if (!dated) quality.heldForReview =
        item.stockCountStatus !== "counted" || item.salesCoverageStatus !== "complete";
      quality.status = quality.heldForReview ? "REVIEW_INPUTS" :
        dated ? "DATED_SELF_DECLARED_CURRENT" : "SELF_DECLARED_COMPLETE";
    } else {
      quality.issues.push("Legacy CSV: stock count and weekly-sales completeness not declared");
    }
    const candidate = classify(item);
    const signal = quality.heldForReview && candidate.actionable
      ? { code: "quality-hold", title: "Hold: verify stock and sales records",
          actionable: false, rank: 6 }
      : candidate;
    return { quality, signal, underlyingSignal: candidate.code };
  }
  function analyze(records, referenceDate) {
    if (!Array.isArray(records) || !records.length || records.length > MAX_ROWS) fail("Invalid inventory");
    const asOfDate = assessAsOf(referenceDate);
    const evaluated = records.map(item => ({ ...item, ...assess(item, asOfDate) }));
    const opportunities = evaluated.filter(item => item.signal.actionable).sort((a, b) =>
      a.signal.rank - b.signal.rank || b.stock - a.stock || a.sku.localeCompare(b.sku));
    const held = evaluated.filter(item => item.quality.heldForReview &&
      item.underlyingSignal !== "normal" && item.underlyingSignal !== "out" &&
      item.underlyingSignal !== "low-stock");
    const legacy = evaluated.filter(item => item.quality.mode === "LEGACY_UNATTESTED").length;
    const dated = evaluated.filter(item => item.quality.mode === "DATED_SELF_DECLARED").length;
    const undated = evaluated.length - dated;
    return { evaluated, opportunities, held, totalItems: records.length,
      flaggedCount: opportunities.length, heldCount: held.length, legacyCount: legacy,
      datedCount: dated, undatedCount: undated, asOfDate,
      missingSalesData: true,
      note: "Assessment uses UTC date " + asOfDate + ". Signals use only user-supplied, " +
        "unverified stock and sales values. Dated records must describe a complete " +
        "seven-day period and current observations; undated files lack temporal proof. " +
        "No profit, demand or campaign impact predicted." };
  }
  const currency = kobo => "₦" + (kobo / 100).toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  function makeCampaign(item, brand, channel) {
    if (!item || !assess(item).signal.actionable)
      fail("Choose an eligible in-stock product with sufficient user-supplied data");
    brand = safeText(brand, 70, "business name");
    if (!CHANNELS.includes(channel)) fail("Choose a supported draft channel");
    const description = item.weeklySales === 0 ? "Review visibility and customer interest before discounting."
      : "Review demand, positioning and availability before promoting.";
    const post = [
      item.name + " from " + brand + ".",
      "Listed price: " + currency(item.priceKobo) + " (please confirm before ordering).",
      "Message us to check availability, delivery options and the final price.",
      "Draft only — verify every claim before publishing."
    ].join("\n\n");
    const videoBrief = [
      "30–60 SECOND PROMOTIONAL VIDEO BRIEF — DRAFT",
      "Brand: " + brand, "Product: " + item.name,
      "0–10 sec: Show original product visuals or a licensed graphic; introduce the item.",
      "10–30 sec: Explain factual product attributes supplied and verified by the business.",
      "30–45 sec: Display the listed price " + currency(item.priceKobo) + " with a verification reminder.",
      "45–60 sec: Invite customers to ask about availability and delivery.",
      "Use only authorized visuals and voice recordings. A human must review the final output.",
      "Record narration (30–120 seconds) and assemble a WebM using MetaAutomate Creative Studio.",
      "No model-generated video or external publication occurs here."
    ].join("\n");
    const quality = assess(item).quality;
    const caution = quality.mode === "LEGACY_UNATTESTED"
      ? " Legacy CSV does not confirm stock counts or sales-data completeness."
      : quality.mode === "DATED_SELF_DECLARED"
        ? " Dates, completeness and counts are self-declared; no external verification."
        : " Statuses are self-declared, undated and have not been independently verified.";
    return { sku: item.sku, product: item.name, brand, channel, priceKobo: item.priceKobo,
      reason: classify(item).title, recommendation: description + caution,
      inputQuality: { mode: quality.mode, status: quality.status, issues: quality.issues.slice(),
        basis: quality.basis, asOfDate: quality.asOfDate,
        stockObservedOn: item.stockObservedOn ?? null,
        salesPeriodStart: item.salesPeriodStart ?? null,
        salesPeriodEnd: item.salesPeriodEnd ?? null }, post, videoBrief };
  }
  function summarizeMetrics(data) {
    if (!data || typeof data !== "object") fail("Metrics missing");
    const impressions = whole(String(data.impressions), "Impressions", 1000000000);
    const clicks = whole(String(data.clicks), "Clicks", 1000000000);
    const orders = whole(String(data.orders), "Orders", 1000000000);
    const note = safeText(data.sourceNote, 160, "measurement source");
    if (clicks > impressions || orders > clicks)
      fail("For this same-funnel sample, orders cannot exceed clicks or clicks exceed impressions");
    return { impressions, clicks, orders, sourceNote: note,
      clickThroughRatePct: impressions ? Math.round((clicks / impressions) * 10000) / 100 : null,
      clickToOrderPct: clicks ? Math.round((orders / clicks) * 10000) / 100 : null,
      evidence: "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
      attribution: "Unverified; these counts do not establish revenue, profit or campaign causation" };
  }
  return Object.freeze({ HEADER, QUALITY_HEADER, DATED_HEADER, STOCK_STATES, SALES_STATES,
    MAX_AGE_DAYS, CHANNELS, MAX_BYTES, MAX_ROWS, CampaignError, parseCSV, analyze,
    makeCampaign, summarizeMetrics, currency });
});
