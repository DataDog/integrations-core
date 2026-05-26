# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_httpx import HTTPXWrapper

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
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    fn = getattr(http, method)
    response = fn('http://example.test/path', headers={'X-Test': '1'})

    assert response.status_code == 200
    assert captured_requests[0].method == verb


def test_post_json_body_is_serialized(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.post('http://example.test/path', json={'a': 1, 'b': 'two'})
    req = captured_requests[0]
    assert req.headers['content-type'] == 'application/json'
    assert b'"a":' in req.content
    assert b'"b":' in req.content
