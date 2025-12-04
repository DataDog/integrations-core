# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import ssl

import mock
import pytest
from requests.exceptions import SSLError

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.tls import TlsConfig
from datadog_checks.dev.utils import ON_WINDOWS

pytestmark = [pytest.mark.unit]

TEST_CIPHERS = ['AES256-GCM-SHA384', 'AES128-GCM-SHA256']


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
            http = RequestsWrapper(instance, init_config)
            http.get('https://example.com')

            assert mock_load_cert_chain.call_count == 1
            assert mock_load_cert_chain.call_args[0][0] == 'cert'

    def test_config_cert_and_private_key(self):
        instance = {'tls_cert': 'cert', 'tls_private_key': 'key'}
        init_config = {}

        with mock.patch.object(ssl.SSLContext, 'load_cert_chain') as mock_load_cert_chain:
            http = RequestsWrapper(instance, init_config)
            http.get('https://example.com')

            assert mock_load_cert_chain.call_count == 1
            assert mock_load_cert_chain.call_args[0][0] == 'cert'
            assert mock_load_cert_chain.call_args[1]["keyfile"] == 'key'

    @pytest.mark.parametrize(
        'options, expected_cert, expected_key',
        [
            pytest.param({}, None, None, id='cert foo'),
            pytest.param({'cert': 'foo'}, 'foo', None, id='cert foo'),
            pytest.param({'cert': ('foo', 'bar')}, 'foo', 'bar', id='cert foo,bar'),
        ],
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

    @pytest.mark.skipif(ON_WINDOWS, reason="Windows uses the default store locations.")
    def test_bad_default_verify_paths_and_fallback_to_certifi(self, monkeypatch, caplog):
        '''The SSL default verify paths can be set incorrectly.'''
        bad_cert_file = "/nonexistent/path/to/ssl/cert.pem"
        bad_cert_dir = "/nonexistent/path/to/ssl/certs"
        monkeypatch.setenv("SSL_CERT_FILE", bad_cert_file)
        monkeypatch.setenv("SSL_CERT_DIR", bad_cert_dir)
        bad_ssl_paths = ssl.DefaultVerifyPaths(
            cafile="None",
            capath="None",
            openssl_cafile_env="SSL_CERT_FILE",
            openssl_capath_env="SSL_CERT_DIR",
            openssl_cafile=bad_cert_file,
            openssl_capath=bad_cert_dir,
        )
        with mock.patch("ssl.get_default_verify_paths", return_value=bad_ssl_paths):
            with mock.patch("requests.Session.get"):
                with caplog.at_level(logging.INFO):
                    http = RequestsWrapper({"tls_verify": True}, {})
                    assert ssl.get_default_verify_paths() == bad_ssl_paths
                    assert http.session.adapters["https://"].ssl_context.get_ca_certs() != []
                    http.get("https://example.com")
            assert 'No CA certificates loaded from system default paths, attempting certifi fallback.' in caplog.text


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
        instance = {'tls_verify': True, 'tls_ciphers': TEST_CIPHERS[0]}
        init_config = {}

        with mock.patch('datadog_checks.base.utils.http.create_socket_connection') as mock_create_socket_connection:
            mock_socket = mock.MagicMock()
            mock_create_socket_connection.return_value = mock_socket

            with mock.patch('datadog_checks.base.utils.tls.ssl.SSLContext') as mock_ssl_context_class:
                mock_context = mock.MagicMock()
                mock_ssl_context_class.return_value = mock_context

                # Mock the wrapped socket to avoid actual SSL operations
                mock_wrapped_socket = mock.MagicMock()
                mock_context.wrap_socket.return_value.__enter__.return_value = mock_wrapped_socket
                mock_wrapped_socket.getpeercert.return_value = b'fake_cert_data'
                mock_wrapped_socket.version.return_value = 'TLSv1.3'

                # Mock the certificate loading to avoid cryptography operations
                with mock.patch('datadog_checks.base.utils.http.RequestsWrapper.load_intermediate_certs'):
                    http = RequestsWrapper(instance, init_config)
                    assert http.session.verify is True  # The session attribute instantiates the SSLContext
                    mock_context.set_ciphers.assert_called_once_with(instance['tls_ciphers'])
                    http.fetch_intermediate_certs('example.com', 443)
                    # Assert set_ciphers called a second time after fetch_intermediate_certs
                    assert mock_context.set_ciphers.call_count == 2
                    assert mock_context.set_ciphers.call_args_list[1][0][0] == instance['tls_ciphers']

    def test_intermediate_certs_loaded(self):
        """Test that intermediate certs are loaded correctly."""
        instance = {'tls_verify': True, 'tls_intermediate_ca_certs': ('some_cert', 'another_cert')}
        init_config = {}
        with mock.patch('requests.Session.get'):
            with mock.patch('ssl.SSLContext.load_verify_locations') as mock_load_verify_locations:
                http = RequestsWrapper(instance, init_config)
                assert http.session.verify is True  # The session attribute instantiates the SSLContext
                assert mock_load_verify_locations.call_count >= 1
                all_calls = mock_load_verify_locations.mock_calls
                # Assert that the last call contains the intermediate CA certs
                assert all_calls[-1].kwargs["cadata"] == "\n".join(instance['tls_intermediate_ca_certs'])


class TestSSLContext:
    def test_default_tls_ciphers(self):
        """Test that default TLS ciphers are applied when none are specified."""
        instance = {'tls_verify': True}
        init_config = {}

        # Mock the SSLContext creation
        with mock.patch.object(ssl.SSLContext, 'set_ciphers') as mock_set_ciphers:
            http = RequestsWrapper(instance, init_config)
            http.get('https://example.com')

            # Verify that the default ciphers are set
            assert mock_set_ciphers.call_count == 1
            assert mock_set_ciphers.call_args[0][0] == 'ALL'


class TestSSLContextAdapter:
    def test_adapter_caching(self):
        """_SSLContextAdapter should be recovered from cache when possible."""

        with mock.patch('requests.Session.get'):
            with mock.patch('datadog_checks.base.utils.http.create_ssl_context') as mock_create_ssl_context:
                http = RequestsWrapper({'persist_connections': True, 'tls_verify': True}, {})
                # Verify that the adapter is created and cached
                default_config_key = TlsConfig(**http.tls_config)
                adapter = http.session.get_adapter('https://example.com')
                assert http._https_adapters == {default_config_key: adapter}
                mock_create_ssl_context.assert_called_once_with(http.tls_config)

                # Verify that the cached adapter is reused for the same TLS config
                http.get('https://example.com')

                assert http._https_adapters == {default_config_key: adapter}
                assert http.session.get_adapter('https://example.com') is adapter
                mock_create_ssl_context.assert_called_once_with(http.tls_config)

    def test_adapter_caching_new_adapter(self):
        """A new _SSLContextAdapter should be created when a new TLS config is requested."""

        with mock.patch('requests.Session.get'):
            with mock.patch('datadog_checks.base.utils.http.create_ssl_context') as mock_create_ssl_context:
                http = RequestsWrapper({'persist_connections': True, 'tls_verify': True}, {})
                # Verify that the adapter is created and cached for the default TLS config
                default_config_key = TlsConfig(**http.tls_config)
                adapter = http.session.get_adapter('https://example.com')
                assert http._https_adapters == {default_config_key: adapter}
                mock_create_ssl_context.assert_called_once_with(http.tls_config)

                # Verify that a new adapter is created for a different TLS config
                http.get('https://example.com', verify=False)

                new_config = http.tls_config.copy()
                new_config.update({'tls_verify': False})
                new_config_key = TlsConfig(**new_config)
                new_adapter = http.session.get_adapter('https://example.com')
                assert new_adapter is not adapter
                mock_create_ssl_context.assert_called_with(new_config)
                assert http._https_adapters == {default_config_key: adapter, new_config_key: new_adapter}
                # Verify that no more adapters are created for the same configs
                http.get('https://example.com', verify=False)
                http.get('https://example.com', verify=True)

                assert http._https_adapters == {default_config_key: adapter, new_config_key: new_adapter}
