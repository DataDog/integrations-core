# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_testing import MockHTTPResponse


def test_mock_http_patches_agentcheck(mock_http):
    check = AgentCheck('test', {}, [{}])
    assert check.http is mock_http


def test_mock_response_json_with_custom_headers():
    headers = {'X-Custom': 'value'}
    response = MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

    assert response.headers['content-type'] == 'application/json'
    assert response.headers['x-custom'] == 'value'


def test_mock_response_json_does_not_mutate_caller_headers():
    headers = {'X-Custom': 'value'}
    MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

    assert list(headers.keys()) == ['X-Custom']


def test_mock_response_file_path(tmp_path):
    f = tmp_path / 'fixture.txt'
    f.write_bytes(b'file content')

    response = MockHTTPResponse(file_path=str(f))
    assert response.content == b'file content'


def test_mock_response_raise_for_status():
    response_404 = MockHTTPResponse(content='Not Found', status_code=404)
    with pytest.raises(HTTPStatusError) as exc_info:
        response_404.raise_for_status()
    assert '404 Client Error' in str(exc_info.value)
    assert exc_info.value.response is response_404

    response_500 = MockHTTPResponse(content='Server Error', status_code=500)
    with pytest.raises(HTTPStatusError) as exc_info:
        response_500.raise_for_status()
    assert '500 Server Error' in str(exc_info.value)
    assert exc_info.value.response is response_500


def test_mock_response_iter_content_chunks():
    response = MockHTTPResponse(content='hello world')

    chunks = list(response.iter_content(chunk_size=5))
    assert chunks == [b'hello', b' worl', b'd']


def test_mock_response_iter_lines_preserves_empty_lines():
    content = 'line1\n\nline3\n'
    response = MockHTTPResponse(content=content)

    lines = list(response.iter_lines())
    assert lines == [b'line1', b'', b'line3']


def test_mock_response_normalize_leading_newline():
    content = '\nActual content'
    response = MockHTTPResponse(content=content)

    assert response.text == 'Actual content'


def test_mock_response_normalize_leading_newline_with_indent():
    content = """
        line one
        line two
    """
    response = MockHTTPResponse(content=content)
    assert response.text == "line one\nline two\n"


def test_mock_response_headers_case_insensitive():
    response = MockHTTPResponse(headers={'Content-Type': 'text/plain', 'X-Custom': 'val'})

    assert response.headers['Content-Type'] == 'text/plain'
    assert response.headers['content-type'] == 'text/plain'
    assert response.headers.get('Content-Type') == 'text/plain'
    assert response.headers.get('cOnTeNt-tYpE') == 'text/plain'


def test_mock_response_headers_update_and_setdefault():
    response = MockHTTPResponse(headers={'Content-Type': 'text/plain'})

    response.headers.update({'X-New': 'new_val'})
    assert response.headers['x-new'] == 'new_val'

    response.headers.setdefault('X-Default', 'default_val')
    assert response.headers['x-default'] == 'default_val'

    response.headers.setdefault('Content-Type', 'should-not-change')
    assert response.headers['content-type'] == 'text/plain'

    response.headers.update([('X-Iter', 'iter_val')])
    assert response.headers['x-iter'] == 'iter_val'


def test_mock_response_links_standard():
    response = MockHTTPResponse(headers={'link': '<http://example.com/page2>; rel=next; type="text/plain"'})
    assert 'next' in response.links
    assert response.links['next']['url'] == 'http://example.com/page2'
    assert response.links['next']['type'] == 'text/plain'


def test_mock_response_links_multiple():
    response = MockHTTPResponse(
        headers={'link': '<http://example.com/page2>; rel=next, <http://example.com/page1>; rel=prev'}
    )
    assert len(response.links) == 2
    assert response.links['next']['url'] == 'http://example.com/page2'
    assert response.links['prev']['url'] == 'http://example.com/page1'


def test_mock_response_links_empty():
    assert MockHTTPResponse().links == {}
    assert MockHTTPResponse(headers={'link': ''}).links == {}


def test_mock_response_links_no_rel_keys_by_url():
    response = MockHTTPResponse(headers={'link': '<http://example.com/page2>; type="text/plain"'})
    assert 'http://example.com/page2' in response.links


def test_mock_response_links_url_with_comma():
    response = MockHTTPResponse(headers={'link': '<http://example.com/path?a=1,2>; rel=next'})
    assert response.links['next']['url'] == 'http://example.com/path?a=1,2'


def test_mock_response_links_cleared_after_header_pop():
    response = MockHTTPResponse(headers={'link': '<http://example.com>; rel=next'})
    assert 'next' in response.links
    response.headers.pop('link')
    assert response.links == {}


def test_mock_response_raw_readable():
    response = MockHTTPResponse(json_data={'key': 'value'})
    assert json.load(response.raw) == {'key': 'value'}
