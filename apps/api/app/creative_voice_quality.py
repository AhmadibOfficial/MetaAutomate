"""P2-04v: objective voice-quality preflight, not a human listening substitute.

Analyzes private PCM16 narration for long gaps, clipping, level and script
rate. No model inference, external ASR, downloads, human approval or publish.
The only route to a final quality PASS is separately signed human review.
"""
from __future__ import annotations
from array import array
from hashlib import sha256
from math import isfinite, log10, sqrt
from pathlib import Path
import re
import stat
import sys
import wave

WINDOW_MS=20
NOISE_GATE_DBFS=-38.0
MAX_INTERNAL_SILENCE_SECONDS=1.8
MAX_EDGE_SILENCE_SECONDS=1.5
MAX_CLIPPED_SAMPLE_FRACTION=0.003
MAX_SPEECH_WORDS_PER_MINUTE=195
MIN_SPEECH_WORDS_PER_MINUTE=65
MAX_WER=0.12

class VoiceQualityHold(ValueError):
    pass

def _normal_tokens(text:str)->list[str]:
    if type(text) is not str or not 1<=len(text.strip())<=6000:
        raise VoiceQualityHold("Approved narration text missing or oversized")
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?",text.casefold(),flags=re.UNICODE)

def word_error_rate(reference:str,recognized:str)->dict:
    """Levenshtein WER for external/human supplied transcript (NOT trusted ASR)."""
    gold=_normal_tokens(reference)
    guessed=_normal_tokens(recognized)
    if not gold or len(gold)>1100 or len(guessed)>1800:
        raise VoiceQualityHold("Empty or unreasonable transcript")
    previous=list(range(len(guessed)+1))
    for i, token in enumerate(gold,1):
        current=[i]
        for j, actual in enumerate(guessed,1):
            current.append(min(current[-1]+1,previous[j]+1,
                               previous[j-1]+(token!=actual)))
        previous=current
    edits=previous[-1]
    return {"word_error_rate":round(edits/len(gold),4),
            "reference_words":len(gold),"recognized_words":len(guessed),
            "transcript_source_independently_authenticated":False}

def _level(sum_squares:int,n:int)->float:
    return 20*log10(max(sqrt(sum_squares/max(n,1))/32768.0,1e-12))

def inspect_narration_pcm(path:Path,script:str,*,transcript:str|None=None)->dict:
    """Read-only technical gate. Does not infer pronunciation or naturalness."""
    words=_normal_tokens(script)
    if len(words)<3:
        raise VoiceQualityHold("Narration script needs at least three words")
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve()!=path or not 44<path.stat().st_size<=110_000_000
        or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise VoiceQualityHold("Private absolute PCM narration WAV required")
    digest=sha256(path.read_bytes()).hexdigest()
    try:
        with wave.open(str(path),"rb") as wav:
            channels,width,rate,frames,encoding,_=wav.getparams()
            if (channels not in (1,2) or width!=2
                or rate not in (22050,44100,48000) or encoding!="NONE"
                or frames<rate or frames>rate*600):
                raise VoiceQualityHold("Unsupported PCM16 narration")
            step=max(1,rate*WINDOW_MS//1000)
            chunk_bytes=step*channels*width
            levels=[]
            clipped=0
            sum_sq=0
            samples=0
            peak=0
            # Work on bounded 20ms windows; do not store entire raw audio.
            while True:
                block=wav.readframes(step)
                if not block:
                    break
                pcm=array("h")
                pcm.frombytes(block)
                if sys.byteorder!="little":
                    pcm.byteswap()
                if not pcm:
                    continue
                squares=sum(int(sample)*int(sample) for sample in pcm)
                sum_sq+=squares
                samples+=len(pcm)
                peak=max(peak,max(abs(v) for v in pcm))
                clipped+=sum(abs(v)>=32700 for v in pcm)
                levels.append(_level(squares,len(pcm)))
    except (wave.Error,EOFError,OSError) as exc:
        raise VoiceQualityHold("Narration WAV cannot be decoded") from exc
    if not levels or not samples:
        raise VoiceQualityHold("Narration has no PCM audio")
    duration=frames/rate
    audible=[i for i,value in enumerate(levels) if value>NOISE_GATE_DBFS]
    if audible:
        leading=audible[0]*WINDOW_MS/1000
        trailing=max(0,(len(levels)-1-audible[-1])*WINDOW_MS/1000)
        longest=0
        run=0
        for i in range(audible[0],audible[-1]+1):
            if levels[i]<=NOISE_GATE_DBFS:
                run+=1
                longest=max(longest,run)
            else:
                run=0
        internal=longest*WINDOW_MS/1000
    else:
        leading=duration
        trailing=duration
        internal=duration
    rms=_level(sum_sq,samples)
    peak_dbfs=20*log10(max(peak/32768.0,1e-12))
    clipping=clipped/samples
    cadence=len(words)*60/duration
    problems=[]
    if not audible:
        problems.append("NO_AUDIBLE_SPEECH")
    if internal>MAX_INTERNAL_SILENCE_SECONDS:
        problems.append("EXCESSIVE_MID_SENTENCE_SILENCE")
    if leading>MAX_EDGE_SILENCE_SECONDS:
        problems.append("EXCESSIVE_INITIAL_SILENCE")
    if trailing>MAX_EDGE_SILENCE_SECONDS:
        problems.append("EXCESSIVE_END_SILENCE")
    if clipping>MAX_CLIPPED_SAMPLE_FRACTION:
        problems.append("POSSIBLE_CLIPPING")
    if rms< -33.0:
        problems.append("LOW_AVERAGE_AUDIO_LEVEL")
    if peak_dbfs> -0.4:
        problems.append("INSUFFICIENT_SAMPLE_PEAK_HEADROOM")
    if cadence>MAX_SPEECH_WORDS_PER_MINUTE:
        problems.append("SCRIPT_MAY_BE_RUSHED")
    if cadence<MIN_SPEECH_WORDS_PER_MINUTE:
        problems.append("SCRIPT_MAY_BE_TOO_SLOW")
    comparison=None
    if transcript is not None:
        comparison=word_error_rate(script,transcript)
        if comparison["word_error_rate"]>MAX_WER:
            problems.append("TRANSCRIPT_WORD_MISMATCH")
    return {
        "schema_version":1,
        "wav_sha256":digest,"approved_script_sha256":sha256(script.encode()).hexdigest(),
        "duration_seconds":round(duration,3),
        "sample_rate":rate,"channels":channels,
        "rms_dbfs":round(rms,2),"sample_peak_dbfs":round(peak_dbfs,2),
        "clipped_sample_fraction":round(clipping,6),
        "initial_silence_seconds":round(leading,2),
        "longest_internal_silence_seconds":round(internal,2),
        "end_silence_seconds":round(trailing,2),
        "script_words_per_minute":round(cadence,1),
        "transcript_comparison":comparison,
        "technical_issues":problems,
        "technical_checks_passed":not problems,
        "acoustic_intelligibility_proven":False,
        "natural_neural_voice_proven":False,
        "spoken_transcript_independently_verified":False,
        "signed_human_listening_review_proven":False,
        "publication_authorized":False,
        "status":("HOLD_VOICE_TECHNICAL_QUALITY" if problems
                  else "HOLD_INDEPENDENT_SIGNED_LISTENING_REVIEW"),
    }

def require_technically_ready_narration(path:Path,script:str,
                                        *,transcript:str|None=None)->dict:
    report=inspect_narration_pcm(path,script,transcript=transcript)
    if not report["technical_checks_passed"]:
        raise VoiceQualityHold("Speech technically unsuitable: "+",".join(report["technical_issues"]))
    return report
