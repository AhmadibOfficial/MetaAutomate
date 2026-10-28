# P2-064 — Interactive universal MetaAutomate workspace

**Status:** source-reviewed website update, draft branch. **Not merged or deployed, no live AI or external operations.**

## What changed

- Preserves the simple four-screen experience: Home, My Work, Results, Team & Settings.
- Adds five interactive **objective choices** on Home: customer experience, business operations, costs and finance, intelligent automation, business intelligence.
- Preserves five quick industry starting cards and adds a selector for **17 additional industry design examples** from the versioned P2-063 catalog, including a custom organization workflow.
- Cross-combines selected objective and industry to produce an actually interactive, four-step local human-reviewed plan. Supports up to 15 session-only plans, session results and local exports. This is rule-based planning, **not AI inference or real-world automation**.
- Retains the functional local inventory CSV inspection and human-reviewed marketing-draft tools.
- Reuses approved navy (#081c36), blue (#0788d2), gold (#e9b84f), silver (#e2e9f1), with responsive cards, keyboard focus and reduced-motion handling.
- Homepage explains industry expansion without claiming 22 operational products or public customer availability.

## Verification and status

Checked from committed GitHub source:
- JavaScript parsed using V8: PASS.
- 64 HTML IDs unique; all referenced JavaScript IDs exist: PASS.
- 5 interactive goals, 5 existing quick industry cards, 17 additional options + placeholder, 22 source-only sector profiles in the P2-063 catalog: PASS.
- Existing local CSP `connect-src 'none'`, human review and session reset retained in source.
- New static source assertions: `tests/test_p2_064_interactive_universal_workspace.py`.

**Not yet run:** Python pytest on exact branch, headless Playwright, accessibility checks with real keyboard/screen readers, complete app regressions, authenticated tenant security, product conversion analytics or founder human usability.

Recommended local verification on an **already approved non-destructive review worktree**:

```sh
cd "$HOME/MetaAutomate"
git fetch origin
git worktree list
# Never overwrite an existing directory; pick a new review path after inspection.
git worktree add --detach "$HOME/MetaAutomate-P2-064-Review" origin/feature/p2-064-interactive-universal-workspace
cd "$HOME/MetaAutomate-P2-064-Review"
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_p2_064_interactive_universal_workspace.py tests/test_p2_063_domain_packs.py tests/test_p2_062_unified_workspace_ui.py
node --check apps/site/assets/unified-workspace.js
python3 scripts/verify_unified_workspace_browser.py
python3 -m http.server 8878 --bind 127.0.0.1 --directory apps/site
```

Browser URL (only if local HTTP server starts): `http://127.0.0.1:8878/workspace/`.

**Release boundary:** PR #132 and founder verification worktree stay unchanged. This change is stacked on draft #133. No production deploy, release gate bypass, live customer integrations, payments, outreach or resumed automation. Once foundation, branch protections and independent security gates are accepted, a separate authorized release can promote reviewed code to the public website.
