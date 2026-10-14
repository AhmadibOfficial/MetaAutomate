"""P2-02d: cryptographic, source-only TLS 1.3 peer evidence adapter.

The *only* safe way to produce this evidence here is from a server-side
SSLSocket after OpenSSL verified the client's certificate against a pinned
trusted CA and required mutual TLS. The caller never supplies forwarded
headers, SAN strings, trust booleans or a plain JSON evidence object.

NOT registered with any HTTP route; cannot authenticate a OneCall user,
authorize a tenant, replay JTI, execute AMBOY or prove live cloud readiness.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ssl

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID

from app.onecall_peer_policy import (
    PeerIdentityTestAdmission,
    SERVICE_ID,
    ServicePeerRejected,
    TrustedPeerPolicy,
    VerifiedTlsPeerEvidence,
    admit_verified_service_peer,
)


def verify_real_mtls_peer_for_identity_test(
    connected_socket: ssl.SSLSocket,
    policy: TrustedPeerPolicy,
) -> PeerIdentityTestAdmission:
    """Only an already-handshaken *server-side* TLS socket can supply evidence.

    Peer CA chain and proof of the private key are verified by Python OpenSSL
    during the handshake, using caller-configured trusted CA roots.
    The test verifies server context requires certificates and TLS >=1.3.
    Chain configuration still requires external operator review before use.
    """
    def reject() -> None:
        raise ServicePeerRejected("Unverified OneCall mTLS service peer")

    if not isinstance(connected_socket, ssl.SSLSocket):
        reject()
    try:
        if (
            connected_socket.server_side is not True
            or connected_socket.context.verify_mode != ssl.CERT_REQUIRED
            or connected_socket.version() != "TLSv1.3"
            or connected_socket.cipher() is None
        ):
            reject()
        peer_der = connected_socket.getpeercert(binary_form=True)
        peer_details = connected_socket.getpeercert(binary_form=False)
        if not peer_der or not peer_details:
            reject()
        certificate = x509.load_der_x509_certificate(peer_der)
        # The handshake validates the chain; X.509 parsing validates the
        # exact product service URI and independent CLIENT_AUTH purpose.
        urls = certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value.get_values_for_type(x509.UniformResourceIdentifier)
        if urls != [SERVICE_ID]:
            reject()
        eku = certificate.extensions.get_extension_for_class(
            x509.ExtendedKeyUsage
        ).value
        if ExtendedKeyUsageOID.CLIENT_AUTH not in eku:
            reject()
        constraints = certificate.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
        if constraints.ca is not False:
            reject()
        current = datetime.now(timezone.utc)
        if not (certificate.not_valid_before_utc <= current <
                certificate.not_valid_after_utc):
            reject()
        return admit_verified_service_peer(
            VerifiedTlsPeerEvidence(
                certificate_der=peer_der,
                identity_uri=urls[0],
                verified_chain=True,  # OpenSSL context with CERT_REQUIRED
                client_certificate_required=True,
                handshake_at=current,
                evidence_origin="verified-tls-terminator",
                tls_session_bound=True,
            ),
            policy,
            now=current,
        )
    except (ssl.SSLError, ValueError, TypeError, x509.ExtensionNotFound):
        reject()
