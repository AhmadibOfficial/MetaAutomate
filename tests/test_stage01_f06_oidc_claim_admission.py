"""Stage 01 / F06: synthetic OIDC claim-shape rejection before session creation.

No real identity provider, network, live database, user data or migration.
These tests do not replace Authlib's signature/JWKS/PKCE/nonce verification.
"""
from __future__ import annotations

import asyncio
from collections import UserDict
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app import workspace_auth

ISSUER = "https://identity.example.test/realm"
VALID = {"iss": ISSUER, "sub": "tenant|staff-1",
         "auth_time": 2_000_000_000, "amr": ["pwd", "mfa"]}


def _fake_oidc(monkeypatch, token_response):
    """Exercise the actual callback using a fake token response, no DB calls."""
    class Provider:
        async def authorize_access_token(self, request):
            return token_response

    class OAuth:
        def create_client(self, name):
            assert name == "meta_idp"
            return Provider()

    monkeypatch.setattr(workspace_auth, "auth_mode", lambda: "oidc")
    monkeypatch.setattr(workspace_auth, "oauth", OAuth())
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)

    def forbidden_db_connection():
        pytest.fail("Invalid or stale identity must not open a DB session")
    monkeypatch.setattr(workspace_auth, "_connection", forbidden_db_connection)


@pytest.mark.parametrize("userinfo", [
    {"iss": ISSUER, "sub": None},
    {"iss": ISSUER, "sub": True},
    {"iss": ISSUER, "sub": 123},
    {"iss": ISSUER, "sub": {"sub": "tenant|staff-1"}},
    {"iss": ISSUER, "sub": ["tenant|staff-1"]},
    {"iss": ISSUER, "sub": ""},
    {"iss": ISSUER, "sub": " "},
    {"iss": ISSUER, "sub": "abc\nxyz"},
    {"iss": ISSUER, "sub": "nonascii-é"},
    {"iss": ISSUER, "sub": "x" * 256},
    {"iss": True, "sub": "tenant|staff-1"},
    {"iss": [ISSUER], "sub": "tenant|staff-1"},
    {"iss": "https://other.example.test", "sub": "tenant|staff-1"},
    ["unexpected", "array"],
    "unexpected string",
])
def test_bad_claim_shapes_rejected_before_db(monkeypatch, userinfo):
    _fake_oidc(monkeypatch, {"id_token": "synthetic-not-a-real-jwt",
                            "userinfo": userinfo})
    with pytest.raises(HTTPException) as captured:
        asyncio.run(workspace_auth.oidc_callback(None))
    assert captured.value.status_code == 401
    assert captured.value.detail == "Verified OIDC identity required"


@pytest.mark.parametrize("id_token", [None, "", True, 99, []])
def test_missing_or_nonstring_id_token_rejected(monkeypatch, id_token):
    _fake_oidc(monkeypatch, {"id_token": id_token, "userinfo": VALID})
    with pytest.raises(HTTPException) as captured:
        asyncio.run(workspace_auth.oidc_callback(None))
    assert captured.value.status_code == 401
    assert captured.value.detail == "Verified OIDC identity required"


def test_mapping_claims_pass_shape_filter_then_reach_existing_mfa_guard(monkeypatch):
    """A dict-compatible Authlib UserInfo is not rejected for being a mapping."""
    fake = UserDict({**VALID, "amr": ["pwd"]})
    _fake_oidc(monkeypatch, {"id_token": "synthetic-not-a-real-jwt",
                            "userinfo": fake})
    with pytest.raises(HTTPException) as captured:
        asyncio.run(workspace_auth.oidc_callback(None))
    assert captured.value.status_code == 401
    assert captured.value.detail == "Recent verified multifactor authentication required"


def test_f06_remains_source_only_and_does_not_weaken_release_gate():
    source = (ROOT / "apps/api/app/workspace_auth.py").read_text()
    assert "require_recent_oidc_mfa(userinfo)" in source
    assert source.index("not subject.isascii()") < source.index(
        "require_recent_oidc_mfa(userinfo)")
    assert source.index("require_recent_oidc_mfa(userinfo)") < source.index(
        "app.create_oidc_workspace_session")
    assert 'if auth_mode() != "oidc"' in source
