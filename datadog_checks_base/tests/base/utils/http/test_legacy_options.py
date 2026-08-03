# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pin the public ``options`` dict on the HTTP client.

Integrations outside this repository read and mutate ``self.http.options`` directly, so the attribute
is part of the client's public surface rather than an implementation detail. Each test below mirrors a
real call shape found in integrations-extras or marketplace, so removing or privatizing ``options``
again fails here instead of at a customer's next Agent upgrade.
"""

import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_protocol import HTTPClient

pytestmark = [pytest.mark.unit]


class TestLegacyOptionsSurface:
    def test_options_is_a_plain_mutable_dict(self):
        http = RequestsWrapper({}, {})
        assert isinstance(http.options, dict)

    def test_protocol_declares_options(self):
        assert 'options' in HTTPClient.__annotations__

    def test_wholesale_header_replacement(self):
        # radarr and sonarr do this inside __init__, so an AttributeError here means the check cannot
        # be constructed at all and the integration reports nothing.
        http = RequestsWrapper({}, {})
        http.options['headers'] = {'Authorization': 'api-key'}
        assert http.options['headers'] == {'Authorization': 'api-key'}

    def test_replaced_headers_are_visible_through_get_header(self):
        http = RequestsWrapper({}, {})
        http.options['headers'] = {'Authorization': 'api-key'}
        assert http.get_header('authorization') == 'api-key'

    def test_connect_timeout_read_by_index(self):
        # eventstore reads options['timeout'][0]; riak_repl reads the whole tuple.
        http = RequestsWrapper({'connect_timeout': 4, 'read_timeout': 9}, {})
        assert http.options['timeout'] == (4, 9)
        assert http.options['timeout'][0] == 4

    def test_update_clears_configured_auth(self):
        # crest_data_systems_claroty_ctd drops config auth before applying a bearer token.
        http = RequestsWrapper({'username': 'user', 'password': 'pass'}, {})
        assert http.options['auth'] == ('user', 'pass')
        http.options.update({'auth': None})
        assert http.options['auth'] is None

    def test_nested_header_assignment(self):
        http = RequestsWrapper({}, {})
        http.options['headers']['Authorization'] = 'token'
        assert http.get_header('Authorization') == 'token'

    def test_update_applies_proxies_and_verify(self):
        # netwrix_auditor, zoho_desk and miro all route through options.update().
        http = RequestsWrapper({}, {})
        http.options.update({'proxies': {'https': 'http://proxy:3128'}, 'verify': False})
        assert http.options['proxies'] == {'https': 'http://proxy:3128'}
        assert http.options['verify'] is False

    def test_set_header_writes_through_to_options(self):
        # The retained header capability and the legacy dict must share one storage location.
        http = RequestsWrapper({}, {})
        http.set_header('X-Token', 'abc')
        assert http.options['headers']['X-Token'] == 'abc'

    def test_tls_config_is_a_mapping_of_tls_fields(self):
        http = RequestsWrapper({'tls_ca_cert': '/tmp/ca.pem'}, {})
        assert isinstance(http.tls_config, dict)
        assert http.tls_config['tls_ca_cert'] == '/tmp/ca.pem'


class TestMockHttpLegacyOptions:
    """The shared test double has to expose the same surface, or downstream-shaped tests cannot run."""

    def test_mock_exposes_options(self, mock_http):
        assert isinstance(mock_http.options, dict)

    def test_mock_header_views_share_storage(self, mock_http):
        mock_http.options['headers']['X-Token'] = 'abc'
        assert mock_http.get_header('x-token') == 'abc'

        mock_http.set_header('X-Other', 'def')
        assert mock_http.options['headers']['X-Other'] == 'def'
