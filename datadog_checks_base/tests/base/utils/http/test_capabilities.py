# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper, ResponseWrapper
from datadog_checks.base.utils.http_protocol import HTTPResponse

pytestmark = [pytest.mark.unit]


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
