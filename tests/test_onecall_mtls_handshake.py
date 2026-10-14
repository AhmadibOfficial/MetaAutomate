"""P2-02d actual localhost mutual-TLS handshakes with ephemeral X.509 PKI.

A successful handshake proves TLS trust enforcement in this disposable CI
environment; it does not assert that a cloud/private OneCall channel exists.
All key files are generated in pytest's temporary directory, never committed.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import socket
import ssl

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.onecall_mtls_adapter import verify_real_mtls_peer_for_identity_test
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


def _handshake(tmp_path, *, mode="valid", wrong_pin=False, disabled=False):
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
            except (ssl.SSLError, ServicePeerRejected, OSError) as exc:
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
