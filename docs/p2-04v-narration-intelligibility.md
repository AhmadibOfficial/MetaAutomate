# P2-04v — Narration Intelligibility and Speech Quality Acceptance

**Reported defect:** the October 17, 2026 32-second MetaAutomate demo has unclear and robotic eSpeak narration. Correct status is **VOICE QUALITY REJECTED**, regardless of the valid H.264/AAC/subtitle container.

## Reproduction evidence (technical only)

The private demonstration's four subtitles match the following 8s scenes. The audio was produced using conventional eSpeak, not neural text-to-speech.
- Scene 1: "MetaAutomate brings creative ideas into one secure production workflow."
- Scene 2: "Design original images, review their rights, and preserve every source."
- Scene 3: "Build short video scenes, then finish them as a Full HD film."
- Scene 4: "Add spoken narration, synchronized captions, and independent human review."

FFmpeg \`silencedetect=noise=-35dB:d=0.2\` found significant silent stretches of approximately **2.92 seconds (5.10-8.02s)**, **3.26 seconds (12.76-16.02s)**, and **3.43 seconds (20.57-24.00s)**. Shorter pauses and the 2.21s ending are also present.

Single-pass FFmpeg loudnorm measured about **-20.04 LUFS integrated** and **-4.24 dBTP true peak** on the original video, so the sample is quieter than a typical online spoken-word target. Testing *only the filter* \`highpass=f=70,lowpass=f=8500,loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000\` on the old audio produced ~**-16.38 LUFS** and **-1.50 dBTP**. **This is a mixing improvement, not a correction to robotic pronunciation or proof of audio quality.**

## Source changes

- \`app.creative_voice_quality.inspect_narration_pcm\` reads private 16-bit PCM WAV (22.05, 44.1 or 48 kHz) in 20ms analysis windows. Reports average RMS, sample peak, clipping fraction, longest mid-sentence/leading/trailing silence, declared script speech rate and WER if a separate transcript is supplied.
- The technical gate blocks all-silence output, audio with **>1.8s internal silence**, **>1.5s leading/trailing silence**, possible clipping, insufficient level/headroom, and severely rushed/slow scripts. If an external/human transcript is supplied, an observed **WER >12%** also blocks it. These are heuristic first-version policy thresholds and may require different language or storytelling profiles later.
- \`creative_multimodal_operator --render\` now requires an approved script and separately checked transcript from owner-only local text files; the exact source receipt verification occurs before any audio QA, and QA occurs **before** the final composer. An omitted script/transcript blocks the full film.
- The finishing engine applies mild high-pass/low-pass filters and -16 LUFS/-1.5 dBTP loudness targeting before mixing. Changing loudness **cannot create natural human-like speech** or fix mispronounced words.
- Synthetic unit tests exercise long pauses, clipping, silent samples, tempo, word mismatch, unsafe file permissions, lack of transcript and denial of final rendering when the voice fails.
- A **technically clean** sample still has status \`HOLD_INDEPENDENT_SIGNED_LISTENING_REVIEW\` and permanently sets \`acoustic_intelligibility_proven=false\` and \`natural_neural_voice_proven=false\`. Source tests use 220 Hz sine-wave fixtures, **not voiced language**. Do not interpret test passes as intelligible synthetic speech.

## Human voice acceptance requirements

For customer-facing MetaAutomate, eSpeak alone is not acceptable as the default voice. Require a legally reviewed natural neural voice candidate and listener-based evaluation covering:
1. Exact spoken wording checked against the **approved signed text** and independently sourced transcript or ASR process evidence; normalized WER should generally be <=12% for supported language/accent (supplemental, not sufficient).
2. Intelligible consonants/vowels, clear pacing, no long unexpected dead air, correct emphasis and pronunciation of brand, personal and technical names.
3. Native or suitable accent/language for the audience, emotional appropriateness, absence of unnatural prosody or speaker drift.
4. Audible dynamic level on phone speakers, safe true peaks, measured voice/mix balance, caption legibility/timing and no unconsented voice cloning or impersonation.
5. Real, independent listening reviewer signature pinned to the exact WAV, reference script, consent/right evidence and final film hash. **Review data or a WER value supplied by the same producer does not prove the reviewer heard the WAV.**
6. Optional second voice candidate comparison and rejection workflow so creators can re-generate a failed voice without redoing approved visuals. Preserve all rights/consent checks.

## Model evaluation direction — not installed or approved

Prioritize **Kokoro-82M** as a potential higher-naturalness offline TTS engine for English narration. The official [hexgrad/Kokoro-82M model card](https://huggingface.co/hexgrad/Kokoro-82M) lists **Apache-2.0 model weights**, example 24kHz output, training-data attribution obligations for included CC BY sources, and its own model/voice descriptions. Evaluate the actual chosen model revision, dependency stack (including espeak-ng G2P obligations), individual voice provenance and commercial terms before any use. Kokoro is **a candidate**, not proof of legal clearance or available execution. The existing Piper PR #97 remains an offline candidate for lower-resource deployments; its model-specific voice rights are still under review.

No Kokoro/Piper neural inference was attempted in this PR. No speaker identity was cloned, no model weights were downloaded, and no audio generation service, hosted API, GPU instance, paid subscription or publishing was enabled.

## Current unresolved authenticity gaps

The approved script and reviewed transcript are 0600 files and validated text, **but their actual external author/reviewer identities and hashes are not yet cryptographically bound to the original Piper job and witness records across PR #97/#102**. A human-supplied transcript is not a trusted ASR transcript. A producer can enter a copy of the script as transcript even when the actual WAV speaks different words. The signed audio review, trusted enrollment, witnessed model process and semantic matching are independent required gates. The current quality module is a **heuristic rejection filter**, not a voice-quality acceptance authority.

## Release boundaries

Stacked on draft PR #102, which depends on #101, #94 and separately #97/#95. GitHub Actions issue #100 remains unresolved; source regression checks and exact-commit results are **not known to have passed CI**. Existing technical demo is explicitly voice-quality **REJECTED**. No merge, production deployment, subscriptions, customer activation or public media release.
