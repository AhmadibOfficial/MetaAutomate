# P2-04q — Verified AI Speech Generation: offline adapter (source increment)

**Status:** implementation and synthetic negative tests only. No licensed voice checkpoint, executable, genuine synthesis, voice-quality evidence, signed approval, or legal assessment was supplied or run. Do **not** call this capability genuinely verified.

## Integration
The optional `apps/api/app/creative_speech_offline.py` adapter consumes the P2-04p job contract with exact authorized text, a local ONNX voice checkpoint/config pair, and a pinned local Piper-compatible executable. It refuses execution unless four operator attestation flags are present; those flags are **not** independent proof of host egress isolation, rights or signatures. It checks the checkpoint digest, local paths, private file modes and blocks model downloads. It creates private quarantined WAV and a separate evidence record with model/config/engine/text/output digests, never publishing.

It calls the local Piper CLI using an argument array with stdin and bounded runtime. **A model may emit a different WAV sample rate or duration than a requested target, in which case downstream validation blocks it.** Fake runner fixtures are marked `TEST_ONLY_FAKE_RUNNER_NOT_AI`.

## Licensing gate

Piper's archived `rhasspy/piper` project lists MIT software licensing, while maintained `OHF-Voice/piper1-gpl` uses GPLv3. Voice models have **separate licenses** and may restrict commercial use. Check exact engine dependencies, executable distribution, model card, trained-voice consent and phonemizer license for the specific pinned versions. Do not infer that MIT on an old repository makes a newer packaged binary permissive or that any model is commercial-use cleared.

References:
- https://github.com/rhasspy/piper/blob/master/LICENSE.md
- https://github.com/OHF-Voice/piper1-gpl
- https://github.com/OHF-Voice/piper1-gpl/discussions/30

## Acceptance (not yet achieved)

1. Approved private host, egress-denied container, executable/engine digest and pinned voice model/config plus a documented commercial-use decision.
2. Independent signed human authorization binding approved text, voice identity, consent records, model/license hashes, intended use and time window; **the adapter does not yet cryptographically verify these signatures**.
3. Actual speech inference recording and independently verified process identity/runtime evidence, output WAV duration/format, SHA-256 receipt and sample integrity.
4. Listener-based language accuracy, intelligibility, prosody, pronunciation, clipping, speaker identity and accessibility review. Transcription or ASR consistency may supplement, not replace listening.
5. Signed independent post-output human safety, rights and voice-consent review bound to exact output hash. Keep output quarantined; release and publishing are separate decisions.
6. Only then connect narration assets to PR #94 cinematic finishing; retain separate CI and operational gates.

This draft is stacked on **PR #95** and must not merge directly into main before its prerequisite passes review. No hosting, subscriptions, customer use, deployment or publishing. Phase 01 (3/9) and Phase 02/03 operational NO-GO remain.
