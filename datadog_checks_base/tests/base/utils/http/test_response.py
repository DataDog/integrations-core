# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from datetime import timedelta

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_protocol import HTTPResponse
from datadog_checks.base.utils.requests_adapter import RequestsResponseAdapter

from . import common

pytestmark = [pytest.mark.unit]


def test_requests_transport_builds_response_through_requests():
    transport = common.RequestsTransport()
    transport.respond(
        status_code=202,
        content=b'{"result": "ok"}',
        headers={
            'Content-Type': 'application/json',
            'Link': '<http://example.test/items?page=2>; rel="next"',
        },
    )
    http = common.create_requests_client(transport)

    response = http.get('http://example.test/items')

    assert response.status_code == 202
    assert response.content == b'{"result": "ok"}'
    assert response.text == '{"result": "ok"}'
    assert response.json() == {'result': 'ok'}
    assert response.headers['content-type'] == 'application/json'
    assert response.encoding == 'utf-8'
    assert response.elapsed >= timedelta()
    assert response.ok
    assert response.reason == 'Accepted'
    assert response.url == 'http://example.test/items'
    assert response.links == {'next': {'url': 'http://example.test/items?page=2', 'rel': 'next'}}
    assert len(transport.requests) == 1


class TestResponseProtocolSurface:
    def test_context_manager_closes_underlying_response(self):
        transport = common.RequestsTransport()
        transport.respond(content=b'body')
        http = common.create_requests_client(transport)
        response = http.get('http://example.test/items', stream=True)
        raw_response = transport.raw_responses[0]

        with response as entered:
            assert entered is response

        assert raw_response.closed
        assert raw_response.released


@pytest.mark.parametrize(
    ('headers', 'expected'),
    [
        (None, None),
        ({'Content-Type': 'application/octet-stream'}, None),
        ({'Content-Type': 'text/plain'}, 'ISO-8859-1'),
        ({'Content-Type': 'text/plain; charset=latin-1'}, 'latin-1'),
        ({'Content-Type': 'application/json'}, 'utf-8'),
        ({'Content-Type': 'application/openmetrics-text; version=1.0.0'}, 'ISO-8859-1'),
        ({'Content-Type': 'TEXT/PLAIN; CHARSET=UTF-8'}, 'UTF-8'),
    ],
)
def test_requests_encoding_derived_from_content_type(headers, expected):
    transport = common.RequestsTransport()
    transport.respond(content=b'abc', headers=headers)
    http = common.create_requests_client(transport)

    response = http.get('http://example.test/items')

    assert response.encoding == expected


def test_requests_decode_unicode_yields_bytes_when_the_encoding_is_undetermined():
    content = 'a: café\nb: 2'.encode('utf-8')
    transport = common.RequestsTransport()
    transport.respond(content=content)
    transport.respond(content=content)
    http = common.create_requests_client(transport)
    lines_response = http.get('http://example.test/lines', stream=True)
    chunks_response = http.get('http://example.test/chunks', stream=True)

    assert lines_response.encoding is None
    assert chunks_response.encoding is None
    assert list(lines_response.iter_lines(decode_unicode=True)) == [b'a: caf\xc3\xa9', b'b: 2']
    assert list(chunks_response.iter_content(chunk_size=4, decode_unicode=True)) == [
        b'a: c',
        b'af\xc3\xa9',
        b'\nb: ',
        b'2',
    ]


def _requests_response(content: bytes) -> RequestsResponseAdapter:
    transport = common.RequestsTransport()
    transport.respond(content=content)
    http = common.create_requests_client(transport)
    return http.get('http://example.test/items', stream=True)


@pytest.mark.parametrize(
    'make_response',
    [
        pytest.param(_requests_response, id='requests'),
        pytest.param(lambda content: FakeHTTPResponse(content=content), id='fake'),
    ],
)
@pytest.mark.parametrize(
    ('content', 'decode_unicode', 'expected', 'element_type'),
    [
        (b'', False, [], bytes),
        (b'a\n', False, [b'a'], bytes),
        (b'a\n\n', False, [b'a', b''], bytes),
        ('café\n\n'.encode('utf-8'), True, ['café', ''], str),
    ],
)
def test_iter_lines_contract(
    make_response: Callable[[bytes], HTTPResponse],
    content: bytes,
    decode_unicode: bool,
    expected: list[bytes | str],
    element_type: type[bytes] | type[str],
):
    response = make_response(content)

    if decode_unicode:
        response.encoding = 'utf-8'

    actual = list(response.iter_lines(decode_unicode=decode_unicode))

    assert actual == expected
    assert [type(line) for line in actual] == [element_type] * len(expected)


class TestPeerCert:
    def test_returns_cert_from_connection_socket(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = b'der-bytes'
        adapter = RequestsResponseAdapter(response, 1024)
        assert adapter.get_peer_cert(binary_form=True) == b'der-bytes'
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=True)

    def test_returns_decoded_cert_with_default_binary_form(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = {'subject': ()}
        adapter = RequestsResponseAdapter(response, 1024)
        assert adapter.get_peer_cert() == {'subject': ()}
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=False)

    def test_returns_none_when_socket_absent(self):
        response = mock.Mock()
        response.raw.connection.sock = None
        adapter = RequestsResponseAdapter(response, 1024)
        assert adapter.get_peer_cert() is None

    def test_returns_none_for_non_tls_socket(self):
        response = mock.Mock()
        response.raw.connection.sock = object()
        adapter = RequestsResponseAdapter(response, 1024)
        assert adapter.get_peer_cert() is None


class TestHistory:
    def test_history_items_are_wrapped(self):
        transport = common.RequestsTransport()
        transport.respond(status_code=302, headers={'Location': '/final'})
        transport.respond(content=b'complete')
        http = common.create_requests_client(transport)

        response = http.get('http://example.test/start')

        history = response.history
        assert len(history) == 1
        assert isinstance(history[0], RequestsResponseAdapter)
        assert history[0].status_code == 302
        assert history[0].url == 'http://example.test/start'
        assert response.url == 'http://example.test/final'

    def test_empty_history(self):
        transport = common.RequestsTransport()
        transport.respond()
        http = common.create_requests_client(transport)

        response = http.get('http://example.test/items')

        assert response.history == []
