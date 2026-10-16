"""P2-03y — pinned RS256 OIDC ID-token *verification primitive* for private staging.

The verifier does not contact an identity provider, complete authorization-code
+ PKCE login, protect the browser session, issue role grants, or enroll MFA.
Keys, expected session nonce and member roster must come from independently
authorized staging infrastructure. It deliberately has NO default trust roots,
membership list, JWT issuer or network discovery path.

Passing a synthetic signed token is NOT proof of a real staff login.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import hashes

from .synthetic_growth_autopilot import SyntheticGrowthError

MAX_JWT_BYTES = 8192
MAX_CLAIMS_BYTES = 4096
MAX_JWKS_BYTES = 16384
B64 = re.compile(r"[A-Za-z0-9_-]+\Z")
ID_CLAIMS = frozenset({
    "iss", "aud", "sub", "exp", "iat", "nbf", "auth_time", "nonce", "amr"
})
ROLES = frozenset({"owner", "security_reviewer", "auditor"})
ALLOWED_WORKSPACES = frozenset({"academy_demo", "bespoke_demo"})


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SyntheticGrowthError(message)


def object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for k, v in pairs:
        require(k not in result, "Duplicate ID token or JWKS JSON field")
        result[k] = v
    return result


def refuse_floats(_):
    raise SyntheticGrowthError("Fractional/nonfinite JWT JSON not supported")


def json_data(raw: bytes, *, limit: int) -> dict:
    require(type(raw) is bytes and 0 < len(raw) <= limit and b"\x00" not in raw,
            "Invalid bounded JSON")
    try:
        parsed = json.loads(raw.decode("utf-8"),
                            object_pairs_hook=object_no_duplicates,
                            parse_float=refuse_floats,
                            parse_constant=refuse_floats)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed signed JWT or pinned key") from exc
    require(type(parsed) is dict, "JWT data must be a JSON object")
    return parsed


def decode(part: str, max_encoded: int) -> bytes:
    require(type(part) is str and 0 < len(part) <= max_encoded
            and B64.fullmatch(part) is not None,
            "Noncanonical JWT encoding")
    try:
        raw = base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise SyntheticGrowthError("Invalid base64url segment") from exc
    require(base64.urlsafe_b64encode(raw).rstrip(b"=").decode() == part,
            "Noncanonical JWT base64url")
    return raw


def require_https_url(text: str, *, may_have_path: bool) -> str:
    require(type(text) is str and 12 <= len(text) <= 230,
            "Missing or oversized trusted HTTPS URL")
    try:
        url = urlsplit(text)
        host = url.hostname
        port = url.port
    except ValueError as exc:
        raise SyntheticGrowthError("Malformed HTTPS authority") from exc
    require(url.scheme == "https" and url.username is None
            and url.password is None and url.query == ""
            and url.fragment == "" and port in (None, 443)
            and type(host) is str and "." in host and
            host not in {"localhost", "127.0.0.1"} and
            not host.endswith((".invalid", ".local", ".test")) and
            (may_have_path or url.path in ("", "/")),
            "Real staging requires explicit nonlocal HTTPS endpoints")
    return host


@dataclass(frozen=True)
class OidcStagingConfig:
    issuer: str
    audience: str
    jwks_uri: str
    private_origin: str
    callback_uri: str

    def __post_init__(self) -> None:
        issuer_host = require_https_url(self.issuer, may_have_path=True)
        jwks_host = require_https_url(self.jwks_uri, may_have_path=True)
        require(issuer_host == jwks_host,
                "JWKS must be pinned to the approved issuer host")
        origin_host = require_https_url(self.private_origin, may_have_path=False)
        cb_host = require_https_url(self.callback_uri, may_have_path=True)
        require(origin_host == cb_host
                and self.callback_uri == self.private_origin.rstrip("/") + "/auth/callback",
                "OIDC callback must exactly match approved private origin")
        require(type(self.audience) is str and
                5 <= len(self.audience) <= 120 and
                re.fullmatch(r"[a-zA-Z0-9:_./-]+",self.audience) is not None,
                "Invalid dedicated application audience")
        require(self.issuer.startswith("https://")
                and self.issuer.rstrip("/") not in
                {"https://example.com","https://localhost"},
                "Dedicated issuer required")


@dataclass(frozen=True)
class IdentityProof:
    subject: str
    workspace: str
    role: str
    verified_signature: bool
    nonce_matches_session: bool
    pinned_signing_key: bool
    local_membership_checked: bool
    production_login_completed: bool = False
    live_mfa_challenge_verified: bool = False
    independent_membership_verified: bool = False
    live_idp_network_contact: bool = False


class PinnedOidcTokenVerifier:
    """RSA ID-token checks, with independently supplied nonce, JWKS and roster."""

    def __init__(self, config: OidcStagingConfig, *,
                 jwks_raw: bytes, trusted_thumbprints: frozenset[str],
                 tenant_roster: dict[str, dict[str,str]],
                 revoked_subs: frozenset[str] = frozenset(),
                 revoked_kids: frozenset[str] = frozenset()):
        require(isinstance(config,OidcStagingConfig), "OIDC policy required")
        require(type(jwks_raw) is bytes and len(jwks_raw) <= MAX_JWKS_BYTES,
                "Bounded pinned issuer keys only")
        doc = json_data(jwks_raw,limit=MAX_JWKS_BYTES)
        require(set(doc)=={"keys"} and type(doc["keys"]) is list
                and 1 <= len(doc["keys"]) <= 6,
                "Unexpected or oversized pinned JWKS")
        require(type(trusted_thumbprints) is frozenset
                and 1 <= len(trusted_thumbprints) <= 6
                and all(type(x) is str and
                        re.fullmatch(r"[0-9a-f]{64}",x) is not None
                        for x in trusted_thumbprints),
                "Out-of-band pinned key fingerprints required")
        self.config = config
        self.keys = {}
        for key in doc["keys"]:
            require(type(key) is dict
                    and set(key)=={"kty","kid","alg","use","n","e"}
                    and key["kty"]=="RSA" and key["alg"]=="RS256"
                    and key["use"]=="sig" and
                    type(key["kid"]) is str and
                    re.fullmatch(r"[A-Za-z0-9_-]{3,80}",key["kid"]) is not None
                    and key["kid"] not in self.keys,
                    "Only unique pinned RSA signing keys allowed")
            public_doc={"e":key["e"],"kty":"RSA","n":key["n"]}
            thumbprint=sha256(json.dumps(
                public_doc,sort_keys=True,separators=(",",":")
            ).encode("ascii")).hexdigest()
            require(thumbprint in trusted_thumbprints,
                    "Unapproved or rotated issuer signing key")
            n=int.from_bytes(decode(key["n"],900),"big")
            e=int.from_bytes(decode(key["e"],16),"big")
            require(n.bit_length()>=2048 and n.bit_length()<=4096
                    and e==65537,
                    "Weak or malformed RSA signing material")
            try:
                self.keys[key["kid"]]=rsa.RSAPublicNumbers(e,n).public_key()
            except ValueError as exc:
                raise SyntheticGrowthError("Invalid pinned RSA public key") from exc
        require(type(tenant_roster) is dict and 1 <= len(tenant_roster) <= 50,
                "Independent tenant membership roster required")
        self.roster={}
        for subject,assignment in tenant_roster.items():
            require(type(subject) is str and 4<=len(subject)<=180
                    and type(assignment) is dict
                    and set(assignment)=={"workspace","role"}
                    and assignment["workspace"] in ALLOWED_WORKSPACES
                    and assignment["role"] in ROLES,
                    "Invalid explicit membership mapping")
            self.roster[subject]=dict(assignment)
        self.revoked_subs=frozenset(revoked_subs)
        self.revoked_kids=frozenset(revoked_kids)

    def verify(self, id_token: str, *, expected_nonce: str, now: int) -> IdentityProof:
        require(type(id_token) is str and 0<len(id_token)<=MAX_JWT_BYTES
                and type(expected_nonce) is str and
                re.fullmatch(r"[A-Za-z0-9_-]{24,120}",expected_nonce) is not None
                and type(now) is int and now>=0,
                "Session-bound nonce and explicit clock required")
        parts = id_token.split(".")
        require(len(parts)==3, "Three signed ID token segments required")
        header=json_data(decode(parts[0],650),limit=420)
        require(set(header)=={"alg","kid","typ"}
                and header["alg"]=="RS256" and header["typ"]=="JWT",
                "Reject algorithm confusion, JKU and unapproved JWT headers")
        kid=header["kid"]
        require(type(kid) is str and kid in self.keys
                and kid not in self.revoked_kids,
                "Unknown or revoked signing key")
        signature=decode(parts[2],750)
        try:
            self.keys[kid].verify(
                signature,(parts[0]+"."+parts[1]).encode("ascii"),
                padding.PKCS1v15(),hashes.SHA256())
        except InvalidSignature as exc:
            raise SyntheticGrowthError("Untrusted issuer signature") from exc
        claims=json_data(decode(parts[1],MAX_CLAIMS_BYTES*2),
                         limit=MAX_CLAIMS_BYTES)
        require(set(claims)==ID_CLAIMS,
                "Unreviewed token claims or missing session proof")
        require(claims["iss"]==self.config.issuer
                and claims["aud"]==self.config.audience,
                "Wrong issuer or audience")
        sub=claims["sub"]
        require(type(sub) is str and sub in self.roster
                and sub not in self.revoked_subs,
                "Missing or revoked independent membership")
        require(claims["nonce"]==expected_nonce,
                "Missing session nonce binding")
        iat, nbf, exp, auth_time = (
            claims["iat"], claims["nbf"], claims["exp"], claims["auth_time"])
        require(all(type(x) is int for x in (iat,nbf,exp,auth_time))
                and 0 <= auth_time <= iat <= now+30
                and nbf <= now and now < exp
                and 0 < exp-iat <= 300
                and now-auth_time <= 300,
                "Expired/stale/future issuer authentication claims")
        amr=claims["amr"]
        require(type(amr) is list and len(amr)<=5
                and all(type(x) is str and len(x)<35 for x in amr)
                and "mfa" in amr,
                "Expected signed MFA assertion absent")
        m=self.roster[sub]
        return IdentityProof(
            subject=sub,workspace=m["workspace"],role=m["role"],
            verified_signature=True,nonce_matches_session=True,
            pinned_signing_key=True,local_membership_checked=True,
        )
