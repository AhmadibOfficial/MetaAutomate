#!/usr/bin/env python3
"""Technical 30-second WebM + audio acceptance with Chromium and FFprobe.

Fixture audio is a sine wave, *not* an intelligible or neural narrator.
"""
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import wave
from playwright.sync_api import expect, sync_playwright

BASE="http://127.0.0.1:18080"
ART=Path("artifacts/validation")
ART.mkdir(parents=True,exist_ok=True)

def tone(path):
    with wave.open(str(path),"wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(8000)
        chunk=8000
        for second in range(30):
            block=b"".join(struct.pack("<h",int(2400*math.sin(2*math.pi*220*i/8000)))
                           for i in range(chunk))
            writer.writeframes(block)

def main():
    errors=[]
    with tempfile.TemporaryDirectory() as directory:
        wav=Path(directory)/"technical-30s-tone.wav"
        tone(wav)
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(viewport={"width":1365,"height":900},
                                        accept_downloads=True)
            page=context.new_page()
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(BASE+"/creative/",wait_until="networkidle")
            expect(page.locator("#maker-canvas")).to_be_visible()
            page.locator("#video-maker-audio").set_input_files(str(wav))
            expect(page.locator("#video-maker-audio-preview")).to_be_visible()
            page.locator("#video-maker-rights").check()
            page.locator("#video-maker-run").click()
            expect(page.locator("#video-maker-status")).to_contain_text(
                "Narrated video created",timeout=60000)
            expect(page.locator("#video-maker-preview")).to_be_visible()
            with page.expect_download() as event:
                page.locator("#video-maker-download").click()
            output=Path(directory)/"technical-video.webm"
            event.value.save_as(output)
            assert output.stat().st_size>10000
            cmd=["ffprobe","-v","error","-show_entries",
                 "stream=codec_type,codec_name,width,height","-of","json",str(output)]
            info=json.loads(subprocess.check_output(cmd,text=True,timeout=20))
            video=[x for x in info["streams"] if x.get("codec_type")=="video"]
            audio=[x for x in info["streams"] if x.get("codec_type")=="audio"]
            assert video and audio,info
            assert video[0]["width"]==1280 and video[0]["height"]==720,info
            assert audio[0]["codec_name"] in ("opus","vorbis"),info
            page.screenshot(path=str(ART/"functional-narrated-video-desktop.png"),
                            full_page=True)
            context.close()
            browser.close()
    assert not errors,errors
    print("PASS WebM 1280x720 + actual encoded Opus audio using *non-voice* technical test fixture.")

if __name__=="__main__":
    main()
