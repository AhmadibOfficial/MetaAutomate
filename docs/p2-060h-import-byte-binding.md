# P2-060h — Byte-exact import manifest and report binding

**Status:** Source implementation on a new draft branch. **NOT independently
tested or developer-local accepted** at the new commit. P2-060g parent at
`f202a0c752893a77ebafab6a6f49976b44ebe04c` had 63/63 local
pytest checks and `DEVELOPER_LOCAL_RECONCILIATION_PASS` reported by the
owner on 2026-10-25. Those outcomes **do not transfer** to this new commit.

## Bounded engineering improvement

The existing P2-060g reconciliation report hashed the **derived JSON payload**,
but did not identify which exact source CSV byte streams produced that report.
P2-060h adds a local-only **owner-generated import manifest** and a second
digest binding the manifest to the payload.

For the three files, in fixed order, the browser records:

1. `previous_snapshot` — exact imported bytes and SHA-256;
2. `current_snapshot` — exact imported bytes and SHA-256;
3. `movement_ledger` — exact imported bytes and SHA-256.

The manifest records **only** each role, exact byte count and SHA-256.
Original filenames, CSV bytes, user identifiers and file paths are excluded
from the manifest. The original CSV data is still used locally to compute the
report; the existing report includes the declared stock and sales figures,
so keep the downloaded report **private**.

The workbench reads each file using `arrayBuffer()` and passes those exact
bytes to the hashing and strict UTF-8 decoding logic. Invalid UTF-8, absent
Web Crypto SHA-256, missing/extra/reordered roles, and files outside
10–128000 bytes fail closed. The same decoded bytes are passed to the existing
deterministic P2-060g reconciliation engine. The UI invalidates report and
manifest together whenever any input or the assessment date changes.

## Reproducibility and limitations

The report wrapper retains the original P2-060g `fingerprint.sha256`
computed over canonical payload JSON. It adds:

- `inputManifest`: owner-supplied **UNVERIFIED** file-byte fingerprints;
- `sourceBinding.sha256`: SHA-256 of UTF-8
  `JSON.stringify({inputManifest, payload}, null, 2) + "\n"`.

A local verifier `MetaImportProof.verifyExport(wrapper, inputs, subtle)`
checks the three original input byte streams against the exported manifest,
recomputes the original payload hash, and recomputes the binding hash.
Changing one imported byte, a derived count, the manifest or a hash must
cause verification to fail. This provides **tamper detection only relative
to the owner's copies of files**. An attacker who can rewrite the inputs
and report can generate fresh valid hashes. It is **not a digital signature**,
independent timestamp, trusted upstream export, merchant consent evidence,
third-party audit or proof of business accuracy.

No external connectors, credentials, uploads, customer records, AI calls,
marketing attribution, publication, database operations or cloud deployment.

## Test and review gate

On the owner's Kali checkout, first confirm a clean tree and the exact
head SHA from the draft PR. Then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_p2_060h_import_binding.py \
  tests/test_p2_060_reconciliation.py \
  tests/test_p2_060_temporal_evidence.py \
  tests/test_p2_060_inventory_quality.py \
  tests/test_p2_060_reflow.py \
  tests/test_p2_060_accessibility.py \
  tests/test_p2_060_campaign_workbench.py \
  tests/test_p2_060_browser_harness.py \
  tests/test_p2_060_evidence_review.py

PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
  "$HOME/.local/share/metautomate-browser-venv/bin/python" \
  scripts/verify_campaign_reconciliation.py
```

**Expected** 69 Python test cases (63 inherited + 6 new), with one new
Python test executing **13** Node byte-manifest tests, and a real
`DEVELOPER_LOCAL_RECONCILIATION_PASS` browser marker. These are
**acceptance targets, not claimed outcomes**. The browser verifier now also
checks SHA-256 for each exact imported CSV, the manifest/payload binding,
no-egress loopback behavior, source-edit invalidation and responsive widths.

## Startup Qatar START evidence impact

**Engineering evidence only:** a reproducible local data-lineage technique
helps substantiate the product roadmap's integrity controls. It does not
verify market need, real customer usage, sales, company incorporation, team
capacity, willingness to pay, pricing, unit economics, financials, ownership
or legal eligibility. The official Qatar Development Bank START criteria
include an unmet need, validated concept, roadmap, market readiness,
business model and committed team:

https://www.qdb.qa/en/Financing-And-Funding/Equity-And-Investment/Startup-Qatar-Investment-Program

**As reviewed 2026-10-25**, QDB lists a *maximum*, not an award or ask,
of USD 1.1 million for START, milestone-tranched. Public program
information is not MetaAutomate-specific validation.

**Operational state:** foundation 3/9 verified, CI unavailable due to
existing GitHub Actions billing restrictions, independent AppSec/real data
provenance pending, release NO-GO. Keep PR draft, unmerged and undeployed;
no Qatar application submission without explicit human authorization.
