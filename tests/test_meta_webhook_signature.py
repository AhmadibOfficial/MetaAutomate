"""Offline test vectors for webhook signature and scoped synthetic event keys."""
import hashlib
import hmac
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.meta_webhook_signature import (
    verify_meta_webhook_signature,synthetic_event_fingerprint,MAX_PAYLOAD_BYTES,
)


def test_valid_hmac_signature_over_exact_raw_body():
    secret=b"simulated-secret-at-least-16"
    payload=b'{"object":"instagram","entry":[{"id":"SIM-123"}]}'
    signed="sha256="+hmac.new(secret,payload,hashlib.sha256).hexdigest()
    assert verify_meta_webhook_signature(payload,signed,secret)
    assert not verify_meta_webhook_signature(payload+b" ",signed,secret)
    assert not verify_meta_webhook_signature(payload,signed,b"another-safe-secret")
    assert not verify_meta_webhook_signature(payload,signed.upper(),secret)


@pytest.mark.parametrize("header",[
    "", "sha256=", "sha1="+"0"*64, "sha256="+"G"*64,
    "sha256="+"0"*64+"evil", " sha256="+"0"*64,
])
def test_invalid_header_rejected(header):
    assert not verify_meta_webhook_signature(b"demo",header,b"abcdefghijklmnop")


@pytest.mark.parametrize("payload,header,secret",[
    ("string","sha256="+"0"*64,b"abcdefghijklmnop"),
    (b"", "sha256="+"0"*64,b"abcdefghijklmnop"),
    (b"x"*(MAX_PAYLOAD_BYTES+1),"sha256="+"0"*64,b"abcdefghijklmnop"),
    (b"x","sha256="+"0"*64,b"short"),
    (b"x",None,b"abcdefghijklmnop"),
])
def test_invalid_envelopes_rejected(payload,header,secret):
    assert not verify_meta_webhook_signature(payload,header,secret)


def test_synthetic_event_ids_are_tenant_separated():
    left=synthetic_event_fingerprint("SIM-IG-01","academy_demo")
    right=synthetic_event_fingerprint("SIM-IG-01","bespoke_demo")
    assert left!=right
    assert len(left)==64
    with pytest.raises(SyntheticGrowthError):
        synthetic_event_fingerprint("customer@example.com","academy_demo")
    with pytest.raises(SyntheticGrowthError):
        synthetic_event_fingerprint("SIM-IG-01","fake_tenant")
