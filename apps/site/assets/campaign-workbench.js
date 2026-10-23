/* P2-060 | Local campaign orchestration. No network, AI calls or persistence.
   Import -> assess -> draft -> PNG/storyboard -> internal approval -> self-reported measurement. */
(() => {
  "use strict";
  const engine = globalThis.MetaCampaign;
  if (!engine) return;
  const el = id => document.getElementById(id);
  const announce = (message, isError = false) => {
    el("campaign-status").textContent = message;
    el("campaign-status").classList.toggle("is-error", isError);
  };
  const audit = [];
  let records = null, results = null, selected = null, plan = null, approval = null, metrics = null, graphicReady = false;
  function recordEvent(action) { audit.push({ action, at: new Date().toISOString() }); if (audit.length > 200) audit.shift(); }
  function resetDownstream() {
    selected = null; plan = null; approval = null; metrics = null; graphicReady = false;
    el("campaign-project").hidden = true;
    el("campaign-media").hidden = true;
    el("campaign-approval").hidden = true;
    el("campaign-measure").hidden = true;
    el("campaign-evidence").disabled = true;
    el("campaign-copy").disabled = true;
    el("campaign-authorize").disabled = true;
    el("campaign-approval-state").textContent = "Not reviewed. No provider publishing is available.";
    el("campaign-metrics-result").textContent = "No results recorded.";
    el("campaign-post").value = "";
    const canvas = el("campaign-canvas");
    canvas.width = 1; canvas.height = 1;
  }
  const text = (parent, tag, value, className) => {
    const n = document.createElement(tag);
    if (className) n.className = className;
    n.textContent = value;
    parent.appendChild(n);
    return n;
  };
  function listItems(analysis) {
    const list = el("campaign-opportunities");
    list.replaceChildren();
    if (!analysis.opportunities.length) {
      text(list, "li", "No promotion candidates match the conservative rule. Review stock and sales rather than manufacturing a campaign.");
      return;
    }
    analysis.opportunities.forEach((item, index) => {
      const li = document.createElement("li");
      const label = text(li, "label", "", "campaign-product-option");
      const radio = document.createElement("input");
      radio.type = "radio"; radio.name = "candidate"; radio.value = item.sku;
      radio.checked = index === 0; label.prepend(radio);
      const detail = document.createElement("span");
      text(detail, "strong", item.name);
      text(detail, "small", item.sku + " · " + item.stock + " in stock · " +
        item.weeklySales + " sold/week · " + item.signal.title + " · " +
        engine.currency(item.priceKobo));
      label.appendChild(detail); list.appendChild(li);
    });
    selected = analysis.opportunities[0];
  }
  function selectedSku() {
    const checked = document.querySelector('input[name="candidate"]:checked');
    return checked ? checked.value : null;
  }
  function formatError(error) {
    announce(error instanceof Error ? error.message : "Something went wrong. Try again.", true);
  }
  el("campaign-import").addEventListener("submit", async event => {
    event.preventDefault();
    const file = el("campaign-file").files?.[0];
    resetDownstream();
    records = results = null;
    el("campaign-results").hidden = true;
    if (!file || file.size < 10 || file.size > engine.MAX_BYTES) {
      announce("Choose a CSV file between 10 bytes and 128 KB.", true); return;
    }
    try {
      const content = await file.text();
      records = engine.parseCSV(content);
      results = engine.analyze(records);
      el("campaign-count").textContent = String(results.totalItems);
      el("campaign-flagged").textContent = String(results.flaggedCount);
      el("campaign-analysis-note").textContent = results.note;
      listItems(results);
      el("campaign-results").hidden = false;
      el("campaign-create").disabled = !results.opportunities.length;
      recordEvent("Inventory CSV imported: " + records.length + " items");
      announce("Inventory assessed locally. No data uploaded. Review the recommended inventory before drafting.");
    } catch (error) { formatError(error); }
  });
  ["campaign-brand", "campaign-channel"].forEach(id => el(id).addEventListener("change", () => {
    if (plan) { resetDownstream(); announce("Campaign settings changed. Generate a new draft before reviewing."); }
  }));
  el("campaign-opportunities").addEventListener("change", () => {
    const sku = selectedSku();
    selected = results?.opportunities.find(item => item.sku === sku) || null;
    plan = approval = metrics = null; graphicReady = false;
    el("campaign-project").hidden = true;
    el("campaign-media").hidden = true;
    el("campaign-approval").hidden = true;
    el("campaign-measure").hidden = true;
    el("campaign-evidence").disabled = true;
    el("campaign-copy").disabled = true;
    el("campaign-approval-state").textContent = "Not reviewed. No provider publishing is available.";
  });
  el("campaign-create").addEventListener("click", () => {
    try {
      selected = results?.opportunities.find(item => item.sku === selectedSku()) || null;
      plan = engine.makeCampaign(selected, el("campaign-brand").value, el("campaign-channel").value);
      approval = metrics = null; graphicReady = false;
      el("campaign-metrics-result").textContent = "No results recorded.";
      el("campaign-post").value = plan.post;
      el("campaign-reason").textContent = plan.reason + ". " + plan.recommendation;
      el("campaign-video-brief").value = plan.videoBrief;
      el("campaign-project").hidden = false;
      el("campaign-media").hidden = false;
      el("campaign-approval").hidden = false;
      el("campaign-measure").hidden = false;
      el("campaign-evidence").disabled = true;
      el("campaign-copy").disabled = true;
      el("campaign-confirm").checked = false;
      el("campaign-authorize").disabled = false;
      el("campaign-approval-state").textContent = "Not reviewed. No provider publishing is available.";
      recordEvent("Campaign draft prepared for " + plan.sku);
      drawGraphic();
      announce("Campaign draft and graphic prepared. Review before recording internal approval.");
    } catch (error) { formatError(error); }
  });
  function revokeApproval() {
    if (!plan) return;
    approval = metrics = null;
    el("campaign-evidence").disabled = true;
    el("campaign-copy").disabled = true;
    el("campaign-confirm").checked = false;
    el("campaign-approval-state").textContent = "Content changed; internal approval must be recorded again.";
    el("campaign-metrics-result").textContent = "No results recorded.";
    recordEvent("Draft edited — previous internal approval revoked");
  }
  el("campaign-post").addEventListener("input", revokeApproval);
  el("campaign-video-brief").addEventListener("input", revokeApproval);
  function wrapWords(ctx, value, maxWidth, maxLines) {
    const words = value.split(/\s+/).filter(Boolean), lines = []; let current = "";
    for (const word of words) {
      const next = current ? current + " " + word : word;
      if (ctx.measureText(next).width > maxWidth && current) {
        lines.push(current); current = word;
      } else current = next;
    }
    if (current) lines.push(current);
    return lines.slice(0, maxLines).map(v => v.slice(0, 90));
  }
  function drawGraphic() {
    if (!plan) return;
    const canvas = el("campaign-canvas"), ctx = canvas.getContext("2d");
    if (!ctx) { graphicReady = false; announce("Canvas unsupported in this browser.", true); return; }
    canvas.width = 1080; canvas.height = 1080;
    ctx.fillStyle = "#040D20"; ctx.fillRect(0, 0, 1080, 1080);
    ctx.fillStyle = "#00A7ED"; ctx.fillRect(90, 86, 650, 10);
    ctx.fillStyle = "#DCE6F1"; ctx.fillRect(740, 86, 175, 10);
    ctx.fillStyle = "#EFB94F"; ctx.fillRect(915, 86, 75, 10);
    ctx.fillStyle = "#0b2549"; ctx.fillRect(90, 180, 900, 735);
    ctx.fillStyle = "#EFB94F"; ctx.beginPath(); ctx.arc(840, 315, 105, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#00A7ED"; ctx.fillRect(116, 230, 440, 4);
    ctx.fillStyle = "#DCE6F1"; ctx.font = "bold 39px Arial, sans-serif";
    ctx.fillText(plan.brand.slice(0, 40), 118, 293, 650);
    ctx.font = "bold 68px Arial, sans-serif";
    wrapWords(ctx, plan.product, 740, 4).forEach((line, i) => ctx.fillText(line, 118, 427 + i * 86, 740));
    ctx.fillStyle = "#00A7ED"; ctx.font = "bold 48px Arial, sans-serif";
    ctx.fillText(engine.currency(plan.priceKobo), 118, 790, 740);
    ctx.fillStyle = "#DCE6F1"; ctx.font = "28px Arial, sans-serif";
    ctx.fillText("Ask us for current availability and terms", 118, 858, 750);
    ctx.fillStyle = "#DCE6F1"; ctx.font = "25px Arial, sans-serif";
    ctx.fillText("ORIGINAL GRAPHIC  ·  PRICE SUBJECT TO CONFIRMATION", 100, 982, 890);
    graphicReady = true;
    recordEvent("Original PNG artwork rendered locally");
  }
  function download(name, mime, content) {
    const blob = content instanceof Blob ? content : new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    // Allow the browser time to consume the URL.
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  el("campaign-png").addEventListener("click", () => {
    if (!plan || !graphicReady) return;
    el("campaign-canvas").toBlob(blob => {
      if (blob) { download("metaautomate-campaign-" + plan.sku + ".png", "image/png", blob);
        recordEvent("Promotional PNG downloaded on explicit request"); }
      else announce("PNG export failed in this browser.", true);
    }, "image/png");
  });
  el("campaign-video-download").addEventListener("click", () => {
    if (!plan) return;
    const brief = el("campaign-video-brief").value.trim();
    if (!brief) { announce("Video brief cannot be empty.", true); return; }
    download("metaautomate-video-brief-" + plan.sku + ".txt", "text/plain;charset=utf-8", brief);
    recordEvent("Video production brief downloaded (no video rendered here)");
  });
  el("campaign-authorize").addEventListener("click", () => {
    if (!plan) return;
    if (!el("campaign-confirm").checked) {
      announce("Confirm review of pricing, rights, channel and claims before recording approval.", true); return;
    }
    const edited = el("campaign-post").value.trim();
    if (!edited || edited.length > 2200 || /[\u0000-\u0008\u000b\u000e-\u001f]/.test(edited)) {
      announce("Write a valid social draft under 2,200 characters.", true); return;
    }
    const brief = el("campaign-video-brief").value.trim();
    if (!brief || brief.length > 4000) {
      announce("Video brief must not be empty or exceed 4,000 characters.", true); return;
    }
    approval = { state: "INTERNAL_DRAFT_REVIEW_RECORDED", scope: "COPY_OR_DOWNLOAD_ONLY",
      channel: plan.channel, at: new Date().toISOString(),
      note: "No API publishing credentials or connected provider authorization used" };
    metrics = null;
    el("campaign-copy").disabled = false;
    el("campaign-evidence").disabled = false;
    el("campaign-approval-state").textContent = "Internal draft review recorded. Publishing still unavailable.";
    recordEvent("Internal content review recorded for " + plan.channel + " draft");
    announce("Internal draft review recorded. Copying is enabled; no external post has been published.");
  });
  el("campaign-copy").addEventListener("click", async () => {
    if (!approval || !plan) return;
    try {
      await navigator.clipboard.writeText(el("campaign-post").value);
      recordEvent("Approved-for-copy draft copied by user");
      announce("Draft copied. Publishing, if any, is the user's separate authorized action.");
    } catch (error) { announce("Clipboard unavailable. Select and copy the text manually.", true); }
  });
  el("campaign-metric-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!approval) { announce("Record internal draft review before adding metrics.", true); return; }
    try {
      metrics = engine.summarizeMetrics({
        impressions: el("campaign-impressions").value,
        clicks: el("campaign-clicks").value,
        orders: el("campaign-orders").value,
        sourceNote: el("campaign-metric-source").value
      });
      el("campaign-metrics-result").textContent = [
        "Self-reported: " + metrics.impressions.toLocaleString() + " impressions, " +
          metrics.clicks.toLocaleString() + " clicks, " + metrics.orders.toLocaleString() + " orders.",
        "Click rate: " + (metrics.clickThroughRatePct === null ? "n/a" : metrics.clickThroughRatePct + "%") +
          " · Click-to-order ratio: " + (metrics.clickToOrderPct === null ? "n/a" : metrics.clickToOrderPct + "%"),
        metrics.attribution
      ].join(" ");
      recordEvent("Self-reported campaign metrics evaluated");
      announce("Counts evaluated locally. No provider data was retrieved or verified.");
    } catch (error) { formatError(error); }
  });
  el("campaign-evidence").addEventListener("click", () => {
    if (!approval || !plan) return;
    const report = {
      schemaVersion: 1, milestone: "P2-060", environment: "BROWSER_LOCAL",
      classification: "USER_SUPPLIED_UNVERIFIED",
      record: { sku: plan.sku, product: plan.product, brand: plan.brand, channel: plan.channel,
        reason: plan.reason, priceKobo: plan.priceKobo },
      drafts: { social: el("campaign-post").value, video: el("campaign-video-brief").value,
        originalGraphicGenerated: graphicReady },
      approval, metrics, events: audit.slice(),
      safeguards: { publishPerformed: false, externalRequests: false, aiModelUsed: false,
        financialPerformanceVerified: false, providerMetricsVerified: false }
    };
    download("metaautomate-campaign-evidence-" + plan.sku + ".json",
      "application/json", JSON.stringify(report, null, 2) + "\n");
    recordEvent("Campaign evidence JSON downloaded");
    announce("Campaign evidence downloaded. No file has been uploaded or submitted.");
  });
  el("campaign-sample").addEventListener("click", () => {
    const csv = [
      engine.HEADER.join(","),
      "FAB-101,Classic Kaftan,24,3,3500000",
      "CAP-220,Embroidered Cap,18,0,850000",
      "SHO-100,Casual Shoes,2,5,1400000"
    ].join("\n") + "\n";
    download("metaautomate-sample-inventory.csv", "text/csv;charset=utf-8", csv);
    announce("Sample CSV downloaded. Example data is fictional, not a customer record.");
  });
})();
