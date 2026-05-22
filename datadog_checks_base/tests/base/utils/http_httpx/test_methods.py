# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_httpx import HTTPXWrapper

METHODS = ['get', 'post', 'put', 'delete', 'head', 'patch', 'options_method']
HTTP_VERBS = {
    'get': 'GET',
    'post': 'POST',
    'put': 'PUT',
    'delete': 'DELETE',
    'head': 'HEAD',
    'patch': 'PATCH',
    'options_method': 'OPTIONS',
}


@pytest.mark.parametrize('method', METHODS)
def test_method_happy_path(method, captured_requests, capturing_transport):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    fn = getattr(http, method)
    response = fn('http://example.test/path', headers={'X-Test': '1'})

    assert response.status_code == 200
    assert len(captured_requests) == 1
    assert captured_requests[0].method == HTTP_VERBS[method]
    assert str(captured_requests[0].url) == 'http://example.test/path'


@pytest.mark.parametrize('method', METHODS)
def test_method_5xx_does_not_raise_unless_asked(method, status_transport_factory):
    transport = status_transport_factory(500, b'oops')
    http = HTTPXWrapper({}, {}, transport=transport)
    fn = getattr(http, method)
    response = fn('http://example.test/path')
    assert response.status_code == 500


@pytest.mark.parametrize('method', METHODS)
def test_method_raise_for_status_propagates(method, status_transport_factory):
    transport = status_transport_factory(503, b'server unavailable')
    http = HTTPXWrapper({}, {}, transport=transport)
    fn = getattr(http, method)
    response = fn('http://example.test/path')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_post_json_body_is_serialized(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.post('http://example.test/path', json={'a': 1, 'b': 'two'})
    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers['content-type'] == 'application/json'
    assert b'"a":' in req.content
    assert b'"b":' in req.content


def test_get_query_params_forwarded(capturing_transport, captured_requests):
    http = HTTPXWrapper({}, {}, transport=capturing_transport)
    http.get('http://example.test/path', params={'foo': 'bar', 'baz': '1'})
    assert captured_requests[0].url.params['foo'] == 'bar'
    assert captured_requests[0].url.params['baz'] == '1'
