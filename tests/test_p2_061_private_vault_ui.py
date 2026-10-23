"""P2-061 private browser presentation gate, no production auth or cloud access."""
from __future__ import annotations
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"apps/web"


def test_data_lab_visible_only_in_authenticated_private_workspace():
    source=(WEB/"index.html").read_text()
    script=(WEB/"assets/app.js").read_text()
    assert 'id="workspace-shell"' in source
    assert 'id="nav-data-lab"' in source
    assert 'data-view="data-lab" hidden' in source
    assert 'id="data-lab-view" class="app-screen" hidden' in source
    assert 'localDataLabEnabled = config.local_data_lab_available === true' in script
    assert 'state.session || !localDataLabEnabled' in script
    assert 'clearLabPreview()' in script


def test_manual_import_claim_and_no_external_publication():
    source=(WEB/"index.html").read_text()
    script=(WEB/"assets/app.js").read_text()
    for field in ("lab-file", "lab-retention", "lab-owner-claim",
                  "lab-items", "lab-preview", "lab-purge", "lab-audit"):
        assert 'id="' + field + '"' in source
    assert 'OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA' in script
    assert '"X-CSRF-Token"' in script
    assert "file.arrayBuffer()" in script
    assert 'credentials:"same-origin"' in script
    assert "textContent=JSON.stringify(result.records,null,2)" in script
    assert "window.confirm(" in script
    assert '"/v1/data-lab/inventory/' in script
    assert not re.search(r'(?i)\bpublish.*(?:fetch|request)\s*\(',script)


def test_ui_four_palette_colors_and_data_not_on_public_marketing_site():
    css=(WEB/"assets/styles.css").read_text()
    for code in ("#040D20","#00A7ED","#DCE6F1","#EFB94F"):
        assert code in css
    public=(ROOT/"apps/site/index.html").read_text()
    assert 'id="data-lab-view"' not in public
    assert "/v1/data-lab/inventory" not in public


def test_local_website_server_can_resolve_inventory_vault():
    main=(ROOT/"apps/api/app/main.py").read_text()
    assert '@app.get("/data-lab", include_in_schema=False)' in main
    assert 'if os.environ.get("MAT_DATA_LAB_ENABLED") == "1":' in main
    assert '"LOCAL_REHEARSAL_ONLY"' in main
