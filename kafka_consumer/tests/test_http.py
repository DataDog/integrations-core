# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError, HTTPClientReadTimeoutError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('oauth', [False, True])
def test_empty_connect_worker(aggregator, datadog_agent, fake_http, fake_http_response, check, kafka_instance, oauth):
    url = 'http://connect:8083'
    kafka_instance.update(kafka_connect_url=url, enable_kafka_console=True)
    expected = []
    if oauth:
        kafka_instance['kafka_connect_oauth_token_provider'] = {
            'url': 'http://auth/token',
            'client_id': 'client',
            'client_secret': 'secret',
        }
        fake_http_response('http://auth/token', method='POST', json_data={'access_token': 'token', 'expires_in': 300})
        expected.append(('POST', 'http://auth/token'))
    fake_http_response(url + '/connectors', json_data={}, match_options={'params': {'expand': ['info', 'status']}})
    fake_http_response(url + '/connector-plugins', json_data=[])
    collector = check(kafka_instance)._connector_collector
    assert collector.collect('cluster-1') == {url: True}
    aggregator.assert_metric('kafka.connector.count', value=0)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == expected + [
        ('GET', url + '/connectors'),
        ('GET', url + '/connector-plugins'),
    ]
    if oauth:
        token_request, connectors, plugins = fake_http.requests
        assert token_request.options['auth'] == ('client', 'secret')
        assert token_request.options['data'] == {'grant_type': 'client_credentials'}
        assert (
            connectors.options['extra_headers'] == plugins.options['extra_headers'] == {'Authorization': 'Bearer token'}
        )


@pytest.mark.parametrize('error', [HTTPClientConnectionError, HTTPClientReadTimeoutError])
def test_connect_worker_failure(fake_http, check, kafka_instance, error):
    url = 'http://connect:8083'
    kafka_instance.update(kafka_connect_url=url, enable_kafka_console=True)
    fake_http.register_response('GET', url + '/connectors', error('unavailable'))
    collector = check(kafka_instance)._connector_collector
    assert collector.collect('cluster-1') == {url: False}
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', url + '/connectors')]
