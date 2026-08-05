# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import codecs

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.dev import http as http_testing
from datadog_checks.dev.http import MockHTTPResponse


def test_mock_http_patches_agentcheck(mock_http):
    check = AgentCheck('test', {}, [{}])
    assert check.http is mock_http


def test_mock_http_patches_explicit_agentcheck_client(mock_http):
    check = AgentCheck('test', {}, [{}])
    assert check.create_http_client({'url': 'https://example.test'}) is mock_http


def test_mock_http_supports_options(mock_http):
    response = MockHTTPResponse()
    mock_http.options_method.return_value = response
    check = AgentCheck('test', {}, [{}])

    assert check.http.options_method('https://example.test') is response


def test_mock_http_rejects_off_protocol_attributes(mock_http):
    with pytest.raises(AttributeError, match='session'):
        mock_http.session = object()


@pytest.mark.parametrize('default', [None, 'fallback'])
def test_mock_http_absent_cookie_returns_default(mock_http, default):
    assert mock_http.get_cookie('missing', default) == default


def test_mock_http_get_cookie_accepts_keyword_arguments(mock_http):
    assert mock_http.get_cookie(name='missing', default='fallback') == 'fallback'


def test_mock_http_get_cookie_return_value_is_configurable(mock_http):
    mock_http.get_cookie.return_value = 'token'
    assert mock_http.get_cookie('csrftoken') == 'token'


def test_legacy_mock_response_is_not_exposed():
    assert not hasattr(http_testing, 'MockResponse')


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


def test_mock_response_text_uses_explicit_encoding():
    response = MockHTTPResponse(content='café'.encode('latin-1'))
    response.encoding = 'latin-1'

    assert response.text == 'café'


def test_mock_response_headers_case_insensitive():
    response = MockHTTPResponse(headers={'Content-Type': 'text/plain', 'X-Custom': 'val'})

    assert response.headers['Content-Type'] == 'text/plain'
    assert response.headers['content-type'] == 'text/plain'
    assert response.headers.get('Content-Type') == 'text/plain'
    assert response.headers.get('cOnTeNt-tYpE') == 'text/plain'


def test_mock_response_headers_compare_case_insensitively():
    """Both real backends compare case-insensitively, so a literal that matches live must match here."""
    response = MockHTTPResponse(headers={'Content-Type': 'text/plain'})

    assert response.headers == {'Content-Type': 'text/plain'}
    assert response.headers == {'content-type': 'text/plain'}
    assert response.headers != {'Content-Type': 'text/html'}


def test_mock_http_exposes_tls_config(mock_http):
    """The tls integration reads check.http.tls_config, and the double is sealed against anything else."""
    assert mock_http.tls_config == {}


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


def test_mock_response_get_peer_cert():
    response = MockHTTPResponse()
    assert response.get_peer_cert(binary_form=True) == b'mock-cert'
    assert response.get_peer_cert() == {}


def test_mock_response_blocks_off_protocol_read():
    response = MockHTTPResponse(json_data={'k': 'v'})
    with pytest.raises(AttributeError, match='HTTPResponse protocol'):
        str(response.raw)
    with pytest.raises(AttributeError, match='HTTPResponse protocol'):
        str(response.request)


def test_mock_response_blocks_off_protocol_write():
    response = MockHTTPResponse()
    with pytest.raises(AttributeError, match='HTTPResponse protocol'):
        response.raw = object()


def test_mock_response_promoted_attributes_delegate():
    response = MockHTTPResponse(cookies={'c': '1'}, url='http://x', headers={'link': '<u>; rel=next'})
    assert response.cookies == {'c': '1'}
    assert response.url == 'http://x'
    assert response.links['next']['url'] == 'u'
    response.encoding = 'utf-8'
    assert response.encoding == 'utf-8'


def test_mock_response_raise_for_status_keeps_identity():
    response = MockHTTPResponse(status_code=500)
    with pytest.raises(HTTPStatusError) as exc_info:
        response.raise_for_status()
    assert exc_info.value.response is response


def test_mock_response_reason():
    assert MockHTTPResponse(status_code=200).reason == 'OK'
    assert MockHTTPResponse(status_code=404).reason == 'Not Found'
    # An unknown status code has no canonical reason phrase.
    assert MockHTTPResponse(status_code=599).reason == ''


@pytest.mark.parametrize(
    ('status_code', 'expected'),
    [(200, True), (301, True), (399, True), (400, False), (404, False), (500, False)],
)
def test_mock_response_truthiness_follows_the_status_code(status_code, expected):
    # A response reached through an error handler is sometimes tested for truth rather than for None,
    # and an always-truthy double sends that branch the other way. nutanix's activity monitor picks
    # its log message that way, so a test written on a truthy double pins the wrong message.
    assert bool(MockHTTPResponse(status_code=status_code)) is expected


def test_mock_response_iter_content_whole_content():
    # chunk_size=None yields the entire body as a single chunk.
    assert list(MockHTTPResponse(content='hello world').iter_content()) == [b'hello world']


def test_mock_response_iter_content_empty():
    # Empty content yields nothing and must not hang on a zero-length read.
    assert list(MockHTTPResponse(content='').iter_content()) == []


def test_mock_response_iter_content_decode_unicode():
    # The character set comes from the header, the same place the production backend reads it.
    response = MockHTTPResponse(content='ab', headers={'Content-Type': 'text/plain; charset=utf-8'})

    assert list(response.iter_content(chunk_size=1, decode_unicode=True)) == ['a', 'b']


def test_mock_response_iter_content_decode_unicode_uses_explicit_encoding():
    response = MockHTTPResponse(content='café'.encode('latin-1'))
    response.encoding = 'latin-1'

    assert list(response.iter_content(chunk_size=1, decode_unicode=True)) == ['c', 'a', 'f', 'é']


def test_mock_response_iter_content_decode_unicode_handles_split_code_points():
    response = MockHTTPResponse(content='café')
    response.encoding = 'utf-8'

    assert list(response.iter_content(chunk_size=1, decode_unicode=True)) == ['c', 'a', 'f', 'é']


def test_mock_response_default_iteration():
    # __iter__ mirrors requests.Response: delegates to iter_content(128).
    assert list(MockHTTPResponse(content='abc')) == [b'abc']


def test_mock_response_iter_lines_custom_delimiter():
    response = MockHTTPResponse(content='a|b|c')
    assert list(response.iter_lines(delimiter='|')) == [b'a', b'b', b'c']


def test_mock_response_iter_lines_decode_unicode():
    response = MockHTTPResponse(content='line1\nline2', headers={'Content-Type': 'text/plain; charset=utf-8'})
    assert list(response.iter_lines(decode_unicode=True)) == ['line1', 'line2']


def test_mock_response_iter_lines_decode_unicode_uses_explicit_encoding():
    response = MockHTTPResponse(content='café\nmañana'.encode('latin-1'))
    response.encoding = 'latin-1'

    assert list(response.iter_lines(decode_unicode=True)) == ['café', 'mañana']


@pytest.mark.parametrize('delimiter', [None, '\n'])
def test_mock_response_iter_lines_decode_unicode_handles_multibyte_encoding(delimiter):
    response = MockHTTPResponse(content='café\nmañana'.encode('utf-16'))
    response.encoding = 'utf-16'

    assert list(response.iter_lines(decode_unicode=True, delimiter=delimiter)) == ['café', 'mañana']


def test_mock_response_iter_lines_byte_mode_handles_multibyte_encoding():
    response = MockHTTPResponse(content='café\nmañana'.encode('utf-16'))
    response.encoding = 'utf-16'

    lines = list(response.iter_lines(delimiter='\n'))
    decoder = codecs.getincrementaldecoder('utf-16')()
    decoded_lines = [decoder.decode(line, final=index == len(lines) - 1) for index, line in enumerate(lines)]

    assert decoded_lines == ['café', 'mañana']


def test_mock_response_history_passthrough():
    inner = MockHTTPResponse(status_code=301)
    response = MockHTTPResponse(history=[inner])
    assert response.history == [inner]


def test_mock_response_context_manager_calls_close(mocker):
    response = MockHTTPResponse()
    response.close = mocker.Mock()

    with response as entered:
        assert entered is response

    response.close.assert_called_once_with()


def test_mock_response_satisfies_full_protocol_surface():
    from datadog_checks.dev.http import protocol_members

    response = MockHTTPResponse(json_data={'k': 'v'})
    # Every declared protocol member must be reachable through the enforcing wrapper.
    for name in protocol_members():
        getattr(response, name)
