# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_testing import MockHTTPResponse


class TestMockHTTPFixture:
    def test_patches_agentcheck_http(self, mock_http):
        check = AgentCheck('test', {}, [{}])
        assert check.http is mock_http


class TestMockHTTPResponseBasics:
    def test_default_status_code(self):
        response = MockHTTPResponse(content='test')

        assert response.status_code == 200


class TestMockHTTPResponseJSON:
    def test_json_with_custom_headers(self):
        headers = {'X-Custom': 'value'}
        response = MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

        assert response.headers['content-type'] == 'application/json'
        assert response.headers['x-custom'] == 'value'

    def test_json_does_not_mutate_caller_headers(self):
        headers = {'X-Custom': 'value'}
        MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

        assert list(headers.keys()) == ['X-Custom']

    def test_header_keys_are_lowercased(self):
        response = MockHTTPResponse(content='ok', headers={'Content-Type': 'text/plain'})

        assert response.headers['content-type'] == 'text/plain'
        assert response.headers.get('content-type') == 'text/plain'
        assert 'content-type' in response.headers
        assert 'Content-Type' not in response.headers


class TestMockHTTPResponseFilePath:
    def test_file_path_reads_content(self, tmp_path):
        f = tmp_path / 'fixture.txt'
        f.write_bytes(b'file content')

        response = MockHTTPResponse(file_path=str(f))
        assert response.content == b'file content'


class TestMockHTTPResponseStatus:
    def test_2xx_does_not_raise(self):
        response = MockHTTPResponse(content='ok', status_code=200)
        response.raise_for_status()  # must not raise

    def test_client_error_raises(self):
        response = MockHTTPResponse(content='Not Found', status_code=404)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '404 Client Error' in str(exc_info.value)
        assert exc_info.value.response is response

    def test_server_error_raises(self):
        response = MockHTTPResponse(content='Server Error', status_code=500)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '500 Server Error' in str(exc_info.value)
        assert exc_info.value.response is response


class TestMockHTTPResponseStreaming:
    def test_iter_content_chunks_by_size(self):
        response = MockHTTPResponse(content='hello world')

        chunks = list(response.iter_content(chunk_size=5))
        assert chunks == [b'hello', b' worl', b'd']

    def test_iter_lines_preserves_empty_lines(self):
        content = 'line1\n\nline3\n'
        response = MockHTTPResponse(content=content)

        lines = list(response.iter_lines())
        assert lines == [b'line1', b'', b'line3']

    def test_iter_lines_decode_unicode(self):
        response = MockHTTPResponse(content='line1\nline2')

        lines = list(response.iter_lines(decode_unicode=True))
        assert lines == ['line1', 'line2']

    def test_iter_lines_custom_delimiter(self):
        response = MockHTTPResponse(content='a|b|c')

        lines = list(response.iter_lines(delimiter='|'))
        assert lines == [b'a', b'b', b'c']


class TestMockHTTPResponseNormalization:
    def test_normalize_leading_newline(self):
        content = '\nActual content'
        response = MockHTTPResponse(content=content)

        assert response.text == 'Actual content'
