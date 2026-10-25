/* P2-060h | Local byte-exact CSV import fingerprints.
   SHA-256 identifies bytes, NOT their author, accuracy, consent, origin or
   time of creation. No external requests, persistence or signing keys. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.MetaImportProof = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const ROLES = Object.freeze(["previous_snapshot", "current_snapshot", "movement_ledger"]);
  const MAX_BYTES = 128000;
  const toHex = bytes => Array.from(new Uint8Array(bytes),
    b => b.toString(16).padStart(2, "0")).join("");
  const digest = async (bytes, subtle) => {
    if (!subtle || typeof subtle.digest !== "function")
      throw new Error("Browser SHA-256 is unavailable; input proof blocked");
    return toHex(await subtle.digest("SHA-256", bytes));
  };
  function canonicalPayload(payload) {
    if (!payload || payload.kind !== "STOCK_SNAPSHOT_RECONCILIATION")
      throw new Error("Expected a reconciliation payload");
    return JSON.stringify(payload, null, 2) + "\n";
  }
  function canonicalBundle(inputManifest, payload) {
    if (!inputManifest || inputManifest.schemaVersion !== 1 ||
        inputManifest.classification !== "USER_SUPPLIED_UNVERIFIED" ||
        !Array.isArray(inputManifest.inputs) ||
        inputManifest.inputs.length !== ROLES.length ||
        !ROLES.every((role, i) => inputManifest.inputs[i]?.role === role))
      throw new Error("Expected the ordered three-input source manifest");
    return JSON.stringify({ inputManifest, payload }, null, 2) + "\n";
  }
  async function inspectInputs(inputs, subtle) {
    if (!Array.isArray(inputs) || inputs.length !== ROLES.length ||
        !ROLES.every((role, i) => inputs[i]?.role === role))
      throw new Error("Exactly three ordered source roles are required");
    const texts = Object.create(null), fingerprints = [];
    for (const { role, bytes } of inputs) {
      if (!(bytes instanceof Uint8Array) ||
          bytes.byteLength < 10 || bytes.byteLength > MAX_BYTES)
        throw new Error("Source bytes must be 10–128000 bytes for " + role);
      let text;
      try { text = new TextDecoder("utf-8", { fatal: true }).decode(bytes); }
      catch (_) { throw new Error("Invalid UTF-8 in " + role); }
      const sha256 = await digest(bytes, subtle);
      texts[role] = text;
      fingerprints.push({ role, byteLength: bytes.byteLength, sha256 });
    }
    return {
      texts,
      inputManifest: {
        schemaVersion: 1,
        classification: "USER_SUPPLIED_UNVERIFIED",
        algorithm: "SHA-256",
        inputs: fingerprints,
        sourceAuthenticated: false,
        consentVerified: false,
        timestampAuthenticated: false,
        includesOriginalFiles: false
      }
    };
  }
  async function bindReport(inputManifest, payload, subtle) {
    const sha256 = await digest(
      new TextEncoder().encode(canonicalBundle(inputManifest, payload)), subtle);
    return {
      algorithm: "SHA-256",
      canonicalForm: "UTF-8 JSON of {inputManifest,payload}, 2-space indent, newline",
      sha256,
      authenticatesSources: false,
      digitallySigned: false
    };
  }
  async function verifyExport(wrapper, inputs, subtle) {
    if (!wrapper || wrapper.kind !== "OWNER_GENERATED_RECONCILIATION_REPORT" ||
        !wrapper.payload || !wrapper.fingerprint ||
        !wrapper.inputManifest || !wrapper.sourceBinding)
      throw new Error("Expected complete owner-generated reconciliation export");
    const actual = await inspectInputs(inputs, subtle);
    const sourceBytesMatch = JSON.stringify(actual.inputManifest) ===
      JSON.stringify(wrapper.inputManifest);
    const payloadHash = await digest(
      new TextEncoder().encode(canonicalPayload(wrapper.payload)), subtle);
    const payloadMatches = payloadHash === wrapper.fingerprint.sha256;
    const bundle = await bindReport(wrapper.inputManifest, wrapper.payload, subtle);
    const bindingMatches = bundle.sha256 === wrapper.sourceBinding.sha256;
    return Object.freeze({
      valid: sourceBytesMatch && payloadMatches && bindingMatches,
      sourceBytesMatch, payloadMatches, bindingMatches,
      independentSourceAuthentication: false
    });
  }
  return Object.freeze({
    ROLES, MAX_BYTES, inspectInputs, bindReport, verifyExport,
    canonicalPayload, canonicalBundle
  });
});
