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
except ImportError:  # Python 2
    from mock import MagicMock, patch

from datadog_checks.tls.tls import TLSCheck
from datadog_checks.tls.tls_remote import TLSRemoteCheck

# Keys that, if present in a session's configuration, would carry the instance's
# credentials or authentication material to the AIA endpoint.
CREDENTIAL_FIELDS = (
    'auth_token',
    'auth_type',
    'aws_host',
    'aws_region',
    'aws_service',
    'extra_headers',
    'headers',
    'kerberos_auth',
    'kerberos_keytab',
    'kerberos_principal',
    'ntlm_domain',
    'password',
    'proxy',
    'tls_ca_cert',
    'tls_cert',
    'tls_private_key',
    'tls_private_key_password',
    'username',
)


def _build_cert(aia_uri=None):
    """Build a self-signed DER certificate, optionally with an AIA CA Issuers extension."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'example.test')])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime(2020, 1, 1))
        .not_valid_after(datetime.datetime(2050, 1, 1))
    )
    if aia_uri is not None:
        builder = builder.add_extension(
            x509.AuthorityInformationAccess(
                [
                    x509.AccessDescription(
                        AuthorityInformationAccessOID.CA_ISSUERS,
                        x509.UniformResourceIdentifier(aia_uri),
                    )
                ]
            ),
            critical=False,
        )
    cert = builder.sign(key, hashes.SHA256())
    return cert.public_bytes(serialization.Encoding.DER)


def _make_checker(instance):
    instance = dict(instance)
    instance.setdefault('server', 'example.test')
    check = TLSCheck('tls', {}, [instance])
    return TLSRemoteCheck(check), check


@pytest.fixture
def credentialed_instance():
    return {
        'server': 'example.test',
        'username': 'admin',
        'password': 'secret',
        'auth_type': 'basic',
        'headers': {'Authorization': 'Bearer token'},
        'extra_headers': {'X-Custom': 'value'},
        'tls_cert': '/path/to/client.crt',
        'tls_private_key': '/path/to/client.key',
        'tls_ca_cert': '/path/to/ca.crt',
        'proxy': {'http': 'http://proxy:3128'},
    }


def _assert_credential_free(call):
    instance_arg = call.args[0] if call.args else call.kwargs.get('instance', {})
    for field in CREDENTIAL_FIELDS:
        assert not instance_arg.get(field), 'AIA fetch session must not carry the instance credential `{}`'.format(
            field
        )


def test_aia_fetch_uses_credential_free_session(credentialed_instance):
    """The instance's credentials must never reach the attacker-controlled AIA URI."""
    checker, check = _make_checker(credentialed_instance)
    leaf = _build_cert(aia_uri='http://issuer.test/ca.der')
    intermediate = _build_cert()  # no AIA -> recursion stops

    instance_session = MagicMock()
    check._http = instance_session  # spy on the instance's configured (credentialed) session

    session = MagicMock()
    session.get.return_value = MagicMock(content=intermediate)

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session) as wrapper:
        checker.load_intermediate_certs(leaf)

    assert wrapper.call_count >= 1
    for call in wrapper.call_args_list:
        _assert_credential_free(call)

    # The instance's own HTTP session must never be used for the AIA fetch.
    assert instance_session.get.call_count == 0


def test_aia_fetch_no_opt_in_flag_required(credentialed_instance):
    """Credential-free fetching applies even when `fetch_intermediate_certs` is not set."""
    assert 'fetch_intermediate_certs' not in credentialed_instance
    checker, _ = _make_checker(credentialed_instance)
    leaf = _build_cert(aia_uri='http://issuer.test/ca.der')
    intermediate = _build_cert()

    session = MagicMock()
    session.get.return_value = MagicMock(content=intermediate)

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session) as wrapper:
        checker.load_intermediate_certs(leaf)

    assert wrapper.call_count >= 1
    for call in wrapper.call_args_list:
        _assert_credential_free(call)


def test_aia_fetch_tls_first_then_plain_fallback(credentialed_instance):
    """Fetch over secure TLS first; on failure retry without TLS verification."""
    checker, _ = _make_checker(credentialed_instance)
    leaf = _build_cert(aia_uri='https://issuer.test/ca.der')
    intermediate = _build_cert()

    secure_session = MagicMock()
    secure_session.get.side_effect = Exception('TLS handshake failed')
    plain_session = MagicMock()
    plain_session.get.return_value = MagicMock(content=intermediate)

    def make_wrapper(instance, init_config, *args, **kwargs):
        return plain_session if instance.get('tls_verify') is False else secure_session

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', side_effect=make_wrapper) as wrapper:
        checker.load_intermediate_certs(leaf)

    tls_verify_values = [
        (c.args[0] if c.args else c.kwargs['instance']).get('tls_verify') for c in wrapper.call_args_list
    ]
    # Secure attempt (verify on / default) must come before the no-TLS fallback (verify off).
    assert tls_verify_values[0] is not False
    assert False in tls_verify_values
    assert secure_session.get.called
    assert plain_session.get.called


def test_aia_fetch_caching_prevents_refetch(credentialed_instance):
    """A successfully fetched URI is cached and not fetched again within the refresh interval."""
    checker, _ = _make_checker(credentialed_instance)
    leaf = _build_cert(aia_uri='http://issuer.test/ca.der')
    intermediate = _build_cert()

    session = MagicMock()
    session.get.return_value = MagicMock(content=intermediate)

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session):
        checker.load_intermediate_certs(leaf)
        first_calls = session.get.call_count
        checker.load_intermediate_certs(leaf)
        second_calls = session.get.call_count

    assert first_calls >= 1
    assert second_calls == first_calls  # cache hit -> no additional fetch


def test_aia_fetch_recurses_into_fetched_cert(credentialed_instance):
    """Chasing recurses through the fetched intermediate's own AIA extension."""
    checker, _ = _make_checker(credentialed_instance)
    leaf = _build_cert(aia_uri='http://issuer.test/intermediate.der')
    intermediate = _build_cert(aia_uri='http://issuer.test/root.der')
    root = _build_cert()  # terminates recursion

    session = MagicMock()
    session.get.side_effect = [MagicMock(content=intermediate), MagicMock(content=root)]

    with patch('datadog_checks.tls.tls_remote.RequestsWrapper', return_value=session):
        checker.load_intermediate_certs(leaf)

    assert session.get.call_count == 2
