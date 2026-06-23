# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID

try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

from datadog_checks.tls.tls import TLSCheck
from datadog_checks.tls.tls_remote import TLSRemoteCheck


def build_cert(aia_uri=None):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'example.test')])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2050, 1, 1))
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
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.DER)


@pytest.fixture
def checker():
    instance = {
        'server': 'example.test',
        'username': 'admin',
        'password': 'secret',
        'headers': {'Authorization': 'Bearer token'},
        'tls_cert': '/path/to/client.crt',
        'proxy': {'http': 'http://proxy:3128'},
    }
    check = TLSCheck('tls', {}, [instance])
    check._http = MagicMock()  # spy on the instance's configured (credentialed) session
    return TLSRemoteCheck(check), check


def session_configs(wrapper):
    return [(c.args[0], c.args[1]) for c in wrapper.call_args_list]


def test_aia_fetch_never_uses_instance_credentials(checker):
    remote, check = checker
    leaf = build_cert(aia_uri='http://issuer.test/ca.der')
    session = MagicMock()
    session.get.return_value = MagicMock(content=build_cert())

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session) as wrapper:
        remote.load_intermediate_certs(leaf)

    assert check._http.get.call_count == 0
    for instance, init_config in session_configs(wrapper):
        assert set(instance) <= {'tls_verify'}
        assert init_config == {}


def test_aia_fetch_tries_tls_then_plain_fallback(checker):
    remote, _ = checker
    leaf = build_cert(aia_uri='https://issuer.test/ca.der')
    secure, plain = MagicMock(), MagicMock()
    secure.get.side_effect = Exception('TLS handshake failed')
    plain.get.return_value = MagicMock(content=build_cert())

    def make_wrapper(instance, init_config, *args, **kwargs):
        return plain if instance.get('tls_verify') is False else secure

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', side_effect=make_wrapper) as wrapper:
        remote.load_intermediate_certs(leaf)

    verifies = [instance.get('tls_verify') for instance, _ in session_configs(wrapper)]
    assert verifies[0] is True and False in verifies
    assert secure.get.called and plain.get.called


def test_aia_fetch_caches_uri(checker):
    remote, _ = checker
    leaf = build_cert(aia_uri='http://issuer.test/ca.der')
    session = MagicMock()
    session.get.return_value = MagicMock(content=build_cert())

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session):
        remote.load_intermediate_certs(leaf)
        first = session.get.call_count
        remote.load_intermediate_certs(leaf)

    assert first >= 1 and session.get.call_count == first


def test_aia_fetch_recurses_into_fetched_cert(checker):
    remote, _ = checker
    leaf = build_cert(aia_uri='http://issuer.test/intermediate.der')
    session = MagicMock()
    session.get.side_effect = [
        MagicMock(content=build_cert(aia_uri='http://issuer.test/root.der')),
        MagicMock(content=build_cert()),
    ]

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session):
        remote.load_intermediate_certs(leaf)

    assert session.get.call_count == 2
