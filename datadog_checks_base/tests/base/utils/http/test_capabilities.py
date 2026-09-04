# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import timedelta

import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.requests_adapter import RequestsResponseAdapter

from . import common
from .common import get_wire_headers

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


class TestClose:
    def test_close_without_session_is_noop(self):
        http = RequestsWrapper({}, {})
        http.close()
        assert http._session is None

    def test_close_closes_underlying_session(self):
        transport = common.RequestsTransport()
        http = common.create_requests_client(transport)

        http.close()

        assert transport.closed

    def test_close_resets_session(self):
        http = RequestsWrapper({}, {})
        first = http.session
        http.close()
        assert http._session is None
        assert http.session is not first

    def test_close_is_idempotent_after_open(self):
        http = RequestsWrapper({}, {})
        assert http.session is not None
        http.close()
        http.close()
        assert http._session is None

    def test_request_succeeds_after_close(self):
        first_transport = common.RequestsTransport()
        first_transport.respond()
        http = RequestsWrapper({}, {})
        http.persist_connections = True
        first = http.session
        first.mount('http://', first_transport)
        http.get('http://example.com')
        http.close()

        second_transport = common.RequestsTransport()
        second_transport.respond()
        second = http.session
        second.mount('http://', second_transport)
        http.get('http://example.com')

        assert len(first_transport.requests) == 1
        assert len(second_transport.requests) == 1
        assert second is not first


class TestDisableAuth:
    def test_disable_auth_overrides_config_basic_auth(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.options['auth'] == ('user', 'pass')
        http.disable_auth()
        assert http.options['auth'] is not None
        assert http.options['auth'] != ('user', 'pass')

    def test_disable_auth_preserves_trust_env(self):
        http = RequestsWrapper({}, {})
        http.disable_auth()
        assert http.trust_env is True

    def test_netrc_header_injected_without_disable_auth(self):
        transport = common.RequestsTransport()
        transport.respond()
        http = common.create_requests_client(transport)
        http.options['auth'] = None

        with mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')):
            http.get('http://example.com')

        assert 'Authorization' in transport.requests[0].headers

    def test_disable_auth_suppresses_netrc_header(self):
        transport = common.RequestsTransport()
        transport.respond()
        http = common.create_requests_client(transport)

        with mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')):
            http.disable_auth()
            http.get('http://example.com')

        assert 'Authorization' not in transport.requests[0].headers

    @pytest.mark.parametrize(
        'location',
        [
            pytest.param('/final', id='same-host'),
            pytest.param('http://redirect.example/final', id='cross-host'),
        ],
    )
    def test_disable_auth_suppresses_netrc_header_after_redirect(self, location):
        transport = common.RequestsTransport()
        transport.respond(status_code=302, headers={'Location': location})
        transport.respond()
        http = RequestsWrapper({}, {})
        http.persist_connections = True
        http.session.mount('http://', transport)

        with mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')):
            http.disable_auth()
            http.get('http://example.com/start')

        assert len(transport.requests) == 2
        assert all('Authorization' not in request.headers for request in transport.requests)

    def test_disable_auth_suppresses_netrc_header_after_redirect_with_injected_session(self):
        transport = common.RequestsTransport()
        transport.respond(status_code=302, headers={'Location': '/final'})
        transport.respond()
        http = common.create_requests_client(transport)

        with mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')):
            http.disable_auth()
            http.get('http://example.com/start')

        assert len(transport.requests) == 2
        assert all('Authorization' not in request.headers for request in transport.requests)


class TestCookies:
    def test_get_cookie_missing_returns_default(self):
        http = RequestsWrapper({}, {})
        assert http.get_cookie('missing') is None
        assert http.get_cookie('missing', 'fallback') == 'fallback'

    def test_get_cookie_returns_value(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('csrftoken', 'abc123')
        value = http.get_cookie('csrftoken')
        assert value == 'abc123'
        assert isinstance(value, str)

    def test_get_cookie_conflict_returns_default(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('dup', 'a', domain='a.example.com')
        http.session.cookies.set('dup', 'b', domain='b.example.com')
        assert http.get_cookie('dup', 'fallback') == 'fallback'

    def test_per_request_cookies_reach_the_request(self):
        http = RequestsWrapper({}, {})

        wire_headers = get_wire_headers(http, cookies={'proxy': 'approved'})

        assert wire_headers['Cookie'] == 'proxy=approved'


class TestTrustEnv:
    def test_trust_env_defaults_to_true(self):
        http = RequestsWrapper({}, {})
        assert http.trust_env is True

    def test_trust_env_propagates_to_existing_session(self):
        http = RequestsWrapper({}, {})
        session = http.session
        http.trust_env = False
        assert http.trust_env is False
        assert session.trust_env is False

    def test_trust_env_applies_to_new_session(self):
        http = RequestsWrapper({}, {})
        http.trust_env = False
        assert http.session.trust_env is False

    def test_trust_env_reset_to_true(self):
        http = RequestsWrapper({}, {})
        http.trust_env = False
        http.trust_env = True
        assert http.session.trust_env is True

    def test_trust_env_adopts_injected_session(self):
        session = requests.Session()
        session.trust_env = False
        http = RequestsWrapper({}, {}, session=session)
        assert http.trust_env is False

    def test_trust_env_defaults_true_when_injected_session_lacks_attribute(self):
        http = RequestsWrapper({}, {}, session=mock.Mock(spec=[]))
        assert http.trust_env is True


class TestShouldBypassProxy:
    def test_no_no_proxy_rules_never_bypasses(self):
        http = RequestsWrapper({}, {})
        assert http.no_proxy_uris is None
        assert http.should_bypass_proxy('http://example.com') is False

    def test_matching_host_bypasses(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': 'example.com'}}, {})
        assert http.should_bypass_proxy('http://example.com/path') is True

    def test_non_matching_host_does_not_bypass(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': 'example.com'}}, {})
        assert http.should_bypass_proxy('http://other.com') is False

    def test_wildcard_bypasses_all(self):
        http = RequestsWrapper({'proxy': {'http': 'http://p:3128', 'no_proxy': '*'}}, {})
        assert http.should_bypass_proxy('http://anything.example') is True


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

    def test_requests_members_are_not_exposed(self):
        transport = common.RequestsTransport()
        transport.respond()
        http = common.create_requests_client(transport)
        response = http.get('http://example.test/items')

        assert not hasattr(response, 'raw')
        assert not hasattr(response, 'request')


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


@pytest.mark.parametrize(
    ('content', 'delimiter', 'decode_unicode', 'expected', 'element_type'),
    [
        (b'', None, False, [], bytes),
        (b'a\n', None, False, [b'a'], bytes),
        (b'a\n\n', None, False, [b'a', b''], bytes),
        (b'a|', b'||', False, [b'a|'], bytes),
        (b'a||', b'||', False, [b'a', b''], bytes),
        ('café\n\n'.encode('utf-8'), None, True, ['café', ''], str),
        ('café||'.encode('utf-8'), '||', True, ['café', ''], str),
    ],
)
def test_requests_iter_lines_contract(
    content: bytes,
    delimiter: bytes | str | None,
    decode_unicode: bool,
    expected: list[bytes | str],
    element_type: type[bytes] | type[str],
) -> None:
    transport = common.RequestsTransport()
    transport.respond(content=content)
    http = common.create_requests_client(transport)
    response = http.get('http://example.test/items', stream=True)

    if decode_unicode:
        response.encoding = 'utf-8'

    actual = list(response.iter_lines(decode_unicode=decode_unicode, delimiter=delimiter))

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
