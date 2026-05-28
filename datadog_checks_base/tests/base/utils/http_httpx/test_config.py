# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_default_headers_include_user_agent(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    assert any(key.lower() == 'user-agent' for key in http.options['headers'])


def test_extra_headers_merge(capturing_transport, captured_requests):
    http = HTTPXWrapper({'extra_headers': {'X-Extra': 'value'}}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-extra'] == 'value'


def test_headers_override_defaults(capturing_transport, captured_requests):
    http = HTTPXWrapper({'headers': {'User-Agent': 'custom-agent/1.0'}}, {}, transport=capturing_transport)
    http.get('http://example.test/')
    assert captured_requests[0].headers['user-agent'] == 'custom-agent/1.0'


def test_per_request_headers_merge_into_request(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/', headers={'X-Per-Request': 'yes'})
    assert captured_requests[0].headers['x-per-request'] == 'yes'


def test_timeout_from_instance(capturing_transport):
    http = HTTPXWrapper({'timeout': 25}, {}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 25.0
    assert read == 25.0


def test_connect_and_read_timeout_split(capturing_transport):
    http = HTTPXWrapper({'connect_timeout': 5, 'read_timeout': 30}, {}, transport=capturing_transport)
    connect, read = http.options['timeout']
    assert connect == 5.0
    assert read == 30.0


def test_verify_defaults_to_true(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    assert http.options['verify'] is True


def test_verify_false_when_tls_verify_off(capturing_transport):
    http = HTTPXWrapper({'tls_verify': False}, {}, transport=capturing_transport)
    assert http.options['verify'] is False


def test_tls_ca_cert_uses_path(capturing_transport):
    http = HTTPXWrapper({'tls_ca_cert': '/etc/ssl/ca.pem'}, {}, transport=capturing_transport)
    assert http.options['verify'] == '/etc/ssl/ca.pem'


def test_tls_client_cert_string(capturing_transport):
    http = HTTPXWrapper({'tls_cert': '/etc/ssl/client.pem'}, {}, transport=capturing_transport)
    assert http.options['cert'] == '/etc/ssl/client.pem'


def test_tls_client_cert_with_key(capturing_transport):
    http = HTTPXWrapper(
        {'tls_cert': '/etc/ssl/client.pem', 'tls_private_key': '/etc/ssl/client.key'},
        {},
        transport=capturing_transport,
    )
    assert http.options['cert'] == ('/etc/ssl/client.pem', '/etc/ssl/client.key')


def test_tls_no_cert_when_not_configured(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
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
    http = HTTPXWrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    assert http.get_header(lookup_name, default=default) == expected


def test_set_header_overrides_existing(capturing_transport):
    http = HTTPXWrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    http.set_header('X-FOO', 'new')
    assert http.get_header('x-foo') == 'new'


def test_remapper_renames_field(capturing_transport):
    remapper = {'ssl_validation': {'name': 'tls_verify'}}
    http = HTTPXWrapper({'ssl_validation': False}, {}, remapper=remapper, transport=capturing_transport)
    assert http.options['verify'] is False


def test_request_rejects_unknown_kwarg(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    with pytest.raises(TypeError, match='proxies'):
        http.get('http://example.test/', proxies={'http': 'http://proxy:8080'})
