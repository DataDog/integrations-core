# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import ssl

import mock
import pytest
from requests.exceptions import SSLError

from datadog_checks.base.utils.http import RequestsWrapper, SSLContextAdapter

pytestmark = [pytest.mark.unit]

IANA_TO_OPENSSL_NAME = {
    'TLS_RSA_WITH_AES_256_GCM_SHA384': 'AES256-GCM-SHA384',
    'TLS_RSA_WITH_AES_128_GCM_SHA256': 'AES128-GCM-SHA256',
}


class TestCert:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['cert'] is None

    def test_config_cert(self):
        instance = {'tls_cert': 'cert'}
        init_config = {}

        with mock.patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load_cert_chain:
            RequestsWrapper(instance, init_config)

            assert mock_load_cert_chain.call_count == 1
            assert mock_load_cert_chain.call_args[0][0] == 'cert'

    def test_config_cert_and_private_key(self):
        instance = {'tls_cert': 'cert', 'tls_private_key': 'key'}
        init_config = {}

        with mock.patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load_cert_chain:
            RequestsWrapper(instance, init_config)

            assert mock_load_cert_chain.call_count == 1
            assert mock_load_cert_chain.call_args[0][0] == 'cert'
            assert mock_load_cert_chain.call_args[1]["keyfile"] == 'key'

    @pytest.mark.parametrize(
        'options, expected_cert, expected_key',
        [
            pytest.param({}, None, None, id='cert foo'),
            pytest.param({'cert': 'foo'}, 'foo', None, id='cert foo'),
            pytest.param({'cert': ('foo','bar')}, 'foo', 'bar', id='cert foo,bar'),
        ]
    )
    def test_request_cert_gets_read(self, options, expected_cert, expected_key):
        '''Test that the request options are set correctly in the new context.'''
        with mock.patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load_cert_chain:
            RequestsWrapper({}, {}).get('https://google.com', **options)

            if options.get('cert') is None:
                assert mock_load_cert_chain.call_count == 0
                return

            mock_load_cert_chain.assert_called_once()
            mock_load_cert_chain.assert_called_with(expected_cert, keyfile=expected_key, password=None)

class TestIgnoreTLSWarning:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is False

    def test_config_flag(self):
        instance = {'tls_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is True

    def test_init_config_flag(self):
        instance = {}
        init_config = {'tls_ignore_warning': True}

        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is True

    def test_instance_and_init_flag(self):
        instance = {'tls_ignore_warning': False}
        init_config = {'tls_ignore_warning': True}

        http = RequestsWrapper(instance, init_config)

        assert http.ignore_tls_warning is False

    def test_default_no_ignore(self, caplog):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_default_no_ignore_http(self, caplog):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('http://www.google.com', verify=False)

        assert sum(1 for _, level, _ in caplog.record_tuples if level == logging.WARNING) == 0

    def test_ignore(self, caplog):
        instance = {'tls_ignore_warning': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_default_no_ignore_session(self, caplog):
        instance = {'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_ignore_session(self, caplog):
        instance = {'tls_ignore_warning': True, 'persist_connections': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_init_ignore(self, caplog):
        instance = {}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_default_init_no_ignore(self, caplog):
        instance = {}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))

    def test_instance_ignore(self, caplog):
        instance = {'tls_ignore_warning': True}
        init_config = {'tls_ignore_warning': False}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, _, message in caplog.record_tuples:
            assert message != expected_message

    def test_instance_no_ignore(self, caplog):
        instance = {'tls_ignore_warning': False}
        init_config = {'tls_ignore_warning': True}
        http = RequestsWrapper(instance, init_config)

        with caplog.at_level(logging.DEBUG), mock.patch('requests.Session.get'):
            http.get('https://www.google.com', verify=False)

        expected_message = 'An unverified HTTPS request is being made to https://www.google.com'
        for _, level, message in caplog.record_tuples:
            if level == logging.DEBUG and message == expected_message:
                break
        else:
            raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))


class TestAIAChasing:
    @pytest.mark.skip(reason="expired certified, reactivate test when certified valid again")
    def test_incomplete_chain(self):
        # Protocol 1.2 is allowed by default
        http = RequestsWrapper({}, {})
        http.get("https://incomplete-chain.badssl.com/")

    def test_cant_allow_unknown_protocol(self, caplog):
        with caplog.at_level(logging.WARNING):
            RequestsWrapper({'tls_protocols_allowed': ['unknown']}, {})
            assert "Unknown protocol `unknown` configured, ignoring it." in caplog.text
        caplog.clear()

    @pytest.mark.skip(reason="expired certified, reactivate test when certified valid again")
    def test_protocol_allowed(self):
        http = RequestsWrapper({'tls_protocols_allowed': ['TLSv1.2']}, {})
        http.get("https://incomplete-chain.badssl.com/")

    def test_protocol_not_allowed(self, caplog):
        http = RequestsWrapper({'tls_protocols_allowed': ['TLSv1.1']}, {})
        with caplog.at_level(logging.ERROR), pytest.raises(Exception):
            http.get("https://incomplete-chain.badssl.com/")
            assert "Protocol version `TLSv1.2` not in the allowed list ['TLSv1.1']" in caplog.text

    @pytest.mark.parametrize(
        "port",
        [
            pytest.param(443, id="443 default https port"),
            pytest.param(444, id="444 non-default https port"),
        ],
    )
    def test_fetch_intermediate_certs(self, port):
        instance = {
            'auth_token': {
                'reader': {'type': 'oauth', 'url': 'foo', 'client_id': 'bar', 'client_secret': 'baz'},
                'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
            }
        }
        http = RequestsWrapper(instance, {})

        with mock.patch('datadog_checks.base.utils.http.create_socket_connection') as mock_create_socket_connection:
            with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.handle_auth_token'):
                with pytest.raises(SSLError):
                    with mock.patch('requests.Session.get', side_effect=SSLError):
                        http.get('https://localhost:{}'.format(port))

        mock_create_socket_connection.assert_called_with('localhost', port)

    def test_fetch_intermediate_certs_tls_ciphers(self):
        """Test that fetch_intermediate_certs uses the correct ciphers."""
        instance = {'tls_verify': True, 'tls_ciphers': ['TLS_RSA_WITH_AES_256_GCM_SHA384']}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        with mock.patch('datadog_checks.base.utils.http.create_socket_connection') as mock_create_socket_connection:
            mock_socket = mock.MagicMock()
            mock_create_socket_connection.return_value = mock_socket

            with mock.patch('datadog_checks.base.utils.http.ssl.SSLContext') as mock_ssl_context_class:
                mock_context = mock.MagicMock()
                mock_ssl_context_class.return_value = mock_context

                # Mock the wrapped socket to avoid actual SSL operations
                mock_wrapped_socket = mock.MagicMock()
                mock_context.wrap_socket.return_value.__enter__.return_value = mock_wrapped_socket
                mock_wrapped_socket.getpeercert.return_value = b'fake_cert_data'
                mock_wrapped_socket.version.return_value = 'TLSv1.3'

                # Mock the certificate loading to avoid cryptography operations
                with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.load_intermediate_certs'):
                    http.fetch_intermediate_certs('example.com', 443)

                # Verify set_ciphers was called with the correct cipher list
                mock_context.set_ciphers.assert_called_once_with('TLS_RSA_WITH_AES_256_GCM_SHA384')


class TestSSLContext:
    """Test the core SSL context functionality."""

    def test_requests_wrapper_creates_ssl_context(self):
        """Test that RequestsWrapper creates an SSLContext instance."""
        instance = {'tls_verify': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert hasattr(http, 'ssl_context')
        assert isinstance(http.ssl_context, ssl.SSLContext)

    def test_session_uses_ssl_context_adapter(self):
        """Test that the session uses SSLContextAdapter for consistent TLS configuration."""
        instance = {'tls_verify': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        session = http.session
        https_adapter = session.get_adapter('https://example.com')

        assert isinstance(https_adapter, SSLContextAdapter)
        assert https_adapter.ssl_context is http.ssl_context

    def test_ssl_context_ciphers_can_be_modified(self):
        """Test that the chosen ciphers can be set on CI runners."""
        context = ssl.create_default_context()
        context.set_ciphers('TLS_RSA_WITH_AES_256_GCM_SHA384')

    def test_tls_ciphers_applied_consistently(self):
        """Test that tls_ciphers are applied consistently."""
        instance = {'tls_verify': True, 'tls_ciphers': list(IANA_TO_OPENSSL_NAME.keys())}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # Verify the TLS context wrapper has the cipher configuration
        assert http.tls_config['tls_ciphers'] == instance['tls_ciphers']

        # Verify the session adapter uses the same TLS context
        session = http.session
        https_adapter = session.get_adapter('https://example.com')

        assert isinstance(https_adapter, SSLContextAdapter)
        assert https_adapter.ssl_context is http.ssl_context
        # Verify that the ciphers are set correctly in the TLS context
        for cipher in instance['tls_ciphers']:
            # At least one entry's name field should match the OpenSSL name
            assert any(
                IANA_TO_OPENSSL_NAME.get(cipher) in c.get('name') for c in https_adapter.ssl_context.get_ciphers()
            )

    def test_default_tls_ciphers(self):
        """Test that default TLS ciphers are applied when none are specified."""
        instance = {'tls_verify': True}
        init_config = {}

        # Mock the SSLContext creation
        with mock.patch.object(ssl.SSLContext, 'set_ciphers') as mock_set_ciphers:
            RequestsWrapper(instance, init_config)

            # Verify that the default ciphers are set
            assert mock_set_ciphers.call_count == 1
            assert mock_set_ciphers.call_args[0][0] == 'ALL'

    def test_host_header_compatibility(self):
        """Test that host header functionality works with TLS context unification."""
        instance = {
            'tls_use_host_header': True,
            'headers': {'Host': 'custom-host.example.com'},
            'tls_verify': True,
            'tls_ciphers': ['TLS_RSA_WITH_AES_256_GCM_SHA384'],
        }
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        session = http.session
        https_adapter = session.get_adapter('https://example.com')

        # Should be the combined adapter that supports both TLS context and host headers
        assert hasattr(https_adapter, 'ssl_context')
        assert https_adapter.ssl_context is http.ssl_context
        assert 'SSLContextHostHeaderAdapter' in str(type(https_adapter))

    def test_remapper_functionality_preserved(self):
        """Test that config remapping functionality is preserved with TLS context unification."""
        instance = {
            'disable_ssl_validation': True,
            'custom_private_key': '/path/to/key.pem',
        }
        remapper = {
            'disable_ssl_validation': {'name': 'tls_verify', 'invert': True},
            'custom_private_key': {'name': 'tls_private_key'},
        }
        init_config = {}

        # Mock the TLS context creation to avoid file operations
        with mock.patch('datadog_checks.base.utils.http.create_ssl_context') as mock_create_context:
            mock_context = mock.MagicMock()
            mock_create_context.return_value = mock_context

            http = RequestsWrapper(instance, init_config, remapper=remapper)

            # Verify remapping worked - disable_ssl_validation: True should become tls_verify: False
            assert http.tls_config['tls_verify'] is False
            assert http.tls_config['tls_private_key'] == '/path/to/key.pem'

    def test_backward_compatibility_maintained(self):
        """Test that all existing TLS configuration options still work."""
        instance = {
            'tls_verify': True,
            'tls_ca_cert': '/path/to/ca.pem',
            'tls_cert': '/path/to/cert.pem',
            'tls_private_key': '/path/to/key.pem',
            'tls_validate_hostname': True,
            'tls_ignore_warning': False,
            'tls_protocols_allowed': ['TLSv1.2', 'TLSv1.3'],
            'tls_ciphers': ['TLS_RSA_WITH_AES_256_GCM_SHA384'],
        }
        init_config = {}

        # Mock the TLS context creation to avoid file operations
        with mock.patch('datadog_checks.base.utils.http.create_ssl_context') as mock_create_context:
            mock_context = mock.MagicMock()
            mock_create_context.return_value = mock_context

            # Should not raise any exceptions
            http = RequestsWrapper(instance, init_config)

            # Verify all options are preserved in RequestsWrapper
            assert http.options['verify'] == '/path/to/ca.pem'
            assert http.options['cert'] == ('/path/to/cert.pem', '/path/to/key.pem')
            assert http.ignore_tls_warning is False
            assert http.tls_protocols_allowed == ['TLSv1.2', 'TLSv1.3']

            # Verify TLS context wrapper has the right config
            assert http.tls_config['tls_verify'] is True
            assert http.tls_config['tls_ciphers'] == ['TLS_RSA_WITH_AES_256_GCM_SHA384']
