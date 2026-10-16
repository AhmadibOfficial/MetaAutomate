"""P2-03w: offline *simulated* OIDC JWT verification and team membership gate.

NO live OIDC discovery, real employee authentication, MFA enrollment, JWKS
fetch, customer identity, OAuth token exchange, production credentials or IdP
provisioning. Separate CI-generated keys test trust logic only.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
import time
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .disposable_crm_authorization import VerifiedActor
from .synthetic_growth_autopilot import SyntheticGrowthError

ISSUER = "https://offline-idp.metaautomate.invalid/"
AUDIENCE = "metaautomate-private-stage-example"
MAX_TOKEN = 4096
SUB_RE = re.compile(r"SIM-SUB-[A-Z0-9-]{3,40}\Z")
JTI_RE = re.compile(r"SIM-JTI-[A-Z0-9-]{3,40}\Z")
KEY_RE = re.compile(r"ci-key-[a-z0-9-]{2,30}\Z")
ENC_RE = re.compile(r"[A-Za-z0-9_-]+\Z")
CLAIMS = frozenset({"iss","aud","sub","iat","nbf","exp","auth_time","jti",
                    "workspace","role","amr"})
HEADERS = frozenset({"typ","alg","kid"})
ROLE_MAP = {"owner":"tenant_admin","security_reviewer":"reviewer","auditor":"auditor"}


def need(condition: bool, detail: str):
    if not condition:
        raise SyntheticGrowthError(detail)


def no_duplicates(pairs):
    out={}
    for key,value in pairs:
        need(key not in out,"Duplicate signed identity field")
        out[key]=value
    return out


def no_floats(_):
    raise SyntheticGrowthError("Nonintegral or nonfinite signed identity claim")


def decode(segment: str, maximum: int) -> bytes:
    need(type(segment) is str and 0<len(segment)<=maximum and
         ENC_RE.fullmatch(segment) is not None,"Invalid JWT encoding")
    try:
        raw=base64.urlsafe_b64decode(segment+"="*(-len(segment)%4))
    except (ValueError,base64.binascii.Error) as exc:
        raise SyntheticGrowthError("Invalid signed identity encoding") from exc
    need(base64.urlsafe_b64encode(raw).rstrip(b"=").decode()==segment,
         "Noncanonical JWT encoding")
    return raw


def json_claims(raw: bytes, limit: int) -> dict:
    need(type(raw) is bytes and 0<len(raw)<=limit and b"\x00" not in raw,
         "Invalid JWT component size")
    try:
        doc=json.loads(raw.decode("utf-8"),object_pairs_hook=no_duplicates,
                       parse_float=no_floats,parse_constant=no_floats)
    except SyntheticGrowthError: raise
    except (ValueError,UnicodeDecodeError,RecursionError) as exc:
        raise SyntheticGrowthError("Malformed JWT document") from exc
    need(type(doc) is dict,"JWT document must be an object")
    return doc


@dataclass(frozen=True)
class OfflineIdentity:
    subject: str
    workspace: str
    role: str
    actor_ref: str
    token_ref: str
    expiry: int
    key_id: str
    mfa_asserted_in_test: bool = True
    real_idp_verified: bool = False


class OfflineIdentityTrust:
    """Explicit pinned CI JWKS and memberships; never resolves keys by URL."""
    def __init__(self, *, keys: Mapping[str, Ed25519PublicKey],
                 memberships: Mapping[str, dict],
                 revoked_jtis: frozenset[str]=frozenset(),
                 revoked_kids: frozenset[str]=frozenset()):
        need(type(keys) is dict and 1<=len(keys)<=4, "Pinned CI keys required")
        for kid,key in keys.items():
            need(type(kid) is str and KEY_RE.fullmatch(kid) is not None
                 and isinstance(key,Ed25519PublicKey),
                 "Invalid pinned CI signing key")
        need(type(memberships) is dict and 1<=len(memberships)<=30,
             "Limited trusted CI membership directory required")
        for sub,m in memberships.items():
            need(type(sub) is str and SUB_RE.fullmatch(sub) is not None
                 and type(m) is dict and set(m)=={"workspace","role","actor_ref"}
                 and m["workspace"] in ("academy_demo","bespoke_demo")
                 and m["role"] in ROLE_MAP
                 and type(m["actor_ref"]) is str
                 and re.fullmatch(r"SIM-ACTOR-[A-Z0-9-]{2,40}",m["actor_ref"]) is not None,
                 "Untrusted local CI membership")
        self.keys=dict(keys);self.memberships={k:dict(v) for k,v in memberships.items()}
        self.revoked_jtis=frozenset(revoked_jtis)
        self.revoked_kids=frozenset(revoked_kids)

    def verify(self, token: str, *, now: int | None=None) -> OfflineIdentity:
        need(type(token) is str and 0<len(token)<=MAX_TOKEN,
             "Invalid bounded identity assertion")
        parts=token.split(".")
        need(len(parts)==3, "Expected three part signed JWT")
        header=json_claims(decode(parts[0],360),256)
        need(set(header)==HEADERS and header["typ"]=="JWT"
             and header["alg"]=="EdDSA", "Unapproved JWT header or algorithm")
        kid=header["kid"]
        need(type(kid) is str and kid in self.keys and kid not in self.revoked_kids,
             "Unknown or revoked issuer key")
        sig=decode(parts[2],110)
        need(len(sig)==64,"Invalid signature length")
        try:
            self.keys[kid].verify(sig,(parts[0]+"."+parts[1]).encode("ascii"))
        except InvalidSignature as exc:
            raise SyntheticGrowthError("Untrusted IdP signature") from exc
        claims=json_claims(decode(parts[1],3000),2048)
        need(set(claims)==CLAIMS,"Unrecognized or missing OIDC identity claim")
        need(claims["iss"]==ISSUER and claims["aud"]==AUDIENCE,
             "Wrong issuer or audience")
        now=int(time.time()) if now is None else now
        need(type(now) is int and now>=0,"Invalid clock")
        iat,nbf,exp,auth_time=(
            claims["iat"],claims["nbf"],claims["exp"],claims["auth_time"])
        need(all(type(x) is int for x in (iat,nbf,exp,auth_time))
             and 0<=auth_time<=iat<=now+30 and nbf<=now
             and exp>now and 0<exp-iat<=300 and now-auth_time<=600,
             "Invalid session lifetime, freshness or MFA event")
        sub,jti=claims["sub"],claims["jti"]
        need(type(sub) is str and sub in self.memberships
             and type(jti) is str and JTI_RE.fullmatch(jti) is not None
             and jti not in self.revoked_jtis, "Unknown or revoked identity")
        m=self.memberships[sub]
        need(type(claims["workspace"]) is str and
             claims["workspace"]==m["workspace"]
             and type(claims["role"]) is str and claims["role"]==m["role"],
             "Provider claims do not match independently assigned membership")
        amr=claims["amr"]
        need(type(amr) is list and len(amr)==2 and set(amr)=={"pwd","mfa"}
             and all(type(x) is str for x in amr),
             "Test assertion must include phishing-resistant policy placeholder")
        # AMR alone is NOT proof that an actual account has MFA.
        return OfflineIdentity(sub,m["workspace"],m["role"],m["actor_ref"],jti,exp,kid)

    def with_revocation(self, *, jti: str | None=None,
                        kid: str | None=None) -> "OfflineIdentityTrust":
        need(jti is not None or kid is not None, "Revocation target required")
        if jti is not None:
            need(type(jti) is str and JTI_RE.fullmatch(jti) is not None,
                 "Invalid revoked token reference")
        if kid is not None:
            need(type(kid) is str and kid in self.keys,"Invalid revoked key reference")
        return OfflineIdentityTrust(
            keys=self.keys,memberships=self.memberships,
            revoked_jtis=self.revoked_jtis | ({jti} if jti else set()),
            revoked_kids=self.revoked_kids | ({kid} if kid else set()))


def require_dual_identity(identity: OfflineIdentity, actor: VerifiedActor):
    """Bridge independently test-signed JWT into existing app-signed actor role."""
    need(isinstance(identity,OfflineIdentity)
         and isinstance(actor,VerifiedActor),"Both verified contexts required")
    need(identity.workspace==actor.workspace
         and identity.actor_ref==actor.actor_ref
         and ROLE_MAP[identity.role]==actor.role,
         "Identity-provider and application actor mismatch")
    need(identity.real_idp_verified is False,
         "This test-only bridge cannot claim real production identity")
    return {"workspace":identity.workspace,"actor":identity.actor_ref,
            "role":actor.role,"dual_signature_verified_in_ci":True,
            "production_identity_verified":False}
