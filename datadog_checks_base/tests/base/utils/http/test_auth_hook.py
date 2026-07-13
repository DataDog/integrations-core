# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import parse_qs, urlparse

import mock
import pytest

from datadog_checks.base.utils.http import HTTPRequestAuth, HTTPRequest, RequestsWrapper

pytestmark = [pytest.mark.unit]


class HeaderAuth(HTTPRequestAuth):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __call__(self, request: HTTPRequest) -> None:
        request.headers[self.name] = self.value


class ParamAuth(HTTPRequestAuth):
    def __init__(self, params):
        self.params = params

    def __call__(self, request: HTTPRequest) -> None:
        request.params.update(self.params)


def _sent_request(http, hook):
    """Send a request with the given hook and return the prepared request passed to requests."""
    with mock.patch('requests.Session.get') as get:
        http.get('http://example.com/api', auth=hook)
    _, kwargs = get.call_args
    return kwargs['auth']


class TestAuthHookAdapter:
    def test_hook_is_adapted_to_requests_auth_base(self):
        import requests

        http = RequestsWrapper({}, {})
        adapted = _sent_request(http, HeaderAuth('X-Token', 'secret'))
        assert isinstance(adapted, requests.auth.AuthBase)

    def test_hook_contributes_header(self):
        http = RequestsWrapper({}, {})
        adapted = _sent_request(http, HeaderAuth('X-Token', 'secret'))

        prepared = requests_prepared_request('http://example.com/api')
        adapted(prepared)
        assert prepared.headers['X-Token'] == 'secret'

    def test_hook_contributes_params(self):
        http = RequestsWrapper({}, {})
        adapted = _sent_request(http, ParamAuth({'User': 'admin', 'Password': 'pass'}))

        prepared = requests_prepared_request('http://example.com/api')
        adapted(prepared)
        query = parse_qs(urlparse(prepared.url).query)
        assert query['User'] == ['admin']
        assert query['Password'] == ['pass']

    def test_hook_contributes_both_headers_and_params(self):
        class BothAuth(HTTPRequestAuth):
            def __call__(self, request: HTTPRequest) -> None:
                request.headers['X-Token'] = 'secret'
                request.params['tenant'] = 'acme'

        http = RequestsWrapper({}, {})
        adapted = _sent_request(http, BothAuth())

        prepared = requests_prepared_request('http://example.com/api')
        adapted(prepared)
        assert prepared.headers['X-Token'] == 'secret'
        assert parse_qs(urlparse(prepared.url).query)['tenant'] == ['acme']

    def test_native_auth_is_not_adapted(self):
        http = RequestsWrapper({}, {})
        adapted = _sent_request(http, ('user', 'pass'))
        # A plain requests-native auth value is passed through untouched.
        assert adapted == ('user', 'pass')

    def test_hook_must_implement_call(self):
        with pytest.raises(TypeError):
            HTTPRequestAuth()


def requests_prepared_request(url):
    import requests

    return requests.Request('GET', url).prepare()
