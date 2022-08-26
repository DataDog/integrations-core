# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.http import STANDARD_FIELDS, RequestsWrapper


class TestTimeout:
    def test_config_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        # Assert the timeout is slightly larger than a multiple of 3,
        # which is the default TCP packet retransmission window. See:
        # https://tools.ietf.org/html/rfc2988
        assert 0 < http.options['timeout'][0] % 3 <= 1

    def test_config_timeout(self):
        instance = {'timeout': 24.5}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (24.5, 24.5)

    def test_config_multiple_timeouts(self):
        instance = {'read_timeout': 4, 'connect_timeout': 10}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (10, 4)

    def test_config_init_config_override(self):
        instance = {}
        init_config = {'timeout': 16}
        http = RequestsWrapper(instance, init_config)

        assert http.options['timeout'] == (16, 16)


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

        assert http.options['verify'] is True

    def test_config_verify(self):
        instance = {'tls_verify': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] is False

    def test_config_ca_cert(self):
        instance = {'tls_ca_cert': 'ca_cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] == 'ca_cert'

    def test_config_verify_and_ca_cert(self):
        instance = {'tls_verify': True, 'tls_ca_cert': 'ca_cert'}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['verify'] == 'ca_cert'


class TestRemapper:
    def test_legacy_no_proxy(self):
        instance = {'no_proxy': True}
        init_config = {}
        http = RequestsWrapper(instance, init_config)

        assert http.options['proxies'] == {'http': '', 'https': ''}
        assert http.no_proxy_uris is None

    def test_no_default(self):
        instance = {}
        init_config = {}
        remapper = {'prometheus_timeout': {'name': 'timeout'}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['timeout'] == (STANDARD_FIELDS['timeout'], STANDARD_FIELDS['timeout'])

    def test_invert(self):
        instance = {'disable_ssl_validation': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True

    def test_invert_without_explicit_default(self):
        instance = {}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True

    def test_standard_override(self):
        instance = {'disable_ssl_validation': True, 'tls_verify': False}
        init_config = {}
        remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is False

    def test_unknown_name_default(self):
        instance = {}
        init_config = {}
        remapper = {'verify_tls': {'name': 'verify', 'default': False}}
        http = RequestsWrapper(instance, init_config, remapper)

        assert http.options['verify'] is True


class TestAllowRedirect:
    def test_allow_redirect_default(self):
        instance = {}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        assert http.options['allow_redirects'] is True

    def test_allow_redirect_override_default(self):
        instance = {'allow_redirects': False}
        init_config = {}
        http = RequestsWrapper(instance, init_config)
        assert http.options['allow_redirects'] is False
