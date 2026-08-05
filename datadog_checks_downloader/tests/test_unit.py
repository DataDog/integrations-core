# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import ssl
import urllib.error
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from tuf.api.exceptions import DownloadError
from urllib3 import ProxyManager

from datadog_checks.downloader.cli import _v2_failure_category
from datadog_checks.downloader.download import TUFDownloader, _load_public_keys
from datadog_checks.downloader.exceptions import TargetNotFoundError

HTTPS_RESPONSE = b'downloader TLS test response'
CA_BUNDLE_VARIABLES = ('SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE')


class HTTPSRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header('Content-Length', str(len(HTTPS_RESPONSE)))
        self.end_headers()
        self.wfile.write(HTTPS_RESPONSE)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def _create_tls_material(directory: Path) -> tuple[Path, Path, Path]:
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Downloader test CA')])
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(server_name)
        .issuer_name(ca_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    ca_path = directory / 'ca.pem'
    certificate_path = directory / 'server.pem'
    key_path = directory / 'server-key.pem'
    ca_path.write_bytes(ca_certificate.public_bytes(Encoding.PEM))
    certificate_path.write_bytes(server_certificate.public_bytes(Encoding.PEM))
    key_path.write_bytes(server_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()))
    return ca_path, certificate_path, key_path


@contextlib.contextmanager
def _local_https_server(directory: Path) -> Iterator[tuple[str, Path]]:
    ca_path, certificate_path, key_path = _create_tls_material(directory)
    server = ThreadingHTTPServer(('localhost', 0), HTTPSRequestHandler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.load_cert_chain(certificate_path, key_path)
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f'https://localhost:{server.server_port}/test', ca_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize(
    'exc,expected',
    [
        pytest.param(TargetNotFoundError('missing'), 'target version not found', id='target-not-found'),
        pytest.param(urllib.error.URLError('timeout'), 'network error', id='network-urlerror'),
        pytest.param(DownloadError('boom'), 'network error', id='network-downloaderror'),
        pytest.param(TimeoutError('slow'), 'network error', id='network-timeout'),
        pytest.param(ValueError('bad pointer'), 'other', id='other'),
    ],
)
def test_v2_failure_category(exc, expected):
    assert _v2_failure_category(exc) == expected


def test_load_public_keys_preserves_historical_key_id(tmp_path):
    key_id = 'historical-key-id'
    public_key = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key()
    public_key_path = tmp_path / f'{key_id}.pub'
    public_key_path.write_bytes(public_key.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

    public_keys = _load_public_keys([str(public_key_path)])

    assert public_keys[key_id]['keyid'] == key_id


def test_tuf_downloader_explicitly_uses_cached_root_as_bootstrap(mocker):
    updater = mocker.patch('datadog_checks.downloader.download.Updater')

    TUFDownloader()

    assert updater.call_args.kwargs['bootstrap'] is None


@pytest.mark.parametrize('ca_bundle_variable', CA_BUNDLE_VARIABLES)
def test_tuf_fetcher_trusts_ca_bundle_environment_variable(
    mocker, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ca_bundle_variable: str
) -> None:
    mocker.patch('datadog_checks.downloader.download.Updater.refresh')
    with _local_https_server(tmp_path) as (url, ca_path):
        for variable in CA_BUNDLE_VARIABLES:
            monkeypatch.delenv(variable, raising=False)
        monkeypatch.setenv(ca_bundle_variable, str(ca_path))
        monkeypatch.setenv('NO_PROXY', 'localhost')
        monkeypatch.setenv('no_proxy', 'localhost')
        downloader = TUFDownloader()
        fetcher = downloader._TUFDownloader__updater._fetcher

        assert fetcher.download_bytes(url, len(HTTPS_RESPONSE)) == HTTPS_RESPONSE


def test_tuf_fetcher_honors_https_proxy(mocker, monkeypatch: pytest.MonkeyPatch) -> None:
    mocker.patch('datadog_checks.downloader.download.Updater.refresh')
    proxy_url = 'http://proxy.example:8080'
    for variable in ('https_proxy', 'NO_PROXY', 'no_proxy', 'ALL_PROXY', 'all_proxy'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('HTTPS_PROXY', proxy_url)
    downloader = TUFDownloader()
    fetcher = downloader._TUFDownloader__updater._fetcher

    manager = fetcher._proxy_env.get_pool_manager('https', 'repository.example')

    assert isinstance(manager, ProxyManager)
    assert manager.proxy.host == 'proxy.example'
    assert manager.proxy.port == 8080


def test_non_official_wheel_filter(mocker):
    mocked_wheels = {
        '3.6.1': {'py2.py3': 'datadog_vsphere-3.6.1-py2.py3-none-any.whl'},
        '3.6.2': {'py2.py3': 'datadog_vsphere-3.6.2-py2.py3-none-any.whl'},
        '5.4.0rc2': {'py2.py3': 'datadog_vsphere-5.4.0rc2-py2.py3-none-any.whl'},
        '6.2.2a1': {'py2.py3': 'datadog_vsphere-6.2.2b1-py2.py3-none-any.whl'},
        '6.3.0b1': {'py2.py3': 'datadog_vsphere-6.3.0b1-py2.py3-none-any.whl'},
        '6.3.0pre3': {'py2.py3': 'datadog_vsphere-6.3.0pre1-py2.py3-none-any.whl'},
    }

    downloader = TUFDownloader()
    mock_wheels_call = mocker.patch.object(TUFDownloader, '_TUFDownloader__get_versions', return_value=mocked_wheels)

    integration = "datadog-vsphere"
    result = downloader.get_wheel_relpath(integration)

    mock_wheels_call.assert_called_once()
    assert result == 'simple/datadog-vsphere/datadog_vsphere-3.6.2-py2.py3-none-any.whl'
