# P2-04q — Independent Speech Reviewer Runbook

**Engineering capability, not proof of a completed production review.** This file describes how two distinct people can record a genuine human assessment on an authentic locally generated WAV without exporting their private signing keys.

## Release status
- P2-04q local Piper adapter remains draft; actual licensed ONNX voice, pinned compatible executable, network-denied host and separate pre-execution authorization must be present before execution.
- The helper in \`creative_speech_review_signing.py\` **never creates an accepted review on its own**. \`prepare_review_request\` creates an **unsigned** review in status \`REJECTED\` with all listening/rights/safety booleans \`false\`.
- A real reviewer must open and listen to the full WAV, inspect the matching narration text and evidence files, and manually record every decision before signing. A programmatic all-true fixture in tests is **not** genuine human assessment.
- Signatures authenticate possession of a key, **not reviewer identity**, unless public-key ownership is independently verified against a trusted human registry. They authenticate a stated rights-review conclusion, **not legal rights**.

## Minimum manual evaluation for one voice sample
1. Independent producer and reviewer IDs (distinct verified people), identified script and consent records.
2. Exact output WAV, output SHA-256, audio technical report, exact job digest, model checkpoint/engine/config hashes, execution record and approved checkpoint model card/licence.
3. Reviewer listening notes covering correct words and pronunciation, target accent/language, intelligibility, naturalness/prosody, unwanted voice changes, artifacts/clipping and absence of unconsented impersonation. Record a transcript-review digest.
4. Independent check of safety, legally applicable model/speaker rights, verified voice consent if required, attribution and intended use. Record a safety report digest. Do not turn missing documents into invented hashes.
5. Generate the unsigned checklist with \`prepare_review_request(job, receipt, wav, producer_id="...", reviewer_id="...")\`. It must contain \`decision="REJECTED"\`, false checks and empty safety/transcript evidence fields.
6. The **human reviewer**, not the program, updates the two report-digest fields with real SHA-256 values, sets \`decision="ACCEPTED"\` and makes each seven-item Boolean true **only after actually completing** that review. Otherwise retain \`REJECTED\` and do not sign an accepted decision.
7. Signing takes place on an authorized private offline workstation with an independently registered Ed25519 reviewer key. Keep the PEM file 0600 and out of git/logs/backups visible to others. \`python -m app.creative_speech_review_signing --job /private/job.json --receipt /private/receipt.json --audio /private/generated.wav --review /private/completed-review.json --reviewer-key /private/reviewer.pem --signed-output /private/signed-review.json\`.
8. The tool validates the claimed job/digest, signed human checklist, final WAV bytes, expiry and key signature against the existing \`verify_speech_review\`. It creates a **new** 0600 signed JSON file and never overwrites prior reviews.
9. Separately verify the output signature against the reviewer's trusted registered **public** key (not a key supplied only by the producer). The result remains \`SIGNED_HUMAN_REVIEW_CLAIM_RECORDED_STILL_QUARANTINED\`, not a publication permit. Distribution and customer activation are gated independently.

## Risks and TODOs
- The current final-review implementation accepts externally supplied reviewer IDs/public keys. **Trusted identity-to-key enrolment** and revocation remain an outstanding operational dependency.
- An unsigned JSON receipt is not a trusted execution trace. Genuine model inference requires observed model process with pinned digest, offline isolation records and trustworthy logs, not only \`OPERATOR_ATTESTED_LOCAL_MODEL\`.
- Build an ASR alignment check or at minimum a word-by-word human transcript audit. RMS, sample rate and SHA-256 cannot measure correctness or naturalness.
- Review \`en_US-libritts-high\` speaker selection and dataset-derived voice rights. CC BY 4.0 training corpus is not blanket consent for all identifiable speakers.
- GitHub Actions runner incident #100 still prevents required CI; the exact-commit local source-test gate cannot replace it.

No model is downloaded or installed by the reviewer utility; no payment information, hosted generation, public publishing, subscriptions or server deployment is activated.
