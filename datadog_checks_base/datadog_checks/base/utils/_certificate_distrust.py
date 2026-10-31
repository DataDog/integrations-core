# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Reject TLS connections whose verified certificate chain contains a distrusted CA public key.

Keys are matched by the SHA-256 of the DER `SubjectPublicKeyInfo`, so reissued and cross-signed certificates
that reuse a distrusted key are rejected as well. The check runs after OpenSSL verifies the chain, so it
applies whichever trust store made the chain verify.

Besides the built-in keys, the Agent setting `tls_distrusted_ca_names` lists the common names of more CAs to
distrust. It adds to the built-in keys and cannot remove one. An invalid value fails every verified connection,
naming the bad entry, rather than trusting a CA it may have been meant to distrust.

`install`, which runs when datadog_checks_base is imported, applies the check to the connections of every
`ssl.SSLContext` in the process, whoever creates it, and to pyOpenSSL connections. The check runs when
`do_handshake()` completes, which covers the default `do_handshake_on_connect=True` and explicit handshakes.
Known limits:
- A caller that disables `do_handshake_on_connect` and lets the first read or write complete the handshake
  implicitly bypasses it.
- With mutual TLS, the client certificate has already been sent when the check rejects the server.
- TLS that doesn't go through Python's `ssl` module or pyOpenSSL is not checked: native client libraries such as
  librdkafka (kafka_consumer) and libpq (postgres) bring their own.
"""

import functools
import hashlib
import logging
import ssl
from collections.abc import Callable, Iterable
from types import ModuleType
from typing import TYPE_CHECKING, Any

import wrapt

from datadog_checks.base.agent import datadog_agent

if TYPE_CHECKING:
    from OpenSSL import SSL

LOGGER = logging.getLogger(__name__)

# The eMudhra emSign G3 intermediate CA keys that were compromised. Go's `crypto/x509`
# (https://go.dev/issue/82345), rustls-webpki 0.103.16
# (https://github.com/rustls/webpki/commit/f3caaa9f2ba94a42dcd31767e367688a416a3d87) and the Datadog Agent
# distrust the same keys.
DISTRUSTED_SPKI_SHA256 = {
    'ebed6475c2c2d80fcb199f3fe8dd6e6b3ce60b77eb15d4e42c3dec0c6f5b5105': 'EM DV TLS CA - G3B (eMudhra)',
    '49dd353dc2b919a3770645117d0e60c16115e7d1bc259eefe734b00ea434fe5f': 'EM DV TLS CA - G3C (eMudhra)',
    'e0254c7fcdc265e2f0f8a428dabb75ab4ae039b4872d62f5ee57f0877d5a8a41': 'EM EV TLS CA - G3B (eMudhra)',
    '5c0660a2b164910d8ff589c18e14552e9e0ec237dcefe2cb736d41a4811f81a0': 'EM EV TLS CA - G3C (eMudhra)',
    '43bffa19d6ef651451f6841e019931e96f6f2eaeff28ab4b6f1ce4576de2717b': 'EM OV TLS CA - G3B (eMudhra)',
    '63ecefee431d49523bc1136c4e72d0206a477086caf606cd5cf025686c109cf8': 'EM OV TLS CA - G3C (eMudhra)',
    'ec4ffa1ad0ac88081314b7aaffef6a91f97cd57291bb5ba686c5415f5eb4f6b6': 'EM OV CS CA - G3B (eMudhra)',
    '92c063d67e8f14db71d288e11266ffdaf69cbf115f7bab14f3bc2f68d25e0e30': 'EM OV CS CA - G3C (eMudhra)',
}

# The Agent setting, in `datadog.yaml` or the `DD_TLS_DISTRUSTED_CA_NAMES` environment variable, that lists the common
# names of more CAs to distrust, so that customers can block a compromised CA before a release adds its keys above.
# It adds to the keys above and cannot remove them.
DISTRUSTED_CA_NAMES_SETTING = 'tls_distrusted_ca_names'

# OpenSSL's `X509_V_ERR_APPLICATION_VERIFICATION`: the application rejected a chain that OpenSSL accepted.
X509_V_ERR_APPLICATION_VERIFICATION = 50
# OpenSSL's `X509_V_ERR_CERT_REJECTED`: the Agent's embedded Python rejects the keys above with this code during the
# handshake, before the check in this module runs, and OpenSSL uses it for certificates a trust store rejects.
X509_V_ERR_CERT_REJECTED = 28

DER_EXPLICIT_VERSION = 0xA0


class CertificateDistrustError(ssl.SSLCertVerificationError):
    """The verified certificate chain contains a distrusted CA public key, or could not be checked for one."""


class CertificateDistrustSSLSocket(ssl.SSLSocket):
    """An `SSLSocket` that rejects distrusted CA keys in the verified chain when `do_handshake()` completes."""

    def do_handshake(self, block: bool = False) -> None:
        super().do_handshake(block)
        try:
            _check_verified_chain(self)
        except CertificateDistrustError:
            # The handshake has already completed, so close the connection: a caller that swallows the error must
            # not be able to send data to the distrusted peer.
            self.close()
            raise


class CertificateDistrustSSLObject(ssl.SSLObject):
    """An `SSLObject` that rejects distrusted CA keys in the verified chain when `do_handshake()` completes."""

    def do_handshake(self) -> None:
        super().do_handshake()
        _check_verified_chain(self)


def attach_distrust_check(context: ssl.SSLContext) -> ssl.SSLContext:
    """Make the connections created from `context` reject verified chains that contain a distrusted CA key.

    `install` does this for every context through `ssl.SSLContext`; setting it on a context as well keeps the check
    if a library later replaces the classes on `ssl.SSLContext`.
    """
    context.sslsocket_class = CertificateDistrustSSLSocket
    context.sslobject_class = CertificateDistrustSSLObject
    return context


def install() -> None:
    """Check the verified chain of every TLS client connection in this process for distrusted CA keys.

    This covers the connections of every `ssl.SSLContext`, whoever creates it, and of pyOpenSSL, which pymongo uses,
    once something imports it.
    """
    ssl.SSLContext.sslsocket_class = CertificateDistrustSSLSocket
    ssl.SSLContext.sslobject_class = CertificateDistrustSSLObject
    wrapt.register_post_import_hook(_check_pyopenssl_handshakes, 'OpenSSL.SSL')


def find_distrusted_key(chain: Iterable[bytes]) -> tuple[str, str] | None:
    """Return the CA name and SPKI SHA-256 of the first distrusted key in a chain of DER certificates."""
    for cert_der in chain:
        try:
            spki = _subject_public_key_info(cert_der)
        except ValueError:
            # OpenSSL re-encodes each certificate's unsigned outer header and returns its signed contents unchanged,
            # so the DER certificates carrying the distrusted keys always parse. Skipping a certificate that can't be
            # read therefore cannot hide one, while failing would reject unusual but valid chains.
            continue
        spki_sha256 = hashlib.sha256(spki).hexdigest()
        if (ca_name := _distrusted_ca_name(spki_sha256)) is not None:
            return ca_name, spki_sha256
    return None


def find_distrusted_name(chain: Iterable[bytes], names: frozenset[str]) -> str | None:
    """Return the common name of the first certificate in a chain of DER certificates whose common name is listed.

    `names` holds names as `_normalize_name` returns them.
    """
    from cryptography import x509
    from cryptography.x509.oid import NameOID

    for cert_der in chain:
        try:
            subject = x509.load_der_x509_certificate(cert_der).subject
        except ValueError:
            # cryptography refuses a few encodings that OpenSSL accepts. Skip such a certificate rather than reject an
            # unusual but valid chain; its name just can't be matched.
            continue
        for attribute in subject.get_attributes_for_oid(NameOID.COMMON_NAME):
            if _normalize_name(str(attribute.value)) in names:
                return str(attribute.value)
    return None


def caused_by_certificate_distrust(error: BaseException) -> bool:
    """Return whether a rejected certificate is in the chain of exceptions behind `error`.

    That is a `CertificateDistrustError`, or a verification error with `X509_V_ERR_CERT_REJECTED`. Both
    `__cause__` and `__context__` are followed because requests and urllib3 link wrapped TLS errors with either,
    so an exception raised while handling a distrust failure counts as caused by it.
    """
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, CertificateDistrustError) or (
            isinstance(current, ssl.SSLCertVerificationError) and current.verify_code == X509_V_ERR_CERT_REJECTED
        ):
            return True
        pending.extend(link for link in (current.__cause__, current.__context__) if link is not None)
    return False


@functools.cache
def _configured_names() -> tuple[frozenset[str], str | None]:
    """Return the CA names the Agent setting distrusts, normalized, or why the setting is invalid.

    The setting is read once per process; the Agent applies a change to it when it restarts.
    """
    try:
        return _parse_configured_names(datadog_agent.get_config(DISTRUSTED_CA_NAMES_SETTING)), None
    except ValueError as e:
        LOGGER.error('%s Verified TLS connections fail until the setting is fixed.', e)
        return frozenset(), str(e)


def _parse_configured_names(value: object) -> frozenset[str]:
    # An Agent that doesn't register the setting returns None, and the test stub returns ''.
    if value is None or value == '':
        return frozenset()
    if not isinstance(value, list):
        raise ValueError(
            f'The Agent setting `{DISTRUSTED_CA_NAMES_SETTING}` must be a list of CA common names, not {value!r}.'
        )
    names = set()
    for index, entry in enumerate(value):
        name = _normalize_name(entry) if isinstance(entry, str) else ''
        if not name:
            raise ValueError(
                f'Entry {index} of the Agent setting `{DISTRUSTED_CA_NAMES_SETTING}` is {entry!r}, which is not a CA '
                "common name such as 'EM DV TLS CA - G3B'."
            )
        names.add(name)
    return frozenset(names)


def _normalize_name(name: str) -> str:
    # Compare names as X.500 matching does: ignoring case and runs of whitespace.
    return ' '.join(name.split()).casefold()


def _distrusted_ca_name(spki_sha256: str) -> str | None:
    """Return the name of the CA whose public key has this SHA-256, if that key is distrusted."""
    return DISTRUSTED_SPKI_SHA256.get(spki_sha256)


def _check_verified_chain(connection: ssl.SSLSocket | ssl.SSLObject) -> None:
    # Without verification, `get_verified_chain` returns the unverified chain the server sent.
    if connection.server_side or connection.context.verify_mode == ssl.CERT_NONE:
        return
    _check_chain(connection.get_verified_chain(), connection.session_reused)


def _check_pyopenssl_handshakes(module: ModuleType) -> None:
    wrapt.wrap_function_wrapper(module, 'Connection.do_handshake', _do_checked_pyopenssl_handshake)


def _do_checked_pyopenssl_handshake(
    wrapped: Callable[..., None], instance: 'SSL.Connection', args: tuple[Any, ...], kwargs: dict[str, Any]
) -> None:
    from OpenSSL import SSL

    wrapped(*args, **kwargs)
    try:
        _check_pyopenssl_chain(instance)
    except CertificateDistrustError:
        # The handshake has already completed, so mark the connection shut down: a caller that swallows the error must
        # not be able to send data to the distrusted peer.
        instance.set_shutdown(SSL.SENT_SHUTDOWN | SSL.RECEIVED_SHUTDOWN)
        raise


def _check_pyopenssl_chain(connection: 'SSL.Connection') -> None:
    from cryptography.hazmat.primitives.serialization import Encoding
    from OpenSSL import SSL

    # Without verification, OpenSSL never verified the chain.
    if connection.get_context().get_verify_mode() == SSL.VERIFY_NONE:
        return
    chain = [cert.public_bytes(Encoding.DER) for cert in connection.get_verified_chain(as_cryptography=True) or []]
    # pyOpenSSL can't tell whether the session was resumed, but a client only completes a verified handshake without
    # a verified chain when it resumes one.
    _check_chain(chain, session_reused=not chain)


def _check_chain(chain: list[bytes], session_reused: bool) -> None:
    names, invalid_setting = _configured_names()
    if invalid_setting is not None:
        # Refuse the connection rather than trust a CA the setting may have been meant to distrust.
        raise _certificate_distrust_error(invalid_setting)
    if not chain and session_reused:
        # A resumed session skips chain verification, so refuse it instead of trusting a chain that can't be seen.
        raise _certificate_distrust_error(
            'the certificate chain of a resumed TLS session could not be checked for distrusted CA keys'
        )
    match = find_distrusted_key(chain)
    if match is not None:
        ca_name, spki_sha256 = match
        raise _certificate_distrust_error(
            f'the certificate chain contains a distrusted CA key: {ca_name} (SPKI SHA-256 {spki_sha256})'
        )
    if names and (common_name := find_distrusted_name(chain, names)) is not None:
        raise _certificate_distrust_error(
            f'the certificate chain contains a distrusted CA: {common_name} (listed in the Agent setting '
            f'`{DISTRUSTED_CA_NAMES_SETTING}`)'
        )


def _certificate_distrust_error(verify_message: str) -> CertificateDistrustError:
    # Built like the verification errors `_ssl.c` raises, so callers inspecting those fields see the usual values.
    error = CertificateDistrustError(
        int(ssl.SSL_ERROR_SSL), f'[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: {verify_message}'
    )
    error.library = 'SSL'
    error.reason = 'CERTIFICATE_VERIFY_FAILED'
    error.verify_code = X509_V_ERR_APPLICATION_VERIFICATION
    error.verify_message = verify_message
    return error


def _subject_public_key_info(cert_der: bytes) -> bytes:
    """Return the `SubjectPublicKeyInfo` of a DER certificate, exactly as encoded."""
    offset, end = _der_tlv(cert_der, 0, len(cert_der))  # Certificate
    offset, end = _der_tlv(cert_der, offset, end)  # tbsCertificate
    # The version is omitted from v1 certificates.
    if offset < end and cert_der[offset] == DER_EXPLICIT_VERSION:
        _, offset = _der_tlv(cert_der, offset, end)
    # serialNumber, signature, issuer, validity and subject precede the subjectPublicKeyInfo.
    for _ in range(5):
        _, offset = _der_tlv(cert_der, offset, end)
    _, spki_end = _der_tlv(cert_der, offset, end)
    return cert_der[offset:spki_end]


def _der_tlv(data: bytes, offset: int, end: int) -> tuple[int, int]:
    """Return the content start and end offsets of the TLV at `offset`, which must fit before `end`."""
    if offset >= end:
        raise ValueError('truncated tag')
    length, content_start = _der_length(data, offset + 1, end)
    content_end = content_start + length
    if content_end > end:
        raise ValueError('truncated value')
    return content_start, content_end


def _der_length(data: bytes, offset: int, end: int) -> tuple[int, int]:
    """Return the length encoded at `offset` and the offset where the content starts."""
    if offset >= end:
        raise ValueError('truncated length')
    first = data[offset]
    if first < 0x80:
        return first, offset + 1
    # DER forbids the indefinite form (0x80), and certificate lengths never need more than four octets.
    octets = first & 0x7F
    if octets == 0 or octets > 4:
        raise ValueError('unsupported length encoding')
    content_start = offset + 1 + octets
    if content_start > end:
        raise ValueError('truncated length')
    return int.from_bytes(data[offset + 1 : content_start], 'big'), content_start
