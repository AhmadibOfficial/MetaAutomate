/* P2-060g | Standalone, local-only snapshot reconciliation workbench.
   No reconciliation result is used for social approval, customer publishing,
   actual stock updates, financial assertions or independent provenance. */
(() => {
  "use strict";
  const engine = globalThis.MetaReconcile;
  const proof = globalThis.MetaImportProof;
  if (!engine || !proof) return;
  const el = id => document.getElementById(id);
  const control = el("reconcile-form");
  let report = null, reportManifest = null, generation = 0;
  el("reconcile-date").value = new Date().toISOString().slice(0, 10);
  const announce = (message, error = false) => {
    const n = el("reconcile-state");
    n.textContent = message;
    n.classList.toggle("is-error", error);
  };
  function invalidate() {
    generation++;
    el("reconcile-run").disabled = false;
    report = null;
    reportManifest = null;
    el("reconcile-export").disabled = true;
    el("reconcile-results").hidden = true;
    el("reconcile-items").replaceChildren();
    announce("Inputs changed. Re-run the private reconciliation; earlier results are invalidated.");
  }
  for (const id of ["reconcile-previous", "reconcile-current", "reconcile-ledger"]) {
    el(id).addEventListener("change", invalidate);
  }
  el("reconcile-date").addEventListener("input", invalidate);
  const text = (parent, tag, value, klass) => {
    const node = document.createElement(tag);
    if (klass) node.className = klass;
    node.textContent = value;
    parent.appendChild(node);
    return node;
  };
  function view(result) {
    const list = el("reconcile-items");
    list.replaceChildren();
    for (const row of result.rows) {
      const li = text(list, "li", "", "reconcile-decision");
      text(li, "strong", row.sku + " · " + row.product);
      text(li, "span", row.status.replace(/_/g, " "));
      const movement = row.movement;
      if (movement && row.expectedStock !== null) {
        text(li, "small",
          "Previous stock " + row.previousStock +
          " + received " + movement.receivedUnits +
          " + returns " + movement.returnedUnits +
          " + adjustment " + movement.adjustmentUnits +
          " − sold " + movement.soldUnits +
          " = " + row.expectedStock + " expected; " +
          row.currentStock + " declared current; difference " + row.differenceUnits + ".");
      }
      if (row.issues.length) text(li, "small", "Review: " + row.issues.join("; "));
      else text(li, "small", "The declared figures agree arithmetically; source records remain unverified.");
    }
    el("reconcile-summary").textContent =
      result.counts.totalSkus + " SKU(s) reviewed. " +
      result.counts.declaredArithmeticMatches + " matched declared arithmetic AND comparable sales count; " +
      result.counts.stockConflicts + " stock conflict(s); " +
      result.counts.salesConflicts + " comparable sales conflict(s); " +
      result.counts.reviewRequired + " record(s) still require review. " +
      "Assessment as-of " + result.asOfDate + " UTC. No independently verified business result.";
    el("reconcile-results").hidden = false;
    el("reconcile-export").disabled = false;
    el("reconcile-results-title").focus();
  }
  async function fileBytes(id) {
    const file = el(id).files?.[0];
    if (!file || file.size < 10 || file.size > proof.MAX_BYTES)
      throw new Error("Each reconciliation CSV must be between 10 bytes and 128 KB");
    return new Uint8Array(await file.arrayBuffer());
  }
  control.addEventListener("submit", async event => {
    event.preventDefault();
    const run = ++generation;
    report = null;
    reportManifest = null;
    el("reconcile-results").hidden = true;
    el("reconcile-export").disabled = true;
    el("reconcile-run").disabled = true;
    announce("Checking local records and declared movement arithmetic. No data uploaded.");
    try {
      const [previousBytes, currentBytes, movementBytes] = await Promise.all([
        fileBytes("reconcile-previous"), fileBytes("reconcile-current"),
        fileBytes("reconcile-ledger")
      ]);
      if (run !== generation) return;
      // Digest the exact imported bytes; parse the same strict UTF-8 bytes.
      // Hashes identify uploaded bytes, not who created the records.
      const { texts, inputManifest } = await proof.inspectInputs([
        { role: "previous_snapshot", bytes: previousBytes },
        { role: "current_snapshot", bytes: currentBytes },
        { role: "movement_ledger", bytes: movementBytes }
      ], globalThis.crypto?.subtle);
      if (run !== generation) return;
      const asOf = el("reconcile-date").value;
      const reconciled = engine.reconcile(
        texts.previous_snapshot, texts.current_snapshot, texts.movement_ledger, asOf);
      if (run !== generation) return;
      report = reconciled;
      reportManifest = inputManifest;
      view(reconciled);
      announce("Reconciliation computed from unverified inputs. Inspect every difference before relying on it.");
    } catch (error) {
      if (run === generation) announce(error instanceof Error ? error.message :
        "Reconciliation failed. Review the files and date.", true);
    } finally {
      if (run === generation) el("reconcile-run").disabled = false;
    }
  });
  function download(name, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  el("reconcile-export").addEventListener("click", async () => {
    const current = report, manifest = reportManifest, serial = generation;
    if (!current || !manifest) return;
    el("reconcile-export").disabled = true;
    try {
      if (!globalThis.crypto?.subtle) throw new Error("Browser SHA-256 unavailable. Export blocked.");
      const canonical = engine.canonicalJson(current);
      const data = new TextEncoder().encode(canonical);
      const digest = await crypto.subtle.digest("SHA-256", data);
      const sourceBinding = await proof.bindReport(manifest, current, crypto.subtle);
      if (serial !== generation || report !== current || reportManifest !== manifest) return;
      const sha256 = [...new Uint8Array(digest)]
        .map(b => b.toString(16).padStart(2, "0")).join("");
      const wrapper = {
        schemaVersion: 1, kind: "OWNER_GENERATED_RECONCILIATION_REPORT",
        provenance: "USER_SUPPLIED_UNVERIFIED",
        payload: current,
        inputManifest: manifest,
        sourceBinding,
        fingerprint: {
          algorithm: "SHA-256", canonicalForm: "UTF-8 JSON of payload, 2-space indent, newline",
          sha256, authenticatesSources: false, digitallySigned: false
        }
      };
      download("metaautomate-reconciliation-" + current.asOfDate + ".json",
        JSON.stringify(wrapper, null, 2) + "\n", "application/json;charset=utf-8");
      announce("Local report downloaded with byte-exact CSV hashes and a report-binding digest. No independent source authentication.");
    } catch (error) {
      announce(error instanceof Error ? error.message : "Report generation failed.", true);
    } finally {
      if (serial === generation) el("reconcile-export").disabled = !report || !reportManifest;
    }
  });
  el("reconcile-example").addEventListener("click", () => {
    const today = el("reconcile-date").value ||
      new Date().toISOString().slice(0, 10);
    // Sample is explicitly illustrative. Matching ledger periods still
    // require user-generated observations from the two dated CSV files.
    const offset = days => new Date(Date.parse(today + "T00:00:00Z") +
      days * 86400000).toISOString().slice(0, 10);
    const example = [
      engine.MOVEMENT_HEADER.join(","),
      "CAP-01," + offset(-6) + "," + today + ",4,1,-1,3",
      "FAB-02," + offset(-6) + "," + today + ",8,0,0,3"
    ].join("\n") + "\n";
    download("metaautomate-synthetic-movement-example.csv", example,
      "text/csv;charset=utf-8");
    announce("Synthetic movement example downloaded. It is not a real business record.");
  });
})();
