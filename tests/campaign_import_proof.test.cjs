"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { webcrypto, createHash } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const proof = require("../apps/site/assets/campaign-import-proof.js");
const encoder = new TextEncoder();
const bytes = text => encoder.encode(text);
const originals = [
  { role: "previous_snapshot", bytes: bytes("sku,stock\nCAP-01,10\n") },
  { role: "current_snapshot", bytes: bytes("sku,stock\nCAP-01,11\n") },
  { role: "movement_ledger", bytes: bytes("sku,sold\nCAP-01,3\n") }
];
const copy = () => originals.map(item => ({ role: item.role, bytes: new Uint8Array(item.bytes) }));
const payload = { schemaVersion: 1, kind: "STOCK_SNAPSHOT_RECONCILIATION",
  asOfDate: "2026-10-25", classification: "USER_SUPPLIED_UNVERIFIED",
  counts: { declaredArithmeticMatches: 1 } };
async function exportSample() {
  const input = copy();
  const { inputManifest } = await proof.inspectInputs(input, webcrypto.subtle);
  const sha256 = createHash("sha256").update(proof.canonicalPayload(payload)).digest("hex");
  const sourceBinding = await proof.bindReport(inputManifest, payload, webcrypto.subtle);
  return { input, wrapper: {
    schemaVersion: 1, kind: "OWNER_GENERATED_RECONCILIATION_REPORT",
    provenance: "USER_SUPPLIED_UNVERIFIED", payload: structuredClone(payload),
    fingerprint: { algorithm: "SHA-256",
      canonicalForm: "UTF-8 JSON of payload, 2-space indent, newline",
      authenticatesSources: false, digitallySigned: false, sha256 },
    inputManifest, sourceBinding
  }};
}

test("exact source byte SHA-256 and lengths are recorded without filenames", async () => {
  const { texts, inputManifest } = await proof.inspectInputs(copy(), webcrypto.subtle);
  assert.deepEqual(inputManifest.inputs.map(x => x.role), proof.ROLES);
  assert.equal(inputManifest.inputs[0].sha256,
    createHash("sha256").update(originals[0].bytes).digest("hex"));
  assert.equal(inputManifest.inputs[0].byteLength, originals[0].bytes.length);
  assert.equal(texts.previous_snapshot, new TextDecoder().decode(originals[0].bytes));
  assert.equal(inputManifest.sourceAuthenticated, false);
  assert.equal(inputManifest.consentVerified, false);
  assert.equal(inputManifest.timestampAuthenticated, false);
  assert.equal(inputManifest.includesOriginalFiles, false);
  assert.doesNotMatch(JSON.stringify(inputManifest), /fileName|path|customerId/);
});

test("byte-level changes are visible even when decoded CSV values are equivalent", async () => {
  const inputs = copy();
  const a = await proof.inspectInputs(inputs, webcrypto.subtle);
  inputs[0].bytes = Uint8Array.from([239,187,191,...inputs[0].bytes]);
  const b = await proof.inspectInputs(inputs, webcrypto.subtle);
  assert.notEqual(a.inputManifest.inputs[0].sha256,b.inputManifest.inputs[0].sha256);
});

test("role order, duplicate roles, missing roles and nonbytes fail closed", async () => {
  await assert.rejects(proof.inspectInputs(copy().reverse(),webcrypto.subtle), /three ordered/);
  await assert.rejects(proof.inspectInputs(copy().slice(1),webcrypto.subtle), /three ordered/);
  const dup = copy();dup[1].role = dup[0].role;
  await assert.rejects(proof.inspectInputs(dup,webcrypto.subtle), /three ordered/);
  const bad = copy();bad[1].bytes = "not bytes";
  await assert.rejects(proof.inspectInputs(bad,webcrypto.subtle), /Source bytes/);
});

test("oversized, undersized and invalid UTF-8 imports fail before report creation", async () => {
  const tooLarge = copy();tooLarge[0].bytes = new Uint8Array(128001);
  await assert.rejects(proof.inspectInputs(tooLarge,webcrypto.subtle), /128000/);
  const tooSmall = copy();tooSmall[0].bytes = new Uint8Array(9);
  await assert.rejects(proof.inspectInputs(tooSmall,webcrypto.subtle), /128000/);
  const invalid = copy();invalid[0].bytes = Uint8Array.from([255,254,...invalid[0].bytes]);
  await assert.rejects(proof.inspectInputs(invalid,webcrypto.subtle), /Invalid UTF-8/);
});

test("unavailable SHA-256 blocks import proof and cannot silently downgrade", async () => {
  await assert.rejects(proof.inspectInputs(copy(),undefined), /SHA-256 is unavailable/);
  const {inputManifest}=await proof.inspectInputs(copy(),webcrypto.subtle);
  await assert.rejects(proof.bindReport(inputManifest,payload,null), /SHA-256 is unavailable/);
});

test("canonical input manifest and bundle fingerprint are deterministic", async () => {
  const {inputManifest}=await proof.inspectInputs(copy(),webcrypto.subtle);
  const a=await proof.bindReport(inputManifest,payload,webcrypto.subtle);
  const b=await proof.bindReport(structuredClone(inputManifest),
    structuredClone(payload),webcrypto.subtle);
  assert.equal(a.sha256,b.sha256);
  assert.equal(a.sha256,createHash("sha256")
    .update(proof.canonicalBundle(inputManifest,payload),"utf8").digest("hex"));
  assert.equal(a.authenticatesSources,false);
  assert.equal(a.digitallySigned,false);
});

test("complete owner-generated report verifies against original CSV bytes", async () => {
  const {input,wrapper}=await exportSample();
  const result=await proof.verifyExport(wrapper,input,webcrypto.subtle);
  assert.deepEqual(result,{
    valid:true,sourceBytesMatch:true,payloadMatches:true,
    bindingMatches:true,independentSourceAuthentication:false
  });
});

test("one changed CSV byte invalidates source proof even with intact report", async () => {
  const {input,wrapper}=await exportSample();
  input[2].bytes[12] ^= 1;
  const result=await proof.verifyExport(wrapper,input,webcrypto.subtle);
  assert.equal(result.valid,false);
  assert.equal(result.sourceBytesMatch,false);
  assert.equal(result.payloadMatches,true);
  assert.equal(result.bindingMatches,true);
});

test("tampered payload invalidates payload and bundle fingerprints", async () => {
  const {input,wrapper}=await exportSample();
  wrapper.payload.counts.declaredArithmeticMatches=999;
  const result=await proof.verifyExport(wrapper,input,webcrypto.subtle);
  assert.equal(result.valid,false);
  assert.equal(result.payloadMatches,false);
  assert.equal(result.bindingMatches,false);
});

test("altered manifest invalidates original source and bundle fingerprint", async () => {
  const {input,wrapper}=await exportSample();
  wrapper.inputManifest.inputs[0].sha256="0".repeat(64);
  const result=await proof.verifyExport(wrapper,input,webcrypto.subtle);
  assert.equal(result.valid,false);
  assert.equal(result.sourceBytesMatch,false);
  assert.equal(result.bindingMatches,false);
});

test("altered binding hash invalidates otherwise intact report", async () => {
  const {input,wrapper}=await exportSample();
  wrapper.sourceBinding.sha256="f".repeat(64);
  const result=await proof.verifyExport(wrapper,input,webcrypto.subtle);
  assert.equal(result.valid,false);
  assert.equal(result.sourceBytesMatch,true);
  assert.equal(result.payloadMatches,true);
  assert.equal(result.bindingMatches,false);
});

test("invalid wrapper and malformed manifest fail closed", async () => {
  const {input,wrapper}=await exportSample();
  await assert.rejects(proof.verifyExport({},input,webcrypto.subtle), /complete/);
  const bad=structuredClone(wrapper);bad.inputManifest.inputs.reverse();
  await assert.rejects(proof.verifyExport(bad,input,webcrypto.subtle), /ordered/);
});

test("source module never reads remote services, storage, model or credentials", () => {
  const source=fs.readFileSync(path.join(__dirname,
    "../apps/site/assets/campaign-import-proof.js"),"utf8");
  for(const banned of [/\bfetch\s*\(/,/XMLHttpRequest/,/WebSocket/,/localStorage/,
    /sessionStorage/,/document\.cookie/,/model\.infer/,/provider\.publish/]){
    assert.doesNotMatch(source,banned);
  }
});

test("rejects spoofed authentication or signature metadata even with unchanged hashes", async () => {
  const fields = [
    ["fingerprint", "authenticatesSources"],
    ["fingerprint", "digitallySigned"],
    ["sourceBinding", "authenticatesSources"],
    ["sourceBinding", "digitallySigned"],
    ["inputManifest", "sourceAuthenticated"],
    ["inputManifest", "consentVerified"],
    ["inputManifest", "timestampAuthenticated"],
    ["inputManifest", "includesOriginalFiles"]
  ];
  for (const [object, field] of fields) {
    const { input, wrapper } = await exportSample();
    wrapper[object][field] = true;
    await assert.rejects(
      proof.verifyExport(wrapper, input, webcrypto.subtle),
      /Untrusted or unsupported/, object + "." + field);
  }
});

test("rejects unsupported versions, provenance, algorithms, and canonical forms", async () => {
  const cases = [
    [["schemaVersion"], 2],
    [["provenance"], "INDEPENDENTLY_VERIFIED"],
    [["payload", "schemaVersion"], 2],
    [["payload", "classification"], "INDEPENDENTLY_VERIFIED"],
    [["inputManifest", "algorithm"], "SHA-1"],
    [["fingerprint", "algorithm"], "SHA-1"],
    [["fingerprint", "canonicalForm"], "unknown"],
    [["fingerprint", "sha256"], "invalid"],
    [["sourceBinding", "algorithm"], "SHA-1"],
    [["sourceBinding", "canonicalForm"], "unknown"],
    [["sourceBinding", "sha256"], "invalid"]
  ];
  for (const [path, value] of cases) {
    const { input, wrapper } = await exportSample();
    let target = wrapper;
    for (const key of path.slice(0, -1)) target = target[key];
    target[path.at(-1)] = value;
    await assert.rejects(
      proof.verifyExport(wrapper, input, webcrypto.subtle),
      /Untrusted or unsupported/, path.join("."));
  }
});
