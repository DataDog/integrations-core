# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID
from pytest_mock import MockerFixture

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.tls import TLSCheck
from datadog_checks.tls.const import SERVICE_CHECK_VALIDATION

pytestmark = pytest.mark.unit


@pytest.fixture(scope='session', autouse=True)
def certs() -> None:
    """These tests generate their own certificates and do not need the Docker certificate fixture."""


def make_certificate(
    name: str,
    issuer: tuple[x509.Certificate, rsa.RSAPrivateKey] | None = None,
    *,
    ca: bool = False,
    aia_uri: str | None = None,
) -> tuple[x509.Certificate, rsa.RSAPrivateKey]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer_name, issuer_key = (issuer[0].subject, issuer[1]) if issuer else (subject, key)
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), critical=False)
    )
    if aia_uri:
        builder = builder.add_extension(
            x509.AuthorityInformationAccess(
                [
                    x509.AccessDescription(
                        AuthorityInformationAccessOID.CA_ISSUERS, x509.UniformResourceIdentifier(aia_uri)
                    )
                ]
            ),
            critical=False,
        )
    return builder.sign(issuer_key, hashes.SHA256()), key


def write_credentials(
    directory: Path,
    name: str,
    credentials: tuple[x509.Certificate, rsa.RSAPrivateKey],
    *,
    combined: bool = False,
    password: bytes | None = None,
) -> tuple[str, str]:
    cert, key = credentials
    cert_path, key_path = directory / f'{name}.pem', directory / f'{name}.key'
    key_bytes = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption(),
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM) + (key_bytes if combined else b''))
    key_path.write_bytes(key_bytes)
    return str(cert_path), str(key_path)


def peer_certificate(check: TLSCheck, server_context: ssl.SSLContext, mocker: MockerFixture) -> bytes:
    """Run a check against a real TLS peer and return the client certificate that peer received."""
    client_socket, server_socket = socket.socketpair()
    client_socket.settimeout(5)
    server_socket.settimeout(5)

    def accept() -> bytes:
        with server_context.wrap_socket(server_socket, server_side=True) as connection:
            return connection.getpeercert(binary_form=True)

    with client_socket, server_socket, ThreadPoolExecutor(max_workers=1) as executor:
        accepted = executor.submit(accept)
        mocker.patch.object(check, 'create_connection', return_value=client_socket)
        check.check(None)
        return accepted.result(timeout=5)


@pytest.mark.parametrize('with_intermediate', [False, True])
@pytest.mark.parametrize('config_style', ['modern', 'legacy', 'combined', 'encrypted'])
def test_rotated_client_certificate_is_presented(
    tmp_path: Path, mocker: MockerFixture, aggregator: AggregatorStub, config_style: str, with_intermediate: bool
):
    # A running check must present the replacement client certificate, without losing downloaded CA trust.
    root = make_certificate('Test Root', ca=True)
    root_path, _ = write_credentials(tmp_path, 'root', root)
    intermediate = make_certificate('Test Intermediate', root, ca=True)
    aia_uri = 'http://issuer.test/intermediate.der'
    server = make_certificate(
        'localhost', intermediate if with_intermediate else root, aia_uri=aia_uri if with_intermediate else None
    )
    server_cert, server_key = write_credentials(tmp_path, 'server', server)
    original_client = make_certificate('original-client', root)
    replacement_client = make_certificate('replacement-client', root)
    combined = config_style == 'combined'
    password = b'test-password' if config_style == 'encrypted' else None
    client_cert, client_key = write_credentials(
        tmp_path, 'client', original_client, combined=combined, password=password
    )
    instance = {'server': 'localhost', 'tls_ca_cert': root_path}
    instance['cert' if config_style == 'legacy' else 'tls_cert'] = client_cert
    if not combined:
        instance['private_key' if config_style == 'legacy' else 'tls_private_key'] = client_key
    if password:
        instance['tls_private_key_password'] = password.decode()
    check = TLSCheck('tls', {}, [instance])

    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    # TLS 1.2 completes client authentication before the client handshake returns.
    server_context.maximum_version = ssl.TLSVersion.TLSv1_2
    server_context.verify_mode = ssl.CERT_REQUIRED
    server_context.load_verify_locations(cafile=root_path)
    server_context.load_cert_chain(server_cert, server_key)

    if with_intermediate:
        fetch = mocker.patch(
            'datadog_checks.tls.tls_remote.fetch_intermediate_cert',
            return_value=intermediate[0].public_bytes(serialization.Encoding.DER),
        )
        check.checker.load_intermediate_certs(server[0].public_bytes(serialization.Encoding.DER))
        fetch.assert_called_once()

    assert peer_certificate(check, server_context, mocker) == original_client[0].public_bytes(
        serialization.Encoding.DER
    )
    write_credentials(tmp_path, 'client', replacement_client, combined=combined, password=password)
    assert peer_certificate(check, server_context, mocker) == replacement_client[0].public_bytes(
        serialization.Encoding.DER
    )
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=2)


def test_invalid_rotated_client_certificate_reports_failure_and_recovers(
    tmp_path: Path, mocker: MockerFixture, aggregator: AggregatorStub
):
    # A bad replacement must not silently keep the previous credential or prevent recovery on the next run.
    root = make_certificate('Test Root', ca=True)
    root_path, _ = write_credentials(tmp_path, 'root', root)
    server = make_certificate('localhost', root)
    server_cert, server_key = write_credentials(tmp_path, 'server', server)
    client = make_certificate('client', root)
    client_cert, client_key = write_credentials(tmp_path, 'client', client)
    check = TLSCheck(
        'tls',
        {},
        [{'server': 'localhost', 'tls_ca_cert': root_path, 'tls_cert': client_cert, 'tls_private_key': client_key}],
    )
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.maximum_version = ssl.TLSVersion.TLSv1_2
    server_context.verify_mode = ssl.CERT_REQUIRED
    server_context.load_verify_locations(cafile=root_path)
    server_context.load_cert_chain(server_cert, server_key)
    peer_certificate(check, server_context, mocker)

    Path(client_cert).write_text('invalid certificate')
    with pytest.raises(ssl.SSLError):
        peer_certificate(check, server_context, mocker)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.CRITICAL, count=1)

    write_credentials(tmp_path, 'client', client)
    assert peer_certificate(check, server_context, mocker) == client[0].public_bytes(serialization.Encoding.DER)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=2)
