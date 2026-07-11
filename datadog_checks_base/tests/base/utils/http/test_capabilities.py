# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base.utils.http import RequestsWrapper

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
        http.session
        http.close()
        http.close()
        assert http._session is None


class TestCookies:
    def test_get_cookie_missing_returns_default(self):
        http = RequestsWrapper({}, {})
        assert http.get_cookie('missing') is None
        assert http.get_cookie('missing', 'fallback') == 'fallback'

    def test_get_cookie_returns_value(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('csrftoken', 'abc123')
        assert http.get_cookie('csrftoken') == 'abc123'

    def test_get_cookie_returns_plain_string(self):
        http = RequestsWrapper({}, {})
        http.session.cookies.set('sid', 'xyz')
        value = http.get_cookie('sid')
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
