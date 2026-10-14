"""P2-02d actual localhost mutual-TLS handshakes with ephemeral X.509 PKI.

A successful handshake proves TLS trust enforcement in this disposable CI
environment; it does not assert that a cloud/private OneCall channel exists.
All key files are generated in pytest's temporary directory, never committed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from base64 import urlsafe_b64encode
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pathlib import Path
import socket
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.onecall_mtls_adapter import verify_real_mtls_peer_for_identity_test
from app.onecall_assertion import AssertionRejected
from app.onecall_joined_identity_test import evaluate_joined_onecall_identity_test
from app.onecall_identity_gate import OneCallCurrentIdentity
from app.onecall_peer_policy import (
    SERVICE_ID, PURPOSE, ServicePeerRejected, TrustedPeerPolicy,
)

ROOT = Path(__file__).resolve().parents[1]


def _save(path, contents):
    path.write_bytes(contents)
    return str(path)


def _private_pem(key):
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )


def _root_ca(tmp_path, prefix="primary"):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                         "Disposable P2-02d " + prefix)])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=2))
        .not_valid_after(now + timedelta(minutes=12))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
            key_encipherment=False, data_encipherment=False, key_agreement=False,
            key_cert_sign=True, crl_sign=True, encipher_only=False,
            decipher_only=False), critical=True)
        .sign(key, hashes.SHA256()))
    path = _save(tmp_path / (prefix + "-ca.pem"),
                 cert.public_bytes(serialization.Encoding.PEM))
    return key, cert, path


def _leaf(tmp_path, ca_key, ca_cert, label, *, client, uri=None,
          expired=False):
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
    builder = (x509.CertificateBuilder()
        .subject_name(name).issuer_name(ca_cert.subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=15))
        .not_valid_after(now - timedelta(minutes=1) if expired
                         else now + timedelta(minutes=7))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage(
            [ExtendedKeyUsageOID.CLIENT_AUTH if client
             else ExtendedKeyUsageOID.SERVER_AUTH]), critical=False))
    if client:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([
                x509.UniformResourceIdentifier(uri or SERVICE_ID)
            ]), critical=False)
    else:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False)
    cert = builder.sign(ca_key, hashes.SHA256())
    certpath = _save(tmp_path / (label + "-cert.pem"),
                     cert.public_bytes(serialization.Encoding.PEM))
    keypath = _save(tmp_path / (label + "-key.pem"), _private_pem(key))
    return cert, certpath, keypath


def _handshake(tmp_path, *, mode="valid", wrong_pin=False, disabled=False, admission_callback=None):
    ca_key, ca_cert, ca_path = _root_ca(tmp_path)
    server_cert, server_certfile, server_keyfile = _leaf(
        tmp_path, ca_key, ca_cert, "server", client=False)
    trusted_client_cert, _, _ = _leaf(
        tmp_path, ca_key, ca_cert, "unused-good-client", client=True)
    if mode == "untrusted-ca":
        client_ca_key, client_ca_cert, _ = _root_ca(tmp_path, "untrusted")
    else:
        client_ca_key, client_ca_cert = ca_key, ca_cert
    uri = "spiffe://other.internal/not-onecall" if mode == "wrong-uri" else SERVICE_ID
    client_cert, client_certfile, client_keyfile = _leaf(
        tmp_path, client_ca_key, client_ca_cert, "client",
        client=True, uri=uri, expired=mode == "expired")

    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sctx.minimum_version = ssl.TLSVersion.TLSv1_3
    sctx.verify_mode = ssl.CERT_REQUIRED
    sctx.load_verify_locations(cafile=ca_path)
    sctx.load_cert_chain(certfile=server_certfile, keyfile=server_keyfile)

    cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    cctx.minimum_version = ssl.TLSVersion.TLSv1_3
    cctx.check_hostname = True
    cctx.verify_mode = ssl.CERT_REQUIRED
    cctx.load_verify_locations(cafile=ca_path)
    if mode != "no-client-cert":
        cctx.load_cert_chain(certfile=client_certfile, keyfile=client_keyfile)

    cert_der = client_cert.public_bytes(serialization.Encoding.DER)
    fingerprint = sha256(cert_der).hexdigest()
    if wrong_pin:
        fingerprint = "f" * 64 if fingerprint != "f" * 64 else "a" * 64
    policy = TrustedPeerPolicy(
        enabled=not disabled, service_identity=SERVICE_ID, purpose=PURPOSE,
        pinned_certificate_sha256=fingerprint,
    )

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listening:
        listening.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listening.bind(("127.0.0.1", 0))
        listening.listen(1)
        listening.settimeout(6)

        def serve():
            connection, _ = listening.accept()
            with connection:
                connection.settimeout(6)
                with sctx.wrap_socket(connection, server_side=True) as tls:
                    if admission_callback is not None:
                        return admission_callback(tls, policy)
                    return verify_real_mtls_peer_for_identity_test(tls, policy)

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(serve)
            client_error = None
            try:
                with socket.create_connection(listening.getsockname(), timeout=6) as raw:
                    with cctx.wrap_socket(raw, server_hostname="localhost"):
                        pass
            except (ssl.SSLError, OSError) as exc:
                client_error = exc
            try:
                accepted = result.result(timeout=8)
            except (ssl.SSLError, ServicePeerRejected, AssertionRejected, OSError) as exc:
                return None, exc
            return accepted, client_error


def test_real_tls13_mtls_valid_onecall_service_chain(tmp_path):
    admitted, error = _handshake(tmp_path)
    assert error is None
    assert admitted.decision == "PEER_VERIFIED_IDENTITY_TEST_ONLY"
    assert admitted.customer_access is False
    assert admitted.tenant_mapping is False
    assert admitted.bookings is False
    assert admitted.payments is False
    assert admitted.model_execution is False


@pytest.mark.parametrize("mode", [
    "untrusted-ca", "no-client-cert", "wrong-uri", "expired",
])
def test_real_handshake_denies_untrusted_or_wrong_purpose_client(tmp_path, mode):
    admitted, failure = _handshake(tmp_path, mode=mode)
    assert admitted is None, mode
    assert isinstance(failure, (ssl.SSLError, ServicePeerRejected)), mode


@pytest.mark.parametrize("option", ["wrong_pin", "disabled"])
def test_crypto_verified_connection_still_requires_operator_policy(tmp_path, option):
    admitted, failure = _handshake(tmp_path, **{option: True})
    assert admitted is None
    assert isinstance(failure, ServicePeerRejected)


def test_adapter_is_not_exposed_as_route_or_header_authentication():
    for path in ["apps/api/app/main.py",
                 "apps/api/app/amboy_m1.py",
                 "apps/api/app/domain_integrations.py"]:
        assert "onecall_mtls_adapter" not in (ROOT / path).read_text()
    source = (ROOT / "apps/api/app/onecall_mtls_adapter.py").read_text()
    assert "getpeercert(binary_form=True)" in source
    assert "ssl.CERT_REQUIRED" in source
    assert "ExtendedKeyUsageOID.CLIENT_AUTH" in source
    assert "X-Forwarded-Client-Cert" not in source


def _signed_compact(key, header, payload):
    import json
    b64 = lambda raw: urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    data = (b64(json.dumps(header, separators=(",", ":")).encode()) + "." +
            b64(json.dumps(payload, separators=(",", ":")).encode()))
    return data + "." + b64(key.sign(data.encode("ascii")))


def _signed_pair():
    import time
    now = int(time.time())
    id_key = Ed25519PrivateKey.generate()
    service_key = Ed25519PrivateKey.generate()
    pub = lambda k: k.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    subject = str(uuid4())
    assertion = _signed_compact(id_key, {
        "alg": "EdDSA", "typ": "onecall-amboy-identity+jwt",
        "kid": "onecall-ci-key-2026",
    }, {
        "iss": "https://onecall-identity.invalid",
        "aud": "metaautomate-amboy-identity-test",
        "sub": subject, "jti": str(uuid4()), "iat": now,
        "nbf": now, "exp": now + 55, "product": "onecall",
        "scope": "amboy:identity-test", "token_version": 5,
        "authority": "onecall-backend",
    })
    proof = _signed_compact(service_key, {
        "alg": "EdDSA", "typ": "onecall-amboy-service-proof+jwt",
        "kid": "oc-m2m-ci-keys2026",
    }, {
        "iss": "https://onecall-service.invalid",
        "aud": "metaautomate-amboy-m2m-test",
        "sub": "onecall-backend", "jti": str(uuid4()), "iat": now,
        "nbf": now, "exp": now + 28, "product": "onecall",
        "scope": "amboy:service-identity-test",
        "htm": "POST", "htu": "/internal/amboy/identity-test",
        "ath": urlsafe_b64encode(sha256(assertion.encode("ascii")).digest())
            .rstrip(b"=").decode("ascii"),
    })
    return assertion, proof, subject, {"onecall-ci-key-2026": pub(id_key)}, {
        "oc-m2m-ci-keys2026": pub(service_key)}


def _joined_callback(*, status="ACTIVE", token_version=5,
                     assertion_override=None, proof_override=None,
                     consume=None, available=True):
    assertion, proof, subject, id_keys, service_keys = _signed_pair()
    state = OneCallCurrentIdentity(
        subject=subject, token_version=token_version,
        active=status == "ACTIVE", email_verified=True,
        phone_verified=True)
    if consume is None:
        used = set()
        def consume(proof_result):
            pair = (proof_result.identity_jti, proof_result.service_jti)
            if pair in used:
                return False
            used.add(pair)
            return True

    def connected(socket, policy):
        return evaluate_joined_onecall_identity_test(
            server_tls_socket=socket, peer_policy=policy,
            identity_assertion=assertion if assertion_override is None else assertion_override,
            service_proof=proof if proof_override is None else proof_override,
            identity_issuer="https://onecall-identity.invalid",
            identity_pinned_keys=id_keys,
            service_issuer="https://onecall-service.invalid",
            service_pinned_keys=service_keys,
            load_authoritative_onecall_identity=(
                (lambda _: state) if available else
                (lambda _: (_ for _ in ()).throw(OSError("offline")))
            ),
            consume_pair_once=consume,
        )
    return connected


def test_full_joined_real_mtls_and_signed_pair_stays_no_access(tmp_path):
    admitted, failure = _handshake(tmp_path, admission_callback=_joined_callback())
    assert failure is None
    assert admitted.decision == "IDENTITY_TEST_ONLY_NO_ACCESS"
    assert admitted.product == "onecall"
    assert admitted.metaautomate_principal_created is False
    assert admitted.tenant_mapping_granted is False
    assert admitted.booking_permitted is False
    assert admitted.payment_permitted is False
    assert admitted.model_executed is False
    assert admitted.external_action_performed is False


@pytest.mark.parametrize("change", [
    {"status": "BLOCKED"}, {"token_version": 6},
    {"available": False}, {"consume": lambda _: False},
    {"consume": lambda _: (_ for _ in ()).throw(OSError("DB unavailable"))},
])
def test_joined_gate_denies_revoked_offline_or_replayed_identity(tmp_path, change):
    admitted, failure = _handshake(
        tmp_path, admission_callback=_joined_callback(**change))
    assert admitted is None
    assert isinstance(failure, AssertionRejected)


@pytest.mark.parametrize("mode", ["untrusted-ca", "no-client-cert", "wrong-uri", "expired"])
def test_joined_gate_never_uses_invalid_transport(tmp_path, mode):
    admitted, failure = _handshake(
        tmp_path, mode=mode, admission_callback=_joined_callback())
    assert admitted is None
    assert isinstance(failure, (ssl.SSLError, ServicePeerRejected, AssertionRejected))


def test_joined_gate_refuses_disabled_service_policy(tmp_path):
    admitted, failure = _handshake(
        tmp_path, disabled=True, admission_callback=_joined_callback())
    assert admitted is None
    assert isinstance(failure, AssertionRejected)


def test_joined_gate_not_wired_to_customer_auth():
    for path in ("apps/api/app/main.py", "apps/api/app/amboy_m1.py",
                 "apps/api/app/domain_integrations.py",
                 "apps/api/app/authn.py"):
        assert "onecall_joined_identity_test" not in (ROOT / path).read_text()
