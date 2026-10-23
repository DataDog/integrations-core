# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientReadTimeoutError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('version', [1, 2])
def test_openmetrics_collection(aggregator, dd_run_check, fake_http, fake_http_response, check, version):
    endpoint = 'http://haproxy:8404/metrics'
    instance = (
        {'use_prometheus': True, 'prometheus_url': endpoint}
        if version == 1
        else {'use_openmetrics': True, 'openmetrics_endpoint': endpoint}
    )
    fake_http_response(endpoint, '# TYPE haproxy_process_nbthread gauge\nhaproxy_process_nbthread 4\n')
    dd_run_check(check(instance))
    aggregator.assert_metric('haproxy.process.nbthread', value=4)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]


@pytest.mark.parametrize('version', [1, 2])
def test_openmetrics_timeout(aggregator, dd_run_check, fake_http, check, version):
    endpoint = 'http://haproxy:8404/metrics'
    instance = (
        {'use_prometheus': True, 'prometheus_url': endpoint}
        if version == 1
        else {'use_openmetrics': True, 'openmetrics_endpoint': endpoint}
    )
    fake_http.register_response('GET', endpoint, HTTPClientReadTimeoutError('unavailable'))
    with pytest.raises(Exception, match='unavailable'):
        dd_run_check(check(instance))
    health_check = 'haproxy.prometheus.health' if version == 1 else 'haproxy.openmetrics.health'
    aggregator.assert_service_check(health_check, 2)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', endpoint)]
