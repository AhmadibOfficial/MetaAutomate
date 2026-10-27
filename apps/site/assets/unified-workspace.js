/* MetaAutomate Unified Workspace | P2-062
   Use the existing P2-060 inventory engine. No network, persistent storage,
   authentication shortcuts, external publishing or automatic AI operations. */
(() => {
  "use strict";
  const engine = globalThis.MetaCampaign;
  const $ = id => document.getElementById(id);
  const screens = ["overview", "inventory", "campaign", "evidence", "modules", "readiness"];
  const titles = { overview: "Home", inventory: "My inventory", campaign: "Create a post", evidence: "My reports", modules: "Other tools", readiness: "Project status" };
  const LIMIT = 40;
  let records = null, analysis = null, plan = null, approved = false, activity = [], messageTimer = null;
  let importGeneration = 0; // Invalidate an in-flight file read when input/session changes.
  let exampleMode = false; // Never present synthetic sample data as owner-supplied business records.
  if (!engine || !["parseCSV", "analyze", "makeCampaign"].every(key => typeof engine[key] === "function")) {
    $("live-status").textContent = "Inventory engine unavailable. No actions can run.";
    $("live-status").classList.add("visible");
    return;
  }
  const announce = text => {
    const box = $("live-status");
    box.textContent = text;
    box.classList.add("visible");
    if (messageTimer !== null) clearTimeout(messageTimer);
    messageTimer = setTimeout(() => box.classList.remove("visible"), 4700);
  };
  const track = code => {
    activity.push({ code, localClock: new Date().toISOString() });
    if (activity.length > LIMIT) activity.shift();
    renderEvidence();
  };
  const saveBlob = (filename, content, mime) => {
    const url = URL.createObjectURL(new Blob([content], { type: mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const makeJSON = (kind, payload) => JSON.stringify({
    schema: "metaautomate.local.v1",
    kind,
    generatedAtClientClock: new Date().toISOString(),
    source: exampleMode ? "SYNTHETIC_EXAMPLE_UNVERIFIED" : "USER_DECLARED_UNVERIFIED",
    independentlyVerified: false,
    customerTractionVerified: false,
    revenueVerified: false,
    externalPublishingPerformed: false,
    aiModelUsed: false,
    serverDataUploaded: false,
    signed: false,
    payload
  }, null, 2) + "\n";
  function navigate() {
    const requested = location.hash.slice(1);
    const current = screens.includes(requested) ? requested : "overview";
    for (const key of screens) $("view-" + key).hidden = current !== key;
    for (const link of document.querySelectorAll('.rail-nav [data-route]')) {
      if (link.dataset.route === current) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    $("current-section").textContent = titles[current];
    document.title = titles[current] + " — MetaAutomate OS";
    closeMenu();
  }
  function closeMenu() {
    $("sidebar").classList.remove("open");
    $("menu-toggle").setAttribute("aria-expanded", "false");
  }
  $("menu-toggle").addEventListener("click", () => {
    const open = $("sidebar").classList.toggle("open");
    $("menu-toggle").setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape") closeMenu();
  });
  for (const a of document.querySelectorAll('a[data-route]')) {
    a.addEventListener("click", () => {
      if (location.hash === a.getAttribute("href")) navigate();
    });
  }
  window.addEventListener("hashchange", navigate);
  navigate();

  function resetPlan() {
    plan = null;
    approved = false;
    $("draft-output").hidden = true;
    $("review-check").checked = false;
    $("copy-draft").disabled = true;
    $("save-draft").disabled = true;
    $("draft-status").textContent = "NOT REVIEWED";
    $("overview-review").textContent = "Not started";
    $("draft-text").value = "";
  }
  function clearInventory(trackClear = true) {
    importGeneration++;
    exampleMode = false;
    records = null;
    analysis = null;
    resetPlan();
    $("overview-count").textContent = "—";
    $("overview-opportunities").textContent = "—";
    $("inventory-results").hidden = true;
    $("draft-form").hidden = true;
    $("campaign-empty").hidden = false;
    $("inventory-file").value = "";
    $("file-label").textContent = "No file selected";
    $("candidate-select").replaceChildren();
    activity = [];
    if (trackClear) track("LOCAL_SESSION_CLEARED");
    else renderEvidence();
  }
  $("clear-inventory").addEventListener("click", () => {
    clearInventory();
    announce("Local workspace session cleared. No server data exists.");
  });
  $("inventory-file").addEventListener("change", () => {
    importGeneration++;
    exampleMode = false;
    const file = $("inventory-file").files?.[0];
    // A newly chosen file must never leave a previous approval or analysis active.
    records = null;
    analysis = null;
    resetPlan();
    activity = [];
    $("inventory-results").hidden = true;
    $("draft-form").hidden = true;
    $("campaign-empty").hidden = false;
    $("overview-count").textContent = "—";
    $("overview-opportunities").textContent = "—";
    $("candidate-select").replaceChildren();
    $("file-label").textContent = file ? "Selected: " + file.name.slice(0, 75) : "No file selected";
    renderEvidence();
  });
  $("try-example").addEventListener("click", () => {
    importGeneration++; // Invalidate a previously started file read.
    const fictionalCSV = [
      "sku,name,stock,weekly_sales,unit_price_kobo",
      "EX-01,Example Cap,18,0,850000",
      "EX-02,Example Kaftan,24,3,3500000",
      "EX-03,Example Shoe,0,5,1200000"
    ].join("\n") + "\n";
    // Same production decision engine, but explicitly labelled fictional throughout.
    try {
      const parsed = engine.parseCSV(fictionalCSV);
      const reviewed = engine.analyze(parsed);
      $("inventory-file").value = "";
      $("file-label").textContent = "Example products (not a real import)";
      records = parsed;
      analysis = reviewed;
      exampleMode = true;
      activity = [];
      resetPlan();
      renderInventory();
      track("SYNTHETIC_EXAMPLE_ANALYZED");
      location.hash = "#inventory";
      navigate();
      announce("Example loaded: 3 fictional products. Your own data has not been uploaded.");
    } catch (error) {
      clearInventory(false);
      announce(error instanceof Error ? "Example unavailable: " + error.message : "Example unavailable.");
    }
  });
  $("download-sample").addEventListener("click", () => {
    saveBlob("metaautomate-sample-inventory.csv",
      "sku,name,stock,weekly_sales,unit_price_kobo\nCAP-01,Embroidered Cap,18,0,850000\nFAB-02,Classic Kaftan,24,3,3500000\nSHO-03,Canvas Shoe,0,5,1200000\n",
      "text/csv;charset=utf-8");
    announce("Fictional inventory example downloaded.");
  });
  $("inventory-form").addEventListener("submit", async event => {
    event.preventDefault();
    const file = $("inventory-file").files?.[0];
    const generation = ++importGeneration;
    if (!file || file.size === 0 || file.size > engine.MAX_BYTES) {
      announce("Choose a nonempty CSV no larger than 128 KB.");
      return;
    }
    // File.arrayBuffer + fatal UTF-8 decode avoids silent replacement bytes.
    try {
      const bytes = await file.arrayBuffer();
      if (!bytes.byteLength || bytes.byteLength > engine.MAX_BYTES) throw new Error("Invalid CSV size");
      const csv = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      const parsed = engine.parseCSV(csv);
      const reviewed = engine.analyze(parsed);
      if (generation !== importGeneration || $("inventory-file").files?.[0] !== file) return;
      // Commit state only after all parsing and analysis checks succeed.
      exampleMode = false;
      records = parsed;
      analysis = reviewed;
      activity = [];
      resetPlan();
      renderInventory();
      track("USER_DECLARED_INVENTORY_ANALYZED");
      announce("Inventory analyzed in this browser; no information uploaded.");
    } catch (error) {
      if (generation !== importGeneration || $("inventory-file").files?.[0] !== file) return;
      records = null;
      analysis = null;
      resetPlan();
      $("inventory-results").hidden = true;
      $("draft-form").hidden = true;
      $("campaign-empty").hidden = false;
      $("overview-count").textContent = "—";
      $("overview-opportunities").textContent = "—";
      activity = [];
      renderEvidence();
      announce(error instanceof Error ? "Import rejected: " + error.message : "Import rejected.");
    }
  });
  function cell(row, value, className) {
    const td = document.createElement("td");
    td.textContent = String(value);
    if (className) td.className = className;
    row.appendChild(td);
    return td;
  }
  function renderInventory() {
    if (!analysis) return;
    $("inventory-caveat").textContent = exampleMode
      ? "Example only: fictional products and prices. These are not your business records."
      : "Data origin is self-declared and not independently verified.";
    $("inventory-results").hidden = false;
    $("inventory-total").textContent = String(analysis.totalItems);
    $("inventory-stock").textContent = String(records.reduce((sum, item) => sum + item.stock, 0));
    $("inventory-candidates").textContent = String(analysis.flaggedCount);
    $("overview-count").textContent = String(analysis.totalItems);
    $("overview-opportunities").textContent = String(analysis.flaggedCount);
    const tbody = $("inventory-table");
    tbody.replaceChildren();
    for (const item of analysis.evaluated) {
      const tr = document.createElement("tr");
      cell(tr, item.name);
      cell(tr, item.sku);
      cell(tr, item.stock);
      cell(tr, item.weeklySales);
      const td = document.createElement("td");
      const status = document.createElement("span");
      status.className = "signal" + (item.signal.actionable ? " recommend" : "");
      status.textContent = item.signal.title;
      td.appendChild(status);
      tr.appendChild(td);
      tbody.appendChild(tr);
    }
    const select = $("candidate-select");
    select.replaceChildren();
    for (const item of analysis.opportunities) {
      const option = document.createElement("option");
      option.value = item.sku;
      option.textContent = item.name + " (" + item.sku + ") — " + engine.currency(item.priceKobo);
      select.appendChild(option);
    }
    $("draft-form").hidden = analysis.opportunities.length === 0;
    $("campaign-empty").hidden = analysis.opportunities.length > 0;
    if (!analysis.opportunities.length) $("campaign-empty").textContent = "No products qualify under the conservative stock rules. Do not invent a campaign.";
  }
  $("download-analysis").addEventListener("click", () => {
    if (!analysis) return;
    const payload = { importedItems: analysis.totalItems, flaggedItems: analysis.flaggedCount,
      ruleNote: analysis.note,
      exampleOnly: exampleMode,
      inventory: analysis.evaluated.map(item => ({
        sku: item.sku, name: item.name, stock: item.stock, weeklySales: item.weeklySales,
        unitPriceKobo: item.priceKobo, signal: item.signal.title, actionable: item.signal.actionable
      }))
    };
    saveBlob("metaautomate-local-inventory-assessment.json", makeJSON("INVENTORY_ASSESSMENT", payload), "application/json");
    track("LOCAL_INVENTORY_EXPORT");
    announce("Self-declared local inventory analysis downloaded.");
  });
  function revokeApproval() {
    if (!plan) return;
    const wasApproved = approved;
    approved = false;
    $("review-check").checked = false;
    $("copy-draft").disabled = true;
    $("save-draft").disabled = true;
    $("draft-status").textContent = "NOT REVIEWED";
    $("overview-review").textContent = "Not reviewed";
    if (wasApproved) {
      track("INTERNAL_DRAFT_REVIEW_REVOKED_BY_EDIT");
      announce("Draft changed: prior internal review revoked.");
    }
  }
  ["candidate-select", "channel-select", "brand-name"].forEach(id => {
    $(id).addEventListener(id === "brand-name" ? "input" : "change", () => {
      if (plan) {
        resetPlan();
        track("CAMPAIGN_INPUT_CHANGED");
        announce("Campaign inputs changed. Prepare a fresh draft before review.");
      }
    });
  });
  $("draft-form").addEventListener("submit", event => {
    event.preventDefault();
    if (!analysis) return;
    const chosen = analysis.opportunities.find(item => item.sku === $("candidate-select").value);
    try {
      const next = engine.makeCampaign(chosen, $("brand-name").value, $("channel-select").value);
      resetPlan();
      plan = next;
      $("draft-text").value = next.post;
      $("draft-reason").textContent = next.reason + ". " + next.recommendation;
      $("draft-output").hidden = false;
      $("overview-review").textContent = "Not reviewed";
      track("CAMPAIGN_DRAFT_PREPARED");
      announce("Editable campaign prepared. Internal review is required before copying.");
    } catch (error) {
      resetPlan();
      announce(error instanceof Error ? error.message : "Campaign could not be prepared.");
    }
  });
  $("draft-text").addEventListener("input", revokeApproval);
  $("record-review").addEventListener("click", () => {
    if (!plan) return;
    if (!$("review-check").checked || !$("draft-text").value.trim()) {
      announce("Review the nonempty draft and select the confirmation checkbox first.");
      return;
    }
    approved = true;
    $("copy-draft").disabled = false;
    $("save-draft").disabled = false;
    $("draft-status").textContent = "INTERNAL DRAFT REVIEW";
    $("overview-review").textContent = "Reviewed";
    track("INTERNAL_DRAFT_REVIEW_RECORDED");
    announce("Internal review recorded for copy/download only. No post was published.");
  });
  $("review-check").addEventListener("change", () => {
    if (!$("review-check").checked) revokeApproval();
  });
  $("copy-draft").addEventListener("click", async () => {
    if (!approved || !plan) return;
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText($("draft-text").value);
      track("REVIEWED_COPY_TO_CLIPBOARD");
      announce("Reviewed text copied locally; no post published.");
    } catch {
      announce("Clipboard unavailable. Use Download .txt instead.");
    }
  });
  $("save-draft").addEventListener("click", () => {
    if (!approved || !plan) return;
    saveBlob("metaautomate-reviewed-draft.txt", $("draft-text").value + "\n", "text/plain;charset=utf-8");
    track("REVIEWED_DRAFT_TEXT_DOWNLOADED");
    announce("Reviewed draft downloaded; no social provider connection.");
  });
  function renderEvidence() {
    const list = $("evidence-list");
    list.replaceChildren();
    if (!activity.length) {
      const empty = document.createElement("li");
      empty.textContent = "No local actions have been recorded. Import inventory to begin.";
      list.appendChild(empty);
    }
    for (const action of activity) {
      const li = document.createElement("li");
      li.textContent = action.code.replaceAll("_", " ") + " · " + action.localClock + " (untrusted client clock)";
      list.appendChild(li);
    }
    $("export-evidence").disabled = !analysis;
  }
  $("export-evidence").addEventListener("click", () => {
    if (!analysis) return;
    // Only counts and review state; avoid copying entire product/marketing data into receipts.
    const receipt = {
      importedProductCount: analysis.totalItems,
      exampleOnly: exampleMode,
      promotionCandidateCount: analysis.flaggedCount,
      selectedSku: plan?.sku || null,
      campaignDraftPrepared: !!plan,
      internalDraftReviewRecorded: approved,
      approvalScope: approved ? "COPY_OR_DOWNLOAD_ONLY" : "NONE",
      eventLog: activity.slice(),
      metricsStatus: "NOT_COLLECTED",
      published: false,
      deployed: false,
      realModelInference: false,
      thirdPartySourceAuthenticated: false
    };
    saveBlob("metaautomate-unverified-local-evidence.json", makeJSON("LOCAL_SESSION_EVIDENCE", receipt), "application/json");
    track("LOCAL_EVIDENCE_EXPORTED");
    announce("Unverified session evidence downloaded. This is not independent attestation.");
  });
  $("module-search").addEventListener("input", () => {
    const query = $("module-search").value.trim().toLowerCase();
    let shown = 0;
    for (const card of $("module-grid").querySelectorAll("[data-search]")) {
      const match = !query || (card.dataset.search + " " + card.textContent).toLowerCase().includes(query);
      card.hidden = !match;
      if (match) shown++;
    }
    $("module-no-results").hidden = shown !== 0;
  });
  renderEvidence();
})();