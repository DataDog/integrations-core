# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import gzip
import io

import pytest
import requests
import urllib3

from datadog_checks.base.utils.http import RequestsWrapper, ResponseSizeLimitExceeded, ResponseWrapper

MIB = 1024 * 1024


def make_response(body, compress=False, encoding='utf-8'):
    headers = {}
    if compress:
        body = gzip.compress(body)
        headers['Content-Encoding'] = 'gzip'

    response = requests.Response()
    response.status_code = 200
    response.url = 'http://localhost/metrics'
    response.encoding = encoding
    response.raw = urllib3.HTTPResponse(
        body=io.BytesIO(body), headers=headers, status=200, preload_content=False, decode_content=True
    )
    return response


@pytest.mark.parametrize(
    'config, expected',
    [
        pytest.param({}, None, id='default'),
        pytest.param({'max_response_size': None}, None, id='none'),
        pytest.param({'max_response_size': 0}, None, id='zero'),
        pytest.param({'max_response_size': -1}, None, id='negative'),
        pytest.param({'max_response_size': 1}, MIB, id='mebibytes'),
        pytest.param({'max_response_size': '0.5'}, MIB // 2, id='string'),
    ],
)
def test_config(config, expected):
    assert RequestsWrapper(config, {}).max_response_size == expected


@pytest.mark.parametrize('compress', [False, True])
@pytest.mark.parametrize('decode_unicode', [False, True])
def test_iter_content_exceeding_limit(compress, decode_unicode):
    response = ResponseWrapper(make_response(b'x' * 10_000, compress=compress), 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded, match='1000 bytes'):
        for _ in response.iter_content(decode_unicode=decode_unicode):
            pass


@pytest.mark.parametrize('compress', [False, True])
def test_iter_content_within_limit(compress):
    response = ResponseWrapper(make_response(b'x' * 1_000, compress=compress), 100, 1_000)

    assert b''.join(response.iter_content()) == b'x' * 1_000


@pytest.mark.parametrize('compress', [False, True])
@pytest.mark.parametrize('decode_unicode', [False, True])
def test_iter_lines_exceeding_limit_without_newline(compress, decode_unicode):
    response = ResponseWrapper(make_response(b'x' * 10_000, compress=compress), 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded):
        for _ in response.iter_lines(decode_unicode=decode_unicode):
            pass


def test_iter_lines_exceeding_limit_with_newlines():
    response = ResponseWrapper(make_response(b'line\n' * 1_000), 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded):
        list(response.iter_lines())


def test_exceeding_limit_closes_response():
    wrapped = make_response(b'x' * 10_000)
    response = ResponseWrapper(wrapped, 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded):
        list(response.iter_lines())

    assert wrapped.raw.closed


@pytest.mark.parametrize(
    'body',
    [
        pytest.param(b'', id='empty'),
        pytest.param(b'one', id='single-line'),
        pytest.param(b'one\ntwo\nthree', id='no-trailing-newline'),
        pytest.param(b'one\ntwo\nthree\n', id='trailing-newline'),
        pytest.param(b'one\r\ntwo\r\n\r\nthree\r\n', id='crlf'),
        pytest.param(b'a' * 250 + b'\n' + b'b' * 250, id='lines-spanning-chunks'),
        pytest.param('caf\u00e9\n\u00fcber\n'.encode(), id='multibyte'),
        pytest.param(('\u00e9' * 300 + '\nend').encode(), id='multibyte-spanning-chunks'),
    ],
)
@pytest.mark.parametrize('compress', [False, True])
@pytest.mark.parametrize('decode_unicode', [False, True])
def test_iter_lines_matches_requests(body, compress, decode_unicode):
    expected = list(make_response(body, compress=compress).iter_lines(100, decode_unicode=decode_unicode))
    response = ResponseWrapper(make_response(body, compress=compress), 100, 10 * MIB)

    assert list(response.iter_lines(decode_unicode=decode_unicode)) == expected


@pytest.mark.parametrize('decode_unicode', [False, True])
def test_iter_lines_custom_delimiter_matches_requests(decode_unicode):
    delimiter = '|' if decode_unicode else b'|'
    body = b'a|b||c|d'
    expected = list(make_response(body).iter_lines(3, decode_unicode=decode_unicode, delimiter=delimiter))
    response = ResponseWrapper(make_response(body), 3, 10 * MIB)

    assert list(response.iter_lines(decode_unicode=decode_unicode, delimiter=delimiter)) == expected


def test_no_limit_is_unrestricted():
    response = ResponseWrapper(make_response(b'x' * 10_000), 100)

    assert sum(len(line) for line in response.iter_lines()) == 10_000


@pytest.mark.parametrize('attribute', ['content', 'text', 'json'])
def test_buffered_read_exceeding_limit(attribute):
    response = ResponseWrapper(make_response(b'x' * 10_000, compress=True), 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded):
        value = getattr(response, attribute)
        if callable(value):
            value()


def test_buffered_read_within_limit():
    response = ResponseWrapper(make_response(b'{"a": 1}', compress=True), 100, 1_000)

    assert response.content == b'{"a": 1}'
    assert response.text == '{"a": 1}'
    assert response.json() == {'a': 1}


def test_file_like_raw_exceeding_limit():
    wrapped = make_response(b'')
    wrapped.raw = io.BytesIO(b'x' * 10_000)
    response = ResponseWrapper(wrapped, 100, 1_000)

    with pytest.raises(ResponseSizeLimitExceeded):
        list(response.iter_lines())


def test_file_like_raw_within_limit():
    wrapped = make_response(b'')
    wrapped.raw = io.BytesIO(b'one\ntwo')
    response = ResponseWrapper(wrapped, 100, 1_000)

    assert list(response.iter_lines()) == [b'one', b'two']


def test_response_without_raw():
    wrapped = requests.Response()
    wrapped.url = 'http://localhost/metrics'

    assert ResponseWrapper(wrapped, 100, 1_000).raw is None
