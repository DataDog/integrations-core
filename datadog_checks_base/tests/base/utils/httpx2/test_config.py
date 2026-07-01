# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper


def test_default_headers_include_user_agent(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert any(key.lower() == 'user-agent' for key in http.options['headers'])


def test_extra_headers_merge(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({'extra_headers': {'X-Extra': 'value'}}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-extra'] == 'value'


def test_headers_override_defaults(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({'headers': {'User-Agent': 'custom-agent/1.0'}}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert captured_requests[0].headers['user-agent'] == 'custom-agent/1.0'


def test_per_request_headers_merge_into_request(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', headers={'X-Per-Request': 'yes'})
    assert captured_requests[0].headers['x-per-request'] == 'yes'


def test_per_request_empty_headers_dict_preserves_client_defaults(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({'extra_headers': {'X-Default': 'kept'}}, {}, transport=capturing_transport)
    http.get('http://example.test/', headers={})
    assert captured_requests[0].headers['x-default'] == 'kept'


@pytest.mark.parametrize(
    'headers,extra_headers,canonical_key,expected_value',
    [
        pytest.param({'X-Foo': 'a'}, {'x-foo': 'b'}, 'x-foo', 'b', id='extra-wins-on-case-different-overlap'),
        pytest.param(
            {'Content-Type': 'application/json'},
            {'content-type': 'text/plain'},
            'content-type',
            'text/plain',
            id='extra-wins-same-case',
        ),
        pytest.param({'X-Foo': 'a'}, None, 'x-foo', 'a', id='headers-only'),
        pytest.param(None, {'X-Foo': 'b'}, 'x-foo', 'b', id='extra-only'),
    ],
)
def test_per_request_headers_extra_headers_case_fold(
    capturing_transport, captured_requests, headers, extra_headers, canonical_key, expected_value
):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    kwargs = {}
    if headers is not None:
        kwargs['headers'] = headers
    if extra_headers is not None:
        kwargs['extra_headers'] = extra_headers
    http.get('http://example.test/', **kwargs)

    sent = captured_requests[0].headers
    # Single case-folded entry on the outgoing request.
    assert sent.get_list(canonical_key) == [expected_value]


def test_init_header_get_set_are_case_insensitive_with_case_different_overlap(capturing_transport):
    http = HTTPX2Wrapper(
        {'headers': {'X-Foo': 'a'}, 'extra_headers': {'x-foo': 'b'}},
        {},
        transport=capturing_transport,
    )
    assert http.get_header('X-FOO') == http.get_header('x-foo')
    http.set_header('X-Foo', 'c')
    assert http.get_header('X-Foo') == 'c'
    assert http.get_header('x-foo') == 'c'


def test_timeout_from_instance(capturing_transport):
    http = HTTPX2Wrapper({'timeout': 25}, {}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 25.0
    assert read == 25.0


def test_connect_and_read_timeout_split(capturing_transport):
    http = HTTPX2Wrapper({'connect_timeout': 5, 'read_timeout': 30}, {}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 5.0
    assert read == 30.0


@pytest.mark.parametrize(
    'timeout_value,expected',
    [
        pytest.param(
            None,
            {'connect': None, 'read': None, 'write': None, 'pool': None},
            id='none-means-no-timeout',
        ),
        pytest.param(
            7,
            {'connect': 7.0, 'read': 7.0, 'write': 7.0, 'pool': 7.0},
            id='scalar-pins-all-phases',
        ),
        pytest.param(
            (3, 5),
            {'connect': 3.0, 'read': 5.0, 'write': 5.0, 'pool': 5.0},
            id='tuple-connect-read-pins-write-pool',
        ),
    ],
)
def test_per_request_timeout_value_construction(capturing_transport, captured_requests, timeout_value, expected):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', timeout=timeout_value)
    assert captured_requests[0].extensions['timeout'] == expected


def test_verify_defaults_to_true(capturing_transport, clean_ca_env):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] is True


def test_verify_uses_requests_ca_bundle_env(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('REQUESTS_CA_BUNDLE', '/env/requests.pem')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/requests.pem'


def test_verify_falls_back_to_curl_ca_bundle_env(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('CURL_CA_BUNDLE', '/env/curl.pem')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/curl.pem'


def test_verify_requests_ca_bundle_wins_over_curl(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('REQUESTS_CA_BUNDLE', '/env/requests.pem')
    clean_ca_env.setenv('CURL_CA_BUNDLE', '/env/curl.pem')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/requests.pem'


def test_explicit_tls_ca_cert_wins_over_env_ca_bundle(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('REQUESTS_CA_BUNDLE', '/env/requests.pem')
    http = HTTPX2Wrapper({'tls_ca_cert': '/etc/ssl/ca.pem'}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/etc/ssl/ca.pem'


def test_verify_off_ignores_env_ca_bundle(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('REQUESTS_CA_BUNDLE', '/env/requests.pem')
    http = HTTPX2Wrapper({'tls_verify': False}, {}, transport=capturing_transport)
    assert http.options['verify'] is False


def test_verify_uses_ssl_cert_file_env(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('SSL_CERT_FILE', '/env/ssl_cert_file.pem')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/ssl_cert_file.pem'


def test_verify_falls_back_to_ssl_cert_dir_env(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('SSL_CERT_DIR', '/env/certs')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/certs'


def test_verify_ssl_cert_file_wins_over_ssl_cert_dir(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('SSL_CERT_FILE', '/env/ssl_cert_file.pem')
    clean_ca_env.setenv('SSL_CERT_DIR', '/env/certs')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/ssl_cert_file.pem'


def test_verify_requests_ca_bundle_wins_over_ssl_cert_file(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('REQUESTS_CA_BUNDLE', '/env/requests.pem')
    clean_ca_env.setenv('SSL_CERT_FILE', '/env/ssl_cert_file.pem')
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/env/requests.pem'


def test_explicit_tls_ca_cert_wins_over_ssl_cert_file(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('SSL_CERT_FILE', '/env/ssl_cert_file.pem')
    http = HTTPX2Wrapper({'tls_ca_cert': '/etc/ssl/ca.pem'}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/etc/ssl/ca.pem'


def test_verify_off_ignores_ssl_cert_file_env(capturing_transport, clean_ca_env):
    clean_ca_env.setenv('SSL_CERT_FILE', '/env/ssl_cert_file.pem')
    http = HTTPX2Wrapper({'tls_verify': False}, {}, transport=capturing_transport)
    assert http.options['verify'] is False


def test_verify_false_when_tls_verify_off(capturing_transport):
    http = HTTPX2Wrapper({'tls_verify': False}, {}, transport=capturing_transport)
    assert http.options['verify'] is False


def test_tls_ca_cert_uses_path(capturing_transport):
    http = HTTPX2Wrapper({'tls_ca_cert': '/etc/ssl/ca.pem'}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/etc/ssl/ca.pem'


def test_tls_client_cert_string(capturing_transport):
    http = HTTPX2Wrapper({'tls_cert': '/etc/ssl/client.pem'}, {}, transport=capturing_transport)
    assert http.options['cert'] == '/etc/ssl/client.pem'


def test_tls_client_cert_with_key(capturing_transport):
    http = HTTPX2Wrapper(
        {'tls_cert': '/etc/ssl/client.pem', 'tls_private_key': '/etc/ssl/client.key'},
        {},
        transport=capturing_transport,
    )
    assert http.options['cert'] == ('/etc/ssl/client.pem', '/etc/ssl/client.key')


def test_tls_no_cert_when_not_configured(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    assert http.options['cert'] is None


@pytest.mark.parametrize(
    'lookup_name,default,expected',
    [
        pytest.param('x-foo', None, 'bar', id='lowercase-lookup'),
        pytest.param('X-FOO', None, 'bar', id='uppercase-lookup'),
        pytest.param('missing', None, None, id='missing-no-default'),
        pytest.param('missing', 'fallback', 'fallback', id='missing-with-default'),
    ],
)
def test_get_header(capturing_transport, lookup_name, default, expected):
    http = HTTPX2Wrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    assert http.get_header(lookup_name, default=default) == expected


def test_set_header_overrides_existing(capturing_transport):
    http = HTTPX2Wrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    http.set_header('X-FOO', 'new')
    assert http.get_header('x-foo') == 'new'


def test_set_header_propagates_to_outgoing_request(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    http.set_header('X-FOO', 'updated')
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-foo'] == 'updated'


def test_set_header_adds_new_header(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.set_header('X-New', 'value')
    assert http.get_header('x-new') == 'value'
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-new'] == 'value'


def test_remapper_renames_field(capturing_transport):
    remapper = {'ssl_validation': {'name': 'tls_verify'}}
    http = HTTPX2Wrapper({'ssl_validation': False}, {}, remapper=remapper, transport=capturing_transport)
    assert http.options['verify'] is False


def test_remapper_invert_flips_value(capturing_transport):
    # disable_ssl_validation=True means "do NOT verify" -> options['verify'] is False.
    remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True}}
    http = HTTPX2Wrapper({'disable_ssl_validation': True}, {}, remapper=remapper, transport=capturing_transport)
    assert http.options['verify'] is False


def test_remapper_invert_with_explicit_default(capturing_transport, clean_ca_env):
    # Remapped field absent from instance, explicit default takes effect, then invert flips it.
    remapper = {'disable_ssl_validation': {'name': 'tls_verify', 'invert': True, 'default': False}}
    http = HTTPX2Wrapper({}, {}, remapper=remapper, transport=capturing_transport)
    # default=False, invert flips to True -> verify is True.
    assert http.options['verify'] is True


def test_remapper_instance_wins_over_remapped_field(capturing_transport, clean_ca_env):
    # If the standard field is present in instance, the remapped alternative is ignored.
    remapper = {'ssl_validation': {'name': 'tls_verify'}}
    http = HTTPX2Wrapper(
        {'ssl_validation': False, 'tls_verify': True}, {}, remapper=remapper, transport=capturing_transport
    )
    assert http.options['verify'] is True


def test_remapper_ignores_unknown_target_field(capturing_transport):
    # Remapper targeting a non-STANDARD_FIELDS key is silently ignored.
    remapper = {'some_alias': {'name': 'definitely_not_a_known_field'}}
    http = HTTPX2Wrapper({'some_alias': 'ignored'}, {}, remapper=remapper, transport=capturing_transport)
    assert 'definitely_not_a_known_field' not in http.options


@pytest.mark.parametrize(
    'kwarg,value,hint_substring',
    [
        pytest.param('proxies', {'http': 'http://proxy:8080'}, 'proxy support', id='proxies'),
        pytest.param('allow_redirects', False, 'follow_redirects', id='allow-redirects-uses-httpx-name'),
    ],
)
def test_request_rejects_unknown_kwarg(capturing_transport, kwarg, value, hint_substring):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError, match=kwarg) as excinfo:
        http.get('http://example.test/', **{kwarg: value})
    assert hint_substring in str(excinfo.value)


def test_init_config_timeout_used_when_instance_has_none(capturing_transport):
    http = HTTPX2Wrapper({}, {'timeout': 42}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 42.0
    assert read == 42.0


def test_instance_timeout_overrides_init_config_timeout(capturing_transport):
    http = HTTPX2Wrapper({'timeout': 7}, {'timeout': 42}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 7.0
    assert read == 7.0


def test_init_config_log_requests_used_when_instance_has_none(capturing_transport):
    http = HTTPX2Wrapper({}, {'log_requests': True}, transport=capturing_transport)
    assert http._log_requests is True


def test_instance_log_requests_overrides_init_config(capturing_transport):
    http = HTTPX2Wrapper({'log_requests': False}, {'log_requests': True}, transport=capturing_transport)
    assert http._log_requests is False
