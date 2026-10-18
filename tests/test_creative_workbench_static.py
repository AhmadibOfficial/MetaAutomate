"""Creative Workbench source contract: truthful creative service and browser privacy."""
from html.parser import HTMLParser
from pathlib import Path
import re

SITE=Path(__file__).resolve().parents[1]/"apps/site"

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.links=[]
        self.form_ids=[]
        self.choices={}
        self.scripts=[]
    def handle_starttag(self,tag,attrs):
        props=dict(attrs)
        if props.get("id"):self.ids.add(props["id"])
        if tag=="a":self.links.append(props.get("href",""))
        if tag=="form":self.form_ids.append(props.get("id"))
        if tag=="script":self.scripts.append(props.get("src",""))

def load(path):
    return (SITE/path).read_text("utf-8")
def parse(path):
    p=FormParser()
    p.feed(load(path))
    return p

def test_new_creative_workbench_has_all_real_destinations_and_right_brand():
    home=load("index.html")
    services=load("services/index.html")
    creative=load("creative/index.html")
    hp=parse("index.html")
    sp=parse("services/index.html")
    cp=parse("creative/index.html")
    assert "/creative/" in hp.links
    assert "/creative/" in sp.links
    assert "/services/#experience" in cp.links
    assert "/engage/?service=Product%20Design%20%26%20Experience" in cp.links
    assert "Image Studio &amp; Video Projects" in home
    assert "Create a branded image now" in services
    assert "WORKING IMAGE CREATOR" in creative
    assert "Create original business graphics" in creative
    assert "Independent" not in creative or "Human" in creative
    assert "/assets/metaautomate-mark.webp" in creative
    assert set(cp.form_ids)=={"creative-brief-form"}
    assert {"/assets/site.js","/assets/creative.js","/assets/creative-maker.js"}<=set(cp.scripts)
    assert len(cp.ids)==len(re.findall(r'\bid="([^"]+)"',creative)), "Repeated HTML ID"
    for key in ("creative-kind","creative-goal","creative-rights","creative-likeness",
                "creative-proof","creative-reviewer","creative-duration",
                "creative-output","creative-structure","creative-checks",
                "creative-outcome","creative-export"):
        assert key in cp.ids

def test_creative_runtime_has_no_external_generation_or_publishing():
    js=load("assets/creative.js")
    assert "textContent" in js
    assert "new Blob(" in js
    assert "URL.createObjectURL" in js
    assert "form.reportValidity()" in js
    assert "no" in js.lower()
    assert "licensed" in js
    assert "permission" in js
    assert '<option value="unknown">' in load("creative/index.html")
    assert 'const rightsKnown = ["owned", "licensed", "permission", "none"].includes(v.rights)' in js
    assert "consented" in js
    assert "NOT APPROVED" in js
    assert "HOLD" in js
    assert "NO MEDIA GENERATED OR PUBLISHED" in js
    for dangerous in ("fetch(", "XMLHttpRequest", "sendBeacon", "localStorage",
                      "sessionStorage", "innerHTML", "eval(", "setInterval(",
                      "MediaRecorder", "new WebSocket"):
        assert dangerous not in js
    # Source is browser-only; real provider calls are not implied by
    # the existence of the image/video planner.
    assert not (SITE/"creative"/"generate.html").exists()

def test_video_runtime_and_accessibility_are_review_constrained():
    page=load("creative/index.html")
    script=load("assets/creative.js")
    for value in ("30","60","90","120"):
        assert f'<option value="{value}"' in page
    assert 'aria-live="polite"' in page
    assert 'aria-labelledby="creative-form-title"' in page
    assert 'aria-labelledby="creative-output-title"' in page
    assert 'type="submit"' in page
    assert 'type="reset"' in page
    assert 'role="status"' in page
    assert '[30, 60, 90, 120]' in script
    assert 'rightsKnown' in script and 'consentKnown' in script
    assert 'canReview = issues.length === 0' in script
    assert 'not an authenticated approval' not in script  # no false "signed approval"
