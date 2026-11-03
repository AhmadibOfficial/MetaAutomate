"""Source-only regression tests for AI coding confidentiality safeguards."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "security"))
import guard
import check_changed_source as scanner
import dependency_review

class TestSecurityControls(unittest.TestCase):
    def test_sensitive_paths_and_safe_templates(self):
        bad = (
            ".env", ".env.production", "apps/api/.env", "apps/api/.env.local",
            "secrets/secret.txt", "apps/api/credentials/cloud.json",
            "project/.aws/credentials", "assets/key.pem", "config/auth.key",
            "id_ed25519", "infra/site.tfstate.backup",
            "service-account-prod.json", "apps/frontend/.npmrc",
            "apps/ios/GoogleService-Info.plist", ".claude/settings.local.json",
        )
        safe = (
            ".env.example", "apps/api/.env.sample", ".env.template",
            "apps/api/app/main.py", ".claude/settings.json",
        )
        for value in bad:
            with self.subTest(value=value):
                self.assertTrue(guard.sensitive(value))
        for value in safe:
            with self.subTest(value=value):
                self.assertFalse(guard.sensitive(value))

    def test_claude_settings_require_approval_and_exclude_secrets(self):
        data = json.loads((ROOT / ".claude/settings.json").read_text("utf-8"))
        deny = data["permissions"]["deny"]
        self.assertIn("Read(./.env)", deny)
        self.assertIn("Read(./**/.env.*)", deny)
        self.assertIn("Bash(git push *)", deny)
        self.assertIn("Bash(git merge *)", deny)
        self.assertIn("Bash(*)", data["permissions"]["ask"])
        self.assertEqual("default", data["permissions"]["defaultMode"])
        self.assertTrue(data["sandbox"]["enabled"])

    def test_js_scan_catches_high_confidence_issues(self):
        for source in ("eval(userText)", "new Function(source)",
                       "node.innerHTML = value", "document.write(untrusted)"):
            self.assertTrue(any(rule.search(source) for _, rule in scanner.JS_BAD), source)
        self.assertFalse(any(rule.search("node.textContent = safe") for _, rule in scanner.JS_BAD))

    def test_dependency_identity_and_external_index_rejection(self):
        self.assertEqual(
            dependency_review.canonical("HTTPX2"),
            "httpx2",
        )
        for value in ("-i https://bad.example", "git+https://example.org/source.git",
                      "untrusted @ https://example.org/a.whl"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    dependency_review.parse_names([value])
        manifest = json.loads((ROOT / "docs/security/approved-api-python-packages.json").read_text("utf-8"))
        self.assertIn("httpx2", manifest["packages"])
        self.assertEqual(manifest["status"], "PACKAGE_IDENTITIES_REVIEWED_NOT_FULLY_VERSION_LOCKED")

    def test_ci_and_hooks_are_fail_closed(self):
        ci = (ROOT / ".github/workflows/security-ai-assisted.yml").read_text("utf-8")
        local = (ROOT / ".pre-commit-config.yaml").read_text("utf-8")
        self.assertIn("gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e", ci)
        self.assertIn("bandit==1.9.4", ci)
        self.assertIn("pull_request:", ci)
        self.assertIn("guard.py --tracked", ci)
        self.assertIn("check_changed_source.py", ci)
        self.assertIn("gitleaks git --staged --redact", local)
        self.assertIn("guard.py --staged", local)
        self.assertNotIn("continue-on-error", ci)
        self.assertIn("@AhmadibOfficial", (ROOT / ".github/CODEOWNERS").read_text("utf-8"))

    def test_contract_explains_actual_release_boundary(self):
        text = (ROOT / "docs/security/AI_ASSISTED_DEVELOPMENT.md").read_text("utf-8").lower()
        for keyword in ("no-go", "manual review", "not enforced", "branch protection",
                        "provider agreement", "codex", "claude", "static"):
            self.assertIn(keyword, text)
        render = (ROOT / "render.yaml").read_text("utf-8")
        self.assertIn("autoDeployTrigger: 'off'", render)
        self.assertIn("staticPublishPath: ./apps/site", render)

if __name__ == "__main__":
    unittest.main()
