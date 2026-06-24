# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging

import httpx2
import pytest

from datadog_checks.base.utils.httpx2 import HTTPX2Wrapper

HTTP_VERBS = {
    'get': 'GET',
    'post': 'POST',
    'put': 'PUT',
    'delete': 'DELETE',
    'head': 'HEAD',
    'patch': 'PATCH',
    'options_method': 'OPTIONS',
}


@pytest.mark.parametrize('method,verb', HTTP_VERBS.items())
def test_method_dispatches_with_correct_verb(method, verb, captured_requests, capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    fn = getattr(http, method)
    response = fn('http://example.test/path', headers={'X-Test': '1'})

    assert response.status_code == 200
    assert captured_requests[0].method == verb


def test_post_json_body_is_serialized(capturing_transport, captured_requests):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    http.post('http://example.test/path', json={'a': 1, 'b': 'two'})
    req = captured_requests[0]
    assert req.headers['content-type'] == 'application/json'
    assert json.loads(req.content) == {'a': 1, 'b': 'two'}


def test_stream_kwarg_logged_and_dropped(capturing_transport, caplog):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    with caplog.at_level(logging.DEBUG, logger='datadog_checks.base.utils.httpx2'):
        response = http.get('http://example.test/', stream=True)
    assert response.status_code == 200
    assert any('dropping unsupported per-request kwarg: stream' in r.message for r in caplog.records)


def _spy_on_send(http):
    captured = {}
    original_send = http._client.send

    def spy(request, **kwargs):
        captured.update(kwargs)
        return original_send(request, **kwargs)

    http._client.send = spy
    return captured


def test_request_passes_follow_redirects_per_request(capturing_transport):
    http = HTTPX2Wrapper({'allow_redirects': False}, {}, transport=capturing_transport)
    captured = _spy_on_send(http)
    http.get('http://example.test/', follow_redirects=True)
    assert captured['follow_redirects'] is True


def test_request_uses_client_default_follow_redirects_when_omitted(capturing_transport):
    http = HTTPX2Wrapper({}, {}, transport=capturing_transport)
    captured = _spy_on_send(http)
    http.get('http://example.test/')
    assert captured['follow_redirects'] is httpx2.USE_CLIENT_DEFAULT
