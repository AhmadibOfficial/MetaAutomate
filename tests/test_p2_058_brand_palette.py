"""P2-058: official 4-color brand system and accessible task workspace."""
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"apps"/"site"
HTML=(SITE/"engage/index.html").read_text(encoding="utf-8")
CSS=(SITE/"assets/project-workspace-brand.css").read_text(encoding="utf-8")
BASE=(SITE/"assets/project-workspace-dark.css").read_text(encoding="utf-8")
TOKENS={
    "--ma-midnight":"#040D20",
    "--ma-blue":"#00A7ED",
    "--ma-silver":"#DCE6F1",
    "--ma-gold":"#EFB94F",
}
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.styles=[]
        self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="link" and a.get("rel")=="stylesheet":
            self.styles.append(a.get("href"))
        if a.get("id"):self.ids.append(a["id"])

def test_all_four_exact_signature_colors_come_from_approved_brand():
    guidance=(ROOT/"docs/brand/GLOBAL_EXPERIENCE_V2.md").read_text()
    site_css=(SITE/"assets/site.css").read_text()
    for variable,value in TOKENS.items():
        assert f"{variable}:{value}" in CSS
        assert value.lower() in guidance.lower()
        assert value.lower() in site_css.lower()
    assert "--ma-deep:#071932" in CSS
    assert "--ma-serif:Georgia" in CSS # no new network font dependencies
    assert "fonts.googleapis.com" not in CSS
    assert "@import" not in CSS

def test_approved_palette_is_loaded_last_and_old_website_stays_intact():
    page=Page()
    page.feed(HTML)
    assert len(page.ids)==len(set(page.ids))
    assert page.styles[-1]=="/assets/project-workspace-brand.css"
    assert page.styles.index("/assets/project-workspace-brand.css")>page.styles.index(
        "/assets/project-workspace-dark.css")
    assert 'content="#040D20"' in HTML
    assert 'id="workspace-sidebar-toggle"' in HTML
    assert 'id="project-chat-input"' in HTML
    assert 'id="workspace-work-panel"' in HTML
    assert 'id="project-ai-experience"' in HTML
    assert 'id="brief-form"' not in HTML
    assert "/assets/project-workspace-brand.css" not in (SITE/"index.html").read_text()
    assert "/assets/project-workspace-brand.css" not in (SITE/"services/index.html").read_text()

def test_all_four_colors_have_actual_roles_in_both_chat_and_work():
    must=[
        "background:var(--ma-midnight)",
        "background:var(--ma-silver)",
        "background:var(--ma-blue)",
        "background:var(--ma-gold)",
        "color:var(--ma-midnight)",
        "color:var(--ma-silver)",
        ".project-immersive-page .workspace-work-grid",
        ".project-immersive-page .project-chat-composer",
        ".project-immersive-page .project-chat-new",
        ".project-immersive-page .project-chat-summary",
        ".project-immersive-page .project-ai-consent",
        ".project-immersive-page .project-chat-side",
        ".project-immersive-page .workspace-sidebar-toggle",
        ".project-immersive-page .workspace-mode-switch",
        ".project-immersive-page .project-chat-top h1::after",
        ".project-immersive-page .project-chat-side::before",
        "var(--ma-gold)",
        "var(--ma-blue)",
    ]
    for token in must:
        assert token in CSS,token
    assert "position:fixed" in CSS
    assert "@media(max-width:740px)" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert ":focus-visible" in CSS
    assert "data-sidebar" in BASE

def relative_luminance(color):
    channels=[int(color[i:i+2],16)/255 for i in (1,3,5)]
    channels=[c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
              for c in channels]
    return sum(a*b for a,b in zip(channels,(0.2126,0.7152,0.0722)))

def contrast(a,b):
    first,second=relative_luminance(a),relative_luminance(b)
    return (max(first,second)+.05)/(min(first,second)+.05)

def test_text_palette_contrast_meets_wCAG_AA_for_selected_solid_surfaces():
    important=[
        ("#DCE6F1","#040D20"),
        ("#DCE6F1","#071932"),
        ("#040D20","#00A7ED"),
        ("#040D20","#EFB94F"),
        ("#040D20","#DCE6F1"),
        ("#3d5573","#DCE6F1"),
        ("#415976","#DCE6F1"),
        ("#EFB94F","#071932"),
        ("#73d9ff","#102c4d"),
    ]
    for fg,bg in important:
        assert contrast(fg,bg)>=4.5,(fg,bg,contrast(fg,bg))
