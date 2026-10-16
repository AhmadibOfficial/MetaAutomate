"""A private OIDC session must carry recent, signed MFA evidence.

These tests only exercise a claim validation function with synthetic tokens.
They do not assert a real IdP is connected, nor that Authlib/JWKS was exercised.
"""
import sys
from pathlib import Path
import pytest
from fastapi import HTTPException

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.workspace_auth import require_recent_oidc_mfa

NOW=2_000_000_000

def test_valid_recent_mfa_claim_passes_only_claim_filter():
    assert require_recent_oidc_mfa(
        {"amr":["pwd","mfa"],"auth_time":NOW-120},now=NOW,
    ) is None
    assert require_recent_oidc_mfa(
        {"amr":["mfa"],"auth_time":NOW-900},now=NOW,
    ) is None


@pytest.mark.parametrize("claims",[
    {},
    {"amr":["pwd"],"auth_time":NOW-30},
    {"amr":["otp"],"auth_time":NOW-30},
    {"amr":[],"auth_time":NOW-30},
    {"amr":"mfa","auth_time":NOW-30},
    {"amr":["mfa"],"auth_time":NOW-901},
    {"amr":["mfa"],"auth_time":NOW+61},
    {"amr":["mfa"],"auth_time":True},
    {"amr":["mfa"],"auth_time":"2000000000"},
    {"amr":["mfa"],"auth_time":0},
    {"amr":[None,"mfa"],"auth_time":NOW-1},
    {"amr":["MFA"],"auth_time":NOW-1},
])
def test_password_only_expired_future_or_forged_claim_is_denied(claims):
    with pytest.raises(HTTPException) as exc:
        require_recent_oidc_mfa(claims,now=NOW)
    assert exc.value.status_code==401


def test_oidc_callback_requests_and_checks_recent_signed_mfa():
    code=(ROOT/"apps/api/app/workspace_auth.py").read_text()
    assert "max_age=900" in code
    assert "require_recent_oidc_mfa(userinfo)" in code
    assert code.index("require_recent_oidc_mfa(userinfo)") < code.index(
        "app.create_oidc_workspace_session",
    )
    assert 'if (not tokens.get("id_token")' in code
    assert 'tokens.get("userinfo") or {}' in code
