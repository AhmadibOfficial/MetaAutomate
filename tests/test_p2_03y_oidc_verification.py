"""P2-03y: future OIDC verifier negative trust cases (CI-generated RSA only)."""
from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.p2_03y_oidc_verification import (
    OidcStagingConfig,PinnedOidcTokenVerifier,IdentityProof,decode,
    require_https_url,
)

NOW=1800000000
NONCE="Staging_Nonce_1234567890abcdefghijkl"
ISSUER="https://login.example.org/tenant"
ORIGIN="https://private.example.org"


def b64(data:bytes)->str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_signed(key,claims,head=None):
    h=head if head is not None else {"typ":"JWT","alg":"RS256","kid":"staging-kid-1"}
    header=b64(json.dumps(h,sort_keys=True,separators=(",",":")).encode())
    payload=b64(json.dumps(claims,sort_keys=True,separators=(",",":")).encode())
    plain=header+"."+payload
    sig=key.sign(plain.encode("ascii"),padding.PKCS1v15(),hashes.SHA256())
    return plain+"."+b64(sig)


@pytest.fixture(scope="module")
def trust():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    p=key.public_key().public_numbers()
    entry={"kty":"RSA","kid":"staging-kid-1","alg":"RS256","use":"sig",
           "n":b64(p.n.to_bytes((p.n.bit_length()+7)//8,"big")),
           "e":b64(p.e.to_bytes((p.e.bit_length()+7)//8,"big"))}
    public_doc={"e":entry["e"],"kty":"RSA","n":entry["n"]}
    thumbprint=__import__("hashlib").sha256(json.dumps(
        public_doc,sort_keys=True,separators=(",",":")
    ).encode()).hexdigest()
    config=OidcStagingConfig(issuer=ISSUER,audience="private-stage-workbench",
               jwks_uri=ISSUER+"/.well-known/jwks.json",
               private_origin=ORIGIN,callback_uri=ORIGIN+"/auth/callback")
    roster={
        "test-staff-one":{"workspace":"academy_demo","role":"owner"},
        "test-staff-two":{"workspace":"academy_demo","role":"security_reviewer"},
    }
    source=json.dumps({"keys":[entry]}).encode()
    verifier=PinnedOidcTokenVerifier(config,jwks_raw=source,
             trusted_thumbprints=frozenset({thumbprint}),
             tenant_roster=roster)
    claims={
        "iss":ISSUER,"aud":"private-stage-workbench",
        "sub":"test-staff-one","exp":NOW+180,"iat":NOW-20,
        "nbf":NOW-20,"auth_time":NOW-60,"nonce":NONCE,"amr":["pwd","mfa"],
    }
    return key,config,entry,thumbprint,roster,source,verifier,claims


def test_ci_generated_id_token_validates_signature_nonce_freshness(trust):
    private,config,entry,thumbprint,roster,source,verifier,claims=trust
    token=make_signed(private,claims)
    actual=verifier.verify(token,expected_nonce=NONCE,now=NOW)
    assert isinstance(actual,IdentityProof)
    assert actual.subject=="test-staff-one" and actual.role=="owner"
    assert actual.workspace=="academy_demo"
    assert actual.pinned_signing_key and actual.verified_signature
    assert actual.nonce_matches_session and actual.local_membership_checked
    assert not actual.production_login_completed
    assert not actual.live_mfa_challenge_verified
    assert not actual.independent_membership_verified
    assert not actual.live_idp_network_contact


@pytest.mark.parametrize("change",[
    {"iss":"https://attacker.example.org"},
    {"aud":"different-api"},
    {"sub":"unknown-person"},
    {"nonce":"Bad_nonce_12345678901234567890123"},
    {"amr":["pwd"]},
    {"amr":["mfa",True]},
    {"iat":NOW+100},
    {"nbf":NOW+200},
    {"auth_time":NOW-9999},
    {"exp":NOW-1},
    {"exp":NOW+999},
    {"exp":True},
    {"iat":NOW-20.5},
    {"workspace":"bespoke_demo"},
    {"role":"tenant_admin"},
    {"email":"personal@example.org"},
    {"jku":"https://attacker.example.org/jwks.json"},
])
def test_unexpected_or_stale_claim_denied(trust,change):
    private,_,_,_,_,_,verifier,claims=trust
    modified={**claims,**change}
    with pytest.raises(SyntheticGrowthError):
        verifier.verify(make_signed(private,modified),expected_nonce=NONCE,now=NOW)


@pytest.mark.parametrize("header",[
    {"typ":"JWT","alg":"none","kid":"staging-kid-1"},
    {"typ":"JWT","alg":"HS256","kid":"staging-kid-1"},
    {"typ":"JWT","alg":"RS256","kid":"fake-kid"},
    {"typ":"JWE","alg":"RS256","kid":"staging-kid-1"},
    {"typ":"JWT","alg":"RS256","kid":"staging-kid-1",
     "jku":"https://attacker.example.org"},
])
def test_alg_and_remote_jwks_header_denied(trust,header):
    private,_,_,_,_,_,verifier,claims=trust
    with pytest.raises(SyntheticGrowthError):
        verifier.verify(make_signed(private,claims,header),
                        expected_nonce=NONCE,now=NOW)


def test_different_signer_invalid_and_key_revoked(trust):
    private,config,entry,pin,roster,raw,verifier,claims=trust
    malicious=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    with pytest.raises(SyntheticGrowthError,match="signature"):
        verifier.verify(make_signed(malicious,claims),expected_nonce=NONCE,now=NOW)
    revoked= PinnedOidcTokenVerifier(config,jwks_raw=raw,
        trusted_thumbprints=frozenset({pin}),tenant_roster=roster,
        revoked_kids=frozenset({"staging-kid-1"}))
    with pytest.raises(SyntheticGrowthError,match="revoked"):
        revoked.verify(make_signed(private,claims),expected_nonce=NONCE,now=NOW)


def test_pinned_key_and_static_membership_both_required(trust):
    key,config,entry,pin,roster,raw,verifier,claims=trust
    with pytest.raises(SyntheticGrowthError,match="Unapproved or rotated"):
        PinnedOidcTokenVerifier(config,jwks_raw=raw,
            trusted_thumbprints=frozenset({"f"*64}),tenant_roster=roster)
    revoked= PinnedOidcTokenVerifier(config,jwks_raw=raw,
        trusted_thumbprints=frozenset({pin}),tenant_roster=roster,
        revoked_subs=frozenset({"test-staff-one"}))
    with pytest.raises(SyntheticGrowthError):
        revoked.verify(make_signed(key,claims),expected_nonce=NONCE,now=NOW)
    unauthorized={**roster,"test-staff-one":{"workspace":"bespoke_demo","role":"auditor"}}
    changed=PinnedOidcTokenVerifier(config,jwks_raw=raw,
        trusted_thumbprints=frozenset({pin}),tenant_roster=unauthorized)
    role=changed.verify(make_signed(key,claims),expected_nonce=NONCE,now=NOW)
    assert role.workspace=="bespoke_demo" and role.role=="auditor"
    assert role.independent_membership_verified is False


@pytest.mark.parametrize("url",[
    "http://login.example.org","https://localhost",
    "https://idp.example.invalid","https://user:password@idp.example.org",
    "https://idp.example.org:8080","https://idp.example.org#redirect",
])
def test_insecure_oidc_origins_rejected(url):
    with pytest.raises(SyntheticGrowthError):
        OidcStagingConfig(issuer=url,audience="private-stage-workbench",
            jwks_uri=ISSUER+"/jwks",private_origin=ORIGIN,
            callback_uri=ORIGIN+"/auth/callback")


def test_redirect_and_jwks_can_not_be_swapped(trust):
    _,config,*_=trust
    with pytest.raises(SyntheticGrowthError):
        OidcStagingConfig(issuer=ISSUER,audience="private-stage-workbench",
            jwks_uri="https://evil.example.org/jwks",private_origin=ORIGIN,
            callback_uri=ORIGIN+"/auth/callback")
    with pytest.raises(SyntheticGrowthError):
        OidcStagingConfig(issuer=ISSUER,audience="private-stage-workbench",
            jwks_uri=ISSUER+"/jwks",private_origin=ORIGIN,
            callback_uri="https://public.example.org/auth/callback")


@pytest.mark.parametrize("bad",[
    "",None,"only.two","a..c", "A"*8193,
])
def test_malformed_or_oversized_jwt_rejected(trust,bad):
    _,_,_,_,_,_,verifier,_=trust
    with pytest.raises(SyntheticGrowthError):
        verifier.verify(bad,expected_nonce=NONCE,now=NOW)


def test_untrusted_app_nonce_cannot_skip_replay_check(trust):
    key,_,_,_,_,_,verifier,claims=trust
    valid=make_signed(key,claims)
    with pytest.raises(SyntheticGrowthError):
        verifier.verify(valid,expected_nonce="random_other_nonce_1234567890123",now=NOW)
    with pytest.raises(SyntheticGrowthError):
        verifier.verify(valid,expected_nonce="short",now=NOW)
