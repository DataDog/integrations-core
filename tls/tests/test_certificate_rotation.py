# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
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
    # Some rotators preserve timestamps; refresh must still notice the new credentials.
    original_stats = {path: Path(path).stat() for path in (client_cert, client_key)}
    write_credentials(tmp_path, 'client', replacement_client, combined=combined, password=password)
    for path, original_stat in original_stats.items():
        os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    assert peer_certificate(check, server_context, mocker) == replacement_client[0].public_bytes(
        serialization.Encoding.DER
    )
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=2)


@pytest.mark.parametrize(
    'config_style,failure',
    [
        (style, failure)
        for style in ('modern', 'legacy', 'combined')
        for failure in ('malformed', 'missing_cert', 'unreadable_cert')
    ]
    + [
        (style, failure)
        for style in ('modern', 'legacy')
        for failure in ('missing_key', 'unreadable_key', 'mismatched')
    ],
)
def test_invalid_rotated_client_certificate_reports_failure_and_recovers(
    tmp_path: Path, mocker: MockerFixture, aggregator: AggregatorStub, failure: str, config_style: str
):
    # A bad replacement must not silently keep the previous credential or prevent recovery on the next run.
    root = make_certificate('Test Root', ca=True)
    root_path, _ = write_credentials(tmp_path, 'root', root)
    server = make_certificate('localhost', root)
    server_cert, server_key = write_credentials(tmp_path, 'server', server)
    client = make_certificate('client', root)
    combined = config_style == 'combined'
    client_cert, client_key = write_credentials(tmp_path, 'client', client, combined=combined)
    instance = {'server': 'localhost', 'tls_ca_cert': root_path}
    instance['cert' if config_style == 'legacy' else 'tls_cert'] = client_cert
    if not combined:
        instance['private_key' if config_style == 'legacy' else 'tls_private_key'] = client_key
    check = TLSCheck('tls', {}, [instance])
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.maximum_version = ssl.TLSVersion.TLSv1_2
    # A missing configured credential must fail even if the server permits anonymous clients.
    server_context.verify_mode = ssl.CERT_OPTIONAL
    server_context.load_verify_locations(cafile=root_path)
    server_context.load_cert_chain(server_cert, server_key)
    peer_certificate(check, server_context, mocker)
    aggregator.reset()

    credential_path = Path(client_key if failure.endswith('_key') else client_cert)
    if failure.startswith('missing'):
        credential_path.unlink()
    elif failure.startswith('unreadable'):
        credential_path.chmod(0)
        if os.access(credential_path, os.R_OK):
            credential_path.chmod(0o600)
            pytest.skip('This platform or user can read files with no read permissions')
    elif failure == 'mismatched':
        client = make_certificate('replacement-client', root)
        Path(client_cert).write_bytes(client[0].public_bytes(serialization.Encoding.PEM))
    else:
        Path(client_cert).write_text('invalid certificate')
    with pytest.raises(ssl.SSLError):
        peer_certificate(check, server_context, mocker)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.CRITICAL, count=1)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=0)
    aggregator.assert_metric('tls.days_left', count=0)
    aggregator.assert_metric('tls.seconds_left', count=0)

    if failure.startswith('unreadable'):
        credential_path.chmod(0o600)
    if failure == 'mismatched':
        Path(client_key).write_bytes(
            client[1].private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
            )
        )
    else:
        write_credentials(tmp_path, 'client', client, combined=combined)
    assert peer_certificate(check, server_context, mocker) == client[0].public_bytes(serialization.Encoding.DER)
    aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=1)


@pytest.mark.parametrize('fetch_result', ['replacement', 'unavailable', 'invalid', 'undiscovered'])
def test_expired_intermediate_is_removed_from_refreshed_trust(
    tmp_path: Path, mocker: MockerFixture, aggregator: AggregatorStub, fetch_result: str
):
    # Expiry must remove old trust even when fetching its replacement fails.
    root = make_certificate('Test Root', ca=True)
    root_path, _ = write_credentials(tmp_path, 'root', root)
    uri = 'http://issuer.test/intermediate.der'
    intermediate = make_certificate('Old Intermediate', root, ca=True)
    old_der = intermediate[0].public_bytes(serialization.Encoding.DER)
    server = make_certificate('localhost', intermediate, aia_uri=uri)
    server_cert, server_key = write_credentials(tmp_path, 'server', server)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.maximum_version = ssl.TLSVersion.TLSv1_2
    server_context.load_cert_chain(server_cert, server_key)
    check = TLSCheck('tls', {}, [{'server': 'localhost', 'tls_ca_cert': root_path}])
    now = mocker.patch('datadog_checks.tls.tls_remote.get_timestamp', return_value=100)
    fetch = mocker.patch('datadog_checks.tls.tls_remote.fetch_intermediate_cert', return_value=old_der)
    check.checker.load_intermediate_certs(server[0].public_bytes(serialization.Encoding.DER))
    peer_certificate(check, server_context, mocker)
    now.return_value = 3699
    check.checker.load_intermediate_certs(server[0].public_bytes(serialization.Encoding.DER))
    fetch.assert_called_once()
    aggregator.reset()

    now.return_value = 3700
    replacement = make_certificate('New Intermediate', root, ca=True)
    new_der = replacement[0].public_bytes(serialization.Encoding.DER)
    if fetch_result != 'undiscovered':
        fetch.return_value = {'replacement': new_der, 'unavailable': None, 'invalid': b'invalid DER'}[fetch_result]
        check.checker.load_intermediate_certs(server[0].public_bytes(serialization.Encoding.DER))
        assert fetch.call_count == 2
    if fetch_result == 'replacement':
        server = make_certificate('localhost', replacement, aia_uri=uri)
        server_cert, server_key = write_credentials(tmp_path, 'server', server)
        server_context.load_cert_chain(server_cert, server_key)
        peer_certificate(check, server_context, mocker)
        aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.OK, count=1)
    else:
        with pytest.raises(ssl.SSLError):
            peer_certificate(check, server_context, mocker)
        aggregator.assert_service_check(SERVICE_CHECK_VALIDATION, status=check.CRITICAL, count=1)
    trusted_certs = check.get_tls_context().get_ca_certs(binary_form=True)
    assert old_der not in trusted_certs
    assert (new_der in trusted_certs) == (fetch_result == 'replacement')
    assert len(check._intermediate_cert_cache) == (1 if fetch_result == 'replacement' else 0)


def test_cached_intermediate_refetches_expired_parent(mocker: MockerFixture):
    # A still-cached intermediate must not prevent renewal of an older parent in its AIA chain.
    root = make_certificate('Test Root', ca=True)
    parent_uri = 'http://issuer.test/parent.der'
    parent = make_certificate('Parent', root, ca=True)
    intermediate = make_certificate('Intermediate', parent, ca=True, aia_uri=parent_uri)
    intermediate_der = intermediate[0].public_bytes(serialization.Encoding.DER)
    leaf = make_certificate('localhost', intermediate, aia_uri='http://issuer.test/intermediate.der')
    leaf_der = leaf[0].public_bytes(serialization.Encoding.DER)
    parent_der = parent[0].public_bytes(serialization.Encoding.DER)
    check = TLSCheck('tls', {}, [{'server': 'localhost'}])
    now = mocker.patch('datadog_checks.tls.tls_remote.get_timestamp', return_value=100)
    fetch = mocker.patch('datadog_checks.tls.tls_remote.fetch_intermediate_cert', return_value=parent_der)
    check.checker.load_intermediate_certs(intermediate_der)
    now.return_value = 200
    fetch.return_value = intermediate_der
    check.checker.load_intermediate_certs(leaf_der)
    now.return_value = 3700
    fetch.reset_mock()
    fetch.return_value = parent_der
    check.checker.load_intermediate_certs(leaf_der)
    fetch.assert_called_once()
    assert fetch.call_args.args[0] == parent_uri
    assert set(check._intermediate_cert_cache.values()) == {intermediate_der, parent_der}
