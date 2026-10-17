"""P2-04q: sequential, three-party offline approval packet signing.

The code cannot establish a person's real identity, legal rights, or genuine
review. Trusted public keys must be registered OUTSIDE the project.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import stat

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

from app.creative_audio_assets import AudioAssetHold, canonical
from app.creative_speech_authorization import _FIELDS, _utc, _b64

ROLES=("OWNER","REVIEWER_1","REVIEWER_2")
REVIEW_FIELDS=("licence_human_reviewed","rights_human_reviewed",
               "consent_human_reviewed","isolated_execution_required")

def _private_signing_key(path:Path)->Ed25519PrivateKey:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve()!=path or not 0<path.stat().st_size<=8192
        or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise AudioAssetHold("Private reviewer key file (0600) required")
    try:
        key=serialization.load_pem_private_key(path.read_bytes(),password=None)
    except (ValueError,TypeError) as exc:
        raise AudioAssetHold("Cannot read private Ed25519 reviewer key") from exc
    if not isinstance(key,Ed25519PrivateKey):
        raise AudioAssetHold("Only Ed25519 keys are allowed")
    return key

def sign_next(packet:dict, *, role:str, key_path:Path,
              trusted_public_keys:dict, now:datetime|None=None)->dict:
    """One signatory at a time; never creates or approves a review itself."""
    if (type(packet) is not dict or set(packet)!=_FIELDS
        or type(packet.get("signatures")) is not list):
        raise AudioAssetHold("Exact unsigned/partially signed packet required")
    signatures=packet["signatures"]
    if (len(signatures)>=len(ROLES) or role!=ROLES[len(signatures)]
        or any(type(s) is not dict or set(s)!={"role","signature"}
               or s["role"]!=ROLES[index]
               for index,s in enumerate(signatures))):
        raise AudioAssetHold("Owner and reviewers must sign in sequence, one time each")
    if (type(trusted_public_keys) is not dict or set(trusted_public_keys)!=set(ROLES)):
        raise AudioAssetHold("Three independently enrolled public keys required")
    keys=[_b64(trusted_public_keys[x],32) for x in ROLES]
    if len(set(keys))!=3:
        raise AudioAssetHold("Duplicate reviewer identities/keys forbidden")
    if (packet.get("publication_authorized") is not False
        or any(packet.get(field) is not True for field in REVIEW_FIELDS)):
        raise AudioAssetHold("All independent human checks must be completed by humans")
    issued,expires=_utc(packet.get("issued_at")),_utc(packet.get("expires_at"))
    current=now or datetime.now(timezone.utc)
    if (current.tzinfo is None or not issued<=current.astimezone(timezone.utc)<expires
        or not timedelta(minutes=1)<=expires-issued<=timedelta(minutes=30)):
        raise AudioAssetHold("Short-lived pre-inference authorization required")
    payload=canonical({k:v for k,v in packet.items() if k!="signatures"})
    for index,prior in enumerate(signatures):
        try:
            Ed25519PublicKey.from_public_bytes(keys[index]).verify(
                _b64(prior["signature"],64),payload)
        except (InvalidSignature,ValueError) as exc:
            raise AudioAssetHold("Earlier reviewer signature invalid") from exc
    key=_private_signing_key(key_path)
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    actual=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    if actual!=keys[len(signatures)]:
        raise AudioAssetHold("Private key does not match registered reviewer")
    import base64
    signature=base64.urlsafe_b64encode(key.sign(payload)).rstrip(b"=").decode("ascii")
    return {**packet,"signatures":[*signatures,
                                   {"role":role,"signature":signature}]}
