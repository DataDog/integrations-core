# ABOUTME: Unit tests for the NiFi integration.
# ABOUTME: Tests API auth, health metrics, and cluster health with mocked HTTP responses.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.nifi import NifiCheck


def _make_instance(**overrides):
    instance = {
        'api_url': 'https://nifi.example.com:8443/nifi-api',
        'username': 'admin',
        'password': 'secret',
        'tls_verify': False,
    }
    instance.update(overrides)
    return instance


def _mock_response(status_code=200, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.headers = {}
    resp.content = b'content'
    if status_code >= 400:
        from requests.exceptions import HTTPError

        resp.raise_for_status.side_effect = HTTPError(f'{status_code}')
    else:
        resp.raise_for_status.return_value = None
    return resp


ABOUT_RESPONSE = {'about': {'title': 'NiFi', 'version': '2.8.0'}}

CLUSTER_SUMMARY_CLUSTERED = {
    'clusterSummary': {
        'clustered': True,
        'connectedNodeCount': 3,
        'totalNodeCount': 3,
        'connectedToCluster': True,
    }
}

CLUSTER_SUMMARY_DEGRADED = {
    'clusterSummary': {
        'clustered': True,
        'connectedNodeCount': 2,
        'totalNodeCount': 3,
        'connectedToCluster': True,
    }
}

CLUSTER_SUMMARY_STANDALONE = {
    'clusterSummary': {
        'clustered': False,
        'connectedNodeCount': 0,
        'totalNodeCount': 0,
    }
}


def _build_request_side_effect(responses_by_url):
    """Build a side_effect for requests.Session.request that dispatches by URL substring."""

    def side_effect(method, url, **kwargs):
        for url_part, resp in responses_by_url.items():
            if url_part in url:
                return resp
        raise ValueError(f'Unmocked URL: {method} {url}')

    return side_effect


class TestAuth:
    def test_auth_success(self):
        """Token endpoint returns 201 with raw JWT string."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        with patch('requests.Session.request', return_value=_mock_response(201, text='jwt-token-string')):
            api._authenticate()

        assert api._token == 'jwt-token-string'

    def test_auth_failure(self):
        """Token endpoint returns 403 on bad credentials."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()

        with patch('requests.Session.request', return_value=_mock_response(403)):
            with pytest.raises(Exception):
                api._authenticate()

    def test_token_refresh_on_401(self):
        """First GET returns 401, re-auth succeeds, retry succeeds."""
        check = NifiCheck('nifi', {}, [_make_instance()])
        api = check._get_api()
        api._token = 'expired-token'

        call_count = {'n': 0}
        responses = [
            _mock_response(401),  # first GET (expired token)
            _mock_response(201, text='new-token'),  # POST /access/token
            _mock_response(200, json_data=ABOUT_RESPONSE),  # retry GET
        ]

        def side_effect(*args, **kwargs):
            resp = responses[call_count['n']]
            call_count['n'] += 1
            return resp

        with patch('requests.Session.request', side_effect=side_effect):
            result = api._request('/flow/about')

        assert result == ABOUT_RESPONSE
        assert api._token == 'new-token'


class TestCanConnect:
    def test_can_connect_success(self, dd_run_check, aggregator):
        """Full check run emits can_connect=1 on success."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        side_effect = _build_request_side_effect(
            {
                '/access/token': _mock_response(201, text='test-token'),
                '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
                '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE),
            }
        )

        with patch('requests.Session.request', side_effect=side_effect):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1, tags=['nifi_version:2.8.0'])

    def test_can_connect_failure(self, dd_run_check, aggregator):
        """Connection error emits can_connect=0."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        from requests.exceptions import ConnectionError

        with patch('requests.Session.request', side_effect=ConnectionError('refused')):
            with pytest.raises(Exception):
                dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=0)


class TestClusterHealth:
    def test_cluster_healthy(self, dd_run_check, aggregator):
        """Clustered mode with all nodes connected: is_healthy=1."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        side_effect = _build_request_side_effect(
            {
                '/access/token': _mock_response(201, text='test-token'),
                '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
                '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_CLUSTERED),
            }
        )

        with patch('requests.Session.request', side_effect=side_effect):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.connected_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.total_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.is_healthy', value=1, tags=tags)

    def test_cluster_degraded(self, dd_run_check, aggregator):
        """Clustered mode with missing node: is_healthy=0."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        side_effect = _build_request_side_effect(
            {
                '/access/token': _mock_response(201, text='test-token'),
                '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
                '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_DEGRADED),
            }
        )

        with patch('requests.Session.request', side_effect=side_effect):
            dd_run_check(check)

        tags = ['nifi_version:2.8.0']
        aggregator.assert_metric('nifi.cluster.connected_node_count', value=2, tags=tags)
        aggregator.assert_metric('nifi.cluster.total_node_count', value=3, tags=tags)
        aggregator.assert_metric('nifi.cluster.is_healthy', value=0, tags=tags)

    def test_standalone_no_cluster_metrics(self, dd_run_check, aggregator):
        """Standalone mode: no cluster metrics emitted."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        side_effect = _build_request_side_effect(
            {
                '/access/token': _mock_response(201, text='test-token'),
                '/flow/about': _mock_response(200, json_data=ABOUT_RESPONSE),
                '/flow/cluster/summary': _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE),
            }
        )

        with patch('requests.Session.request', side_effect=side_effect):
            dd_run_check(check)

        aggregator.assert_metric('nifi.can_connect', value=1)
        assert not aggregator.metrics('nifi.cluster.connected_node_count')
        assert not aggregator.metrics('nifi.cluster.total_node_count')
        assert not aggregator.metrics('nifi.cluster.is_healthy')

    def test_version_cached(self, dd_run_check, aggregator):
        """Version is fetched once and cached for subsequent check runs."""
        instance = _make_instance()
        check = NifiCheck('nifi', {}, [instance])

        call_log = []

        def side_effect_factory():
            def side_effect(method, url, **kwargs):
                call_log.append(url)
                if '/access/token' in url:
                    return _mock_response(201, text='test-token')
                elif '/flow/about' in url:
                    return _mock_response(200, json_data=ABOUT_RESPONSE)
                elif '/flow/cluster/summary' in url:
                    return _mock_response(200, json_data=CLUSTER_SUMMARY_STANDALONE)
                raise ValueError(f'Unmocked: {url}')

            return side_effect

        # First run: token + about + cluster
        with patch('requests.Session.request', side_effect=side_effect_factory()):
            dd_run_check(check)

        about_calls_run1 = sum(1 for u in call_log if '/flow/about' in u)
        assert about_calls_run1 == 1

        call_log.clear()

        # Second run: only cluster (about is cached, token already obtained)
        with patch('requests.Session.request', side_effect=side_effect_factory()):
            dd_run_check(check)

        about_calls_run2 = sum(1 for u in call_log if '/flow/about' in u)
        assert about_calls_run2 == 0
