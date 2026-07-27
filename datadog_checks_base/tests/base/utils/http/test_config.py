# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ssl

import mock

from datadog_checks.base.utils.http import STANDARD_FIELDS, RequestsWrapper
from datadog_checks.base.utils.http_protocol import HTTPTimeoutConfig

from .common import proxies_from_http


class TestTimeout:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # Assert the timeout is slightly larger than a multiple of 3,
        # which is the default TCP packet retransmission window. See:
        # https://tools.ietf.org/html/rfc2988
        assert 0 < http.default_timeout.connect % 3 <= 1

    def test_config_timeout(self):
        instance = {'timeout': 24.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.default_timeout == HTTPTimeoutConfig(24.5, 24.5)

    def test_config_multiple_timeouts(self):
        instance = {'read_timeout': 4, 'connect_timeout': 10}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.default_timeout == HTTPTimeoutConfig(10, 4)

    def test_config_init_config_override(self):
        instance = {}
        init_config = {'timeout': 16}
        http = RequestsWrapper(instance, init_config)

        assert http.default_timeout == HTTPTimeoutConfig(16, 16)


class TestRequestSize:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.request_size == 16384

    def test_config_correct(self):
        instance = {'request_size': 0.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert isinstance(http.request_size, int)
        assert http.request_size == 512


class TestVerify:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.tls_config.tls_verify is True

    def test_config_verify(self):
        instance = {'tls_verify': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.tls_config.tls_verify is False

    def test_config_ca_cert(self):
        instance = {'tls_ca_cert': 'ca_cert'}
        init_config = {}

        with mock.patch.object(ssl.SSLContext, 'load_verify_locations') as mock_load_verify_locations:
            http = RequestsWrapper(instance, init_config)

            assert http.session.verify == 'ca_cert'  # The session attribute instantiates the SSLContext
            assert mock_load_verify_locations.call_count == 1
            assert mock_load_verify_locations.call_args[1]['cafile'] == 'ca_cert'

    def test_config_verify_and_ca_cert(self):
        instance = {'tls_verify': True, 'tls_ca_cert': 'ca_cert'}
        init_config = {}

        with mock.patch.object(ssl.SSLContext, 'load_verify_locations') as mock_load_verify_locations:
            http = RequestsWrapper(instance, init_config)

            assert http.session.verify == 'ca_cert'  # The session attribute instantiates the SSLContext
            assert http.tls_config.tls_ca_cert == 'ca_cert'
            assert mock_load_verify_locations.call_count == 1
            assert mock_load_verify_locations.call_args[1]['cafile'] == 'ca_cert'


class TestRemapper:
    def test_legacy_no_proxy(self):
        instance = {'no_proxy': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert proxies_from_http(http) == {'http': '', 'https': ''}
        assert http.no_proxy_uris is None

    def test_no_default(self):
        instance = {}
        init_config = {}
        remapper = {'prometheus_timeout': {'name': 'timeout'}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.default_timeout == HTTPTimeoutConfig(STANDARD_FIELDS['timeout'], STANDARD_FIELDS['timeout'])

    def test_invert(self):
        instance = {'disable_ssl_validation': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.tls_config.tls_verify is True

    def test_invert_without_explicit_default(self):
        instance = {}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.tls_config.tls_verify is True

    def test_standard_override(self):
        instance = {'disable_ssl_validation': True, 'tls_verify': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.tls_config.tls_verify is False

    def test_unknown_name_default(self):
        instance = {}
        init_config = {}
        remapper = {'verify_tls': {'name': 'verify', 'default': False}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.tls_config.tls_verify is True


class TestAllowRedirect:
    def test_allow_redirect_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com')
            assert get.call_args.kwargs['allow_redirects'] is True

    def test_allow_redirect_override_default(self):
        instance = {'allow_redirects': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com')
            assert get.call_args.kwargs['allow_redirects'] is False
