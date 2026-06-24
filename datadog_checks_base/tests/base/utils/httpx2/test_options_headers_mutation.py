# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper


def test_options_headers_setitem_reaches_wire(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers']['X-Token'] = 'after-init'
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-token'] == 'after-init'


def test_options_headers_update_reaches_wire(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers'].update({'X-Token': 'after-init', 'X-Extra': 'two'})
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-token'] == 'after-init'
    assert captured_requests[0].headers['x-extra'] == 'two'


def test_options_headers_whole_dict_replace_reaches_wire(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers'] = {'X-Token': 'after-init'}
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-token'] == 'after-init'


def test_options_headers_mid_stream_mutation_observed(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers']['X-Token'] = 'first'
    http.get('http://example.test/')
    http.options['headers']['X-Token'] = 'second'
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-token'] == 'first'
    assert captured_requests[1].headers['x-token'] == 'second'


def test_set_header_still_works_after_change(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.set_header('X-Token', 'set-via-helper')
    http.get('http://example.test/')
    assert captured_requests[0].headers['x-token'] == 'set-via-helper'


def test_per_call_headers_override_options_headers(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers']['X-Token'] = 'wrapper-default'
    http.get('http://example.test/', headers={'X-Token': 'per-call'})
    assert captured_requests[0].headers['x-token'] == 'per-call'


def test_extra_headers_override_per_call_headers_with_options_default(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers']['X-Token'] = 'wrapper-default'
    http.get(
        'http://example.test/',
        headers={'X-Token': 'per-call'},
        extra_headers={'X-Token': 'per-call-extra'},
    )
    assert captured_requests[0].headers['x-token'] == 'per-call-extra'


def test_options_headers_case_insensitive_collapse_with_per_call(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.options['headers']['X-FOO'] = 'a'
    http.get('http://example.test/', headers={'x-foo': 'b'})
    sent = captured_requests[0].headers
    assert sent.get_list('x-foo') == ['b']
