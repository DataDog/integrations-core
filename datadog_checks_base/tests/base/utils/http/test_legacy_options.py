# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pin the public ``HTTPClient.options`` compatibility surface."""

import mock
import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient
from datadog_checks.base.utils.http import RequestsWrapper

pytestmark = [pytest.mark.unit]


class TestLegacyOptionsSurface:
    def test_wholesale_header_replacement(self):
        http = RequestsWrapper({}, {})
        http.options['headers'] = {'Authorization': 'api-key'}
        assert http.options['headers'] == {'Authorization': 'api-key'}

    def test_replaced_headers_are_visible_through_get_header(self):
        http = RequestsWrapper({}, {})
        http.options['headers'] = {'Authorization': 'api-key'}
        assert http.get_header('authorization') == 'api-key'

    def test_update_clears_configured_auth(self):
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.options['auth'] == ('user', 'pass')
        http.options.update({'auth': None})
        assert http.options['auth'] is None

    def test_nested_header_assignment(self):
        http = RequestsWrapper({}, {})
        http.options['headers']['Authorization'] = 'token'
        assert http.get_header('Authorization') == 'token'

    def test_update_applies_proxies_and_verify(self):
        http = RequestsWrapper({}, {})
        http.options.update({'proxies': {'https': 'http://proxy:3128'}, 'verify': False})
        assert http.options['proxies'] == {'https': 'http://proxy:3128'}
        assert http.options['verify'] is False

    def test_set_header_writes_through_to_options(self):
        http = RequestsWrapper({}, {})
        http.set_header('X-Token', 'abc')
        assert http.options['headers']['X-Token'] == 'abc'


class TestOptionsReachTheWire:
    """Verify post-construction options writes affect requests."""

    def test_replaced_timeout_reaches_the_request(self):
        http = RequestsWrapper({'connect_timeout': 4, 'read_timeout': 9}, {})
        http.options['timeout'] = (1, 2)

        with mock.patch('requests.Session.get') as get:
            http.get('https://www.example.com')

        assert get.call_args.kwargs['timeout'] == (1, 2)

    def test_nested_header_write_reaches_the_request(self):
        http = RequestsWrapper({}, {})
        http.options['headers']['X-Auth-Token'] = 'token'

        with mock.patch('requests.Session.get') as get:
            http.get('https://www.example.com')

        assert get.call_args.kwargs['headers']['X-Auth-Token'] == 'token'

    def test_updated_verify_reaches_the_request(self):
        http = RequestsWrapper({}, {})
        http.options.update({'verify': False})

        with mock.patch('requests.Session.get') as get:
            http.get('https://www.example.com')

        assert get.call_args.kwargs['verify'] is False


class TestFakeHttpLegacyOptions:
    def test_header_views_share_storage(self):
        http = FakeHTTPClient()
        http.options['headers']['X-Token'] = 'abc'
        assert http.get_header('x-token') == 'abc'

        http.set_header('X-Other', 'def')
        assert http.options['headers']['X-Other'] == 'def'

    def test_set_header_collapses_duplicate_spellings(self):
        http = FakeHTTPClient()
        http.options['headers'].update({'x-vault-token': 'stale', 'X-Vault-Token': 'canon'})

        http.set_header('X-Vault-Token', 'fresh')

        assert http.get_header('X-Vault-Token') == 'fresh'
        assert sum(1 for key in http.options['headers'] if key.lower() == 'x-vault-token') == 1
