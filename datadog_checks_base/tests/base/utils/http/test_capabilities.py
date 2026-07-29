# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper, ResponseWrapper
from datadog_checks.base.utils.http_protocol import HTTPResponse, HTTPTimeoutConfig
from datadog_checks.base.utils.tls import TlsConfig
from datadog_checks.dev.http import MockHTTPResponse

pytestmark = [pytest.mark.unit]


class TestHeaderCapabilities:
    def test_get_headers_returns_detached_snapshot(self):
        http = RequestsWrapper({}, {})
        http.set_header('X-Test', 'one')
        snapshot = http.get_headers()
        snapshot['X-Other'] = 'two'
        assert http.get_header('X-Other') is None

    def test_clear_and_update_headers(self):
        http = RequestsWrapper({}, {})
        http.set_header('Accept', 'text/plain')
        http.clear_headers()
        http.update_headers({'X-Token': 'abc'})
        assert http.get_headers() == {'X-Token': 'abc'}

    def test_remove_header_is_case_insensitive(self):
        http = RequestsWrapper({}, {})
        http.set_header('Authorization', 'token')
        http.remove_header('authorization')
        assert http.get_header('Authorization') is None


class TestTimeoutCapabilities:
    def test_default_timeout_exposes_connect_and_read(self):
        http = RequestsWrapper({'timeout': 7, 'connect_timeout': 3, 'read_timeout': 9}, {})
        assert http.default_timeout == HTTPTimeoutConfig(3, 9)

    def test_request_accepts_timeout_config(self):
        http = RequestsWrapper({}, {})
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com', timeout=HTTPTimeoutConfig(1.5, 2.5))
        assert get.call_args.kwargs['timeout'] == (1.5, 2.5)


class TestAuthCapabilities:
    def test_get_basic_auth_returns_configured_tuple(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.get_basic_auth() == ('user', 'pass')

    def test_clear_default_auth_allows_netrc(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        http.clear_default_auth()
        assert http.get_basic_auth() is None
        assert http.get_basic_auth() is None

    def test_clear_default_auth_removes_auth_from_persistent_prepared_request(self):
        http = RequestsWrapper(
            {'username': 'user', 'password': 'pass', 'persist_connections': True},
            {},
        )
        session = http.session
        http.trust_env = False
        http.clear_default_auth()
        captured = {}

        def fake_send(prepared_request, **kwargs):
            captured['request'] = prepared_request
            response = requests.Response()
            response.status_code = 200
            return response

        with mock.patch.object(session, 'send', side_effect=fake_send):
            http.get('http://example.com')

        prepared_request = captured['request']
        assert prepared_request.headers.get('Authorization') is None


class TestTlsAndProxyCapabilities:
    def test_tls_config_reflects_verify_and_cert(self):
        http = RequestsWrapper(
            {
                'tls_verify': True,
                'tls_ca_cert': '/tmp/ca.pem',
                'tls_cert': '/tmp/client.pem',
                'tls_private_key': '/tmp/client.key',
            },
            {},
        )
        tls = http.tls_config
        assert isinstance(tls, TlsConfig)
        assert tls.tls_verify is True
        assert tls.tls_ca_cert == '/tmp/ca.pem'
        assert tls.tls_cert == '/tmp/client.pem'
        assert tls.tls_private_key == '/tmp/client.key'

    def test_proxy_for_url_honors_bypass_rules(self):
        http = RequestsWrapper({'proxy': {'https': 'http://proxy:3128', 'no_proxy': 'example.com'}}, {})
        assert http.proxy_for_url('https://example.com/path') is None
        assert http.proxy_for_url('https://other.com/path') == 'http://proxy:3128'


class TestClose:
    def test_close_without_session_is_noop(self):
        http = RequestsWrapper({}, {})
        # No session has been created yet; closing must not raise.
        http.close()
        assert http._session is None

    def test_close_closes_underlying_session(self):
        http = RequestsWrapper({}, {})
        session = http.session
        with mock.patch.object(session, 'close') as close:
            http.close()
        close.assert_called_once_with()

    def test_close_resets_session(self):
        http = RequestsWrapper({}, {})
        first = http.session
        http.close()
        assert http._session is None
        # A fresh session is created on next access.
        assert http.session is not first

    def test_close_is_idempotent_after_open(self):
        http = RequestsWrapper({}, {})
        # Open a session, then close twice; the second close must be a safe no-op.
        assert http.session is not None
        http.close()
        http.close()
        assert http._session is None

    def test_request_succeeds_after_close(self):
        # The documented contract is that the client stays usable after close(): a subsequent request
        # transparently rebuilds the session and goes through.
        http = RequestsWrapper({}, {})
        http.persist_connections = True
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com')
            first = http.session
            http.close()
            http.get('http://example.com')
            second = http.session
        assert get.call_count == 2
        assert second is not first


class TestDisableAuth:
    def test_disable_auth_overrides_config_basic_auth(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.get_basic_auth() == ('user', 'pass')
        http.disable_auth()
        assert http.get_basic_auth() is None
        with mock.patch('requests.Session.get') as get:
            http.get('http://example.com')
            auth = get.call_args.kwargs['auth']
            assert auth is not None
            assert auth != ('user', 'pass')

    def test_disable_auth_preserves_trust_env(self):
        http = RequestsWrapper({}, {})
        http.disable_auth()
        # Only auth is suppressed. Env proxy and CA bundle resolution must stay on.
        assert http.trust_env is True

    def test_netrc_header_injected_without_disable_auth(self):
        # Guards the regression: with auth=None and trust_env on, a matching .netrc entry injects Authorization.
        http = RequestsWrapper({}, {})
        http.clear_default_auth()
        captured = {}

        def fake_send(session_self, request, **kwargs):
            captured['headers'] = dict(request.headers)
            response = requests.Response()
            response.status_code = 200
            return response

        with (
            mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')),
            mock.patch('requests.sessions.Session.send', new=fake_send),
        ):
            http.get('http://example.com')

        assert 'Authorization' in captured['headers']

    def test_disable_auth_suppresses_netrc_header(self):
        http = RequestsWrapper({}, {})
        captured = {}

        def fake_send(session_self, request, **kwargs):
            captured['headers'] = dict(request.headers)
            response = requests.Response()
            response.status_code = 200
            return response

        with (
            mock.patch('requests.sessions.get_netrc_auth', return_value=('netrc-user', 'netrc-pass')),
            mock.patch('requests.sessions.Session.send', new=fake_send),
        ):
            http.disable_auth()
            http.get('http://example.com')

        # The truthy no-op auth short-circuits requests' .netrc lookup, so no Authorization header goes out.
        assert 'Authorization' not in captured['headers']


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
        # Same cookie name on multiple domains makes RequestsCookieJar.get raise
        # CookieConflictError. get_cookie must still honor its value-or-default contract.
        http.session.cookies.set('dup', 'a', domain='a.example.com')
        http.session.cookies.set('dup', 'b', domain='b.example.com')
        assert http.get_cookie('dup', 'fallback') == 'fallback'


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
        # Session created after the setting must honor it.
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
        # The reported value must match the injected session, not the default True.
        assert http.trust_env is False

    def test_trust_env_defaults_true_when_injected_session_lacks_attribute(self):
        # A duck-typed session without trust_env must fall back to the True default.
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


class TestClientProtocolSurface:
    def test_client_capabilities_declared(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        for name in ('ignore_tls_warning', 'persist_connections'):
            assert name in HTTPClient.__annotations__, f'{name} missing from HTTPClient'
        assert callable(HTTPClient.should_bypass_proxy)

    def test_wrapper_satisfies_client_surface(self):
        from datadog_checks.base.utils.http_protocol import HTTPClient

        http = RequestsWrapper({}, {})
        for name in HTTPClient.__annotations__:
            assert hasattr(http, name), f'RequestsWrapper missing attribute {name}'
        for name in vars(HTTPClient):
            if not name.startswith('_'):
                assert hasattr(http, name), f'RequestsWrapper missing member {name}'


class TestResponseProtocolSurface:
    def test_promoted_attributes_declared(self):
        annotations = HTTPResponse.__annotations__
        for name in ('encoding', 'elapsed', 'cookies', 'links', 'url', 'history'):
            assert name in annotations, f'{name} missing from HTTPResponse'

    def test_get_peer_cert_declared(self):
        assert callable(HTTPResponse.get_peer_cert)

    def test_context_manager_closes_underlying_response(self):
        response = requests.Response()
        response.close = mock.Mock()
        wrapper = ResponseWrapper(response, 1024)

        with wrapper as entered:
            assert entered is wrapper

        response.close.assert_called_once_with()


@pytest.mark.parametrize('backend', ['requests', 'mock'])
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
def test_iter_lines_contract(
    backend: str,
    content: bytes,
    delimiter: bytes | str | None,
    decode_unicode: bool,
    expected: list[bytes | str],
    element_type: type[bytes] | type[str],
) -> None:
    if backend == 'requests':
        raw_response = requests.Response()
        raw_response._content = content
        raw_response._content_consumed = True
        response = ResponseWrapper(raw_response, 1024)
    else:
        response = MockHTTPResponse(content=content)

    if decode_unicode:
        response.encoding = 'utf-8'

    actual = list(response.iter_lines(decode_unicode=decode_unicode, delimiter=delimiter))

    assert actual == expected
    assert [type(line) for line in actual] == [element_type] * len(expected)


class TestPeerCert:
    def test_returns_cert_from_connection_socket(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = b'der-bytes'
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert(binary_form=True) == b'der-bytes'
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=True)

    def test_returns_decoded_cert_with_default_binary_form(self):
        response = mock.Mock()
        response.raw.connection.sock.getpeercert.return_value = {'subject': ()}
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() == {'subject': ()}
        response.raw.connection.sock.getpeercert.assert_called_once_with(binary_form=False)

    def test_returns_none_when_socket_absent(self):
        response = mock.Mock()
        response.raw.connection.sock = None
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() is None

    def test_returns_none_for_non_tls_socket(self):
        # A plain http:// connection exposes a bare socket with no getpeercert; must return None, not raise.
        response = mock.Mock()
        response.raw.connection.sock = object()
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.get_peer_cert() is None


class TestHistory:
    def test_history_items_are_wrapped(self):
        redirect = mock.Mock()
        redirect.status_code = 301
        final = mock.Mock()
        final.history = [redirect]
        wrapper = ResponseWrapper(final, 1024)
        history = wrapper.history
        assert len(history) == 1
        assert isinstance(history[0], ResponseWrapper)
        assert history[0].status_code == 301

    def test_history_item_translates_raise_for_status(self):
        from datadog_checks.base.utils.http_exceptions import HTTPStatusError

        redirect = mock.Mock()
        redirect.raise_for_status.side_effect = requests.exceptions.HTTPError('boom')
        final = mock.Mock()
        final.history = [redirect]
        wrapper = ResponseWrapper(final, 1024)
        # A raw requests error on a history item must surface as the translated agnostic exception.
        with pytest.raises(HTTPStatusError):
            wrapper.history[0].raise_for_status()

    def test_empty_history(self):
        response = mock.Mock()
        response.history = []
        wrapper = ResponseWrapper(response, 1024)
        assert wrapper.history == []
