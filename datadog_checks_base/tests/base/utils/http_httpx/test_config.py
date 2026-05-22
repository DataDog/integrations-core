# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_options_dict_shape(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    options = http.options
    assert 'auth' in options
    assert 'cert' in options
    assert 'headers' in options
    assert 'timeout' in options
    assert 'verify' in options
    assert 'allow_redirects' in options


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


def test_timeout_default(capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    timeout = http.options['timeout']
    assert isinstance(timeout, tuple) and len(timeout) == 2


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


def test_get_header_case_insensitive(capturing_transport):
    http = HTTPXWrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    assert http.get_header('x-foo') == 'bar'
    assert http.get_header('X-FOO') == 'bar'
    assert http.get_header('missing') is None
    assert http.get_header('missing', default='fallback') == 'fallback'


def test_set_header_overrides_existing(capturing_transport):
    http = HTTPXWrapper({'extra_headers': {'X-Foo': 'bar'}}, {}, transport=capturing_transport)
    http.set_header('X-FOO', 'new')
    assert http.get_header('x-foo') == 'new'


def test_remapper_renames_field(capturing_transport):
    remapper = {'ssl_validation': {'name': 'tls_verify'}}
    http = HTTPXWrapper({'ssl_validation': False}, {}, remapper=remapper, transport=capturing_transport)
    assert http.options['verify'] is False
