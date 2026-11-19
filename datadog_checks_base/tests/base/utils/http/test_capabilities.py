# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
import requests

from datadog_checks.base.utils.http import RequestsWrapper

from . import common
from .common import get_wire_headers

pytestmark = [pytest.mark.unit]


class TestClose:
    def test_close_closes_underlying_session(self):
        transport = common.RequestsTransport()
        http = common.create_requests_client(transport)

        http.close()

        assert transport.closed

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
    @pytest.mark.parametrize('existing_session', [False, True], ids=['fresh-session', 'existing-session'])
    def test_disable_auth_overrides_config_basic_auth(self, existing_session):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        if existing_session:
            assert get_wire_headers(http)['Authorization'] == 'Basic dXNlcjpwYXNz'

        http.disable_auth()

        assert 'Authorization' not in get_wire_headers(http)
        assert 'Authorization' not in get_wire_headers(http, auth=None)

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

    def test_trust_env_adopts_injected_session(self):
        session = requests.Session()
        session.trust_env = False
        http = RequestsWrapper({}, {}, session=session)
        assert http.trust_env is False

    def test_trust_env_defaults_true_when_injected_session_lacks_attribute(self):
        http = RequestsWrapper({}, {}, session=mock.Mock(spec=[]))
        assert http.trust_env is True
