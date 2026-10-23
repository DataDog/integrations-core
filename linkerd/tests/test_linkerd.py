# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPClientConnectionError
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.linkerd import LinkerdCheck

from .common import (
    EXPECTED_METRICS_V2,
    EXPECTED_METRICS_V2_E2E,
    EXPECTED_METRICS_V2_NEW,
    HERE,
    LINKERD_FIXTURE_VALUES,
    MOCK_INSTANCE,
    MOCK_INSTANCE_NEW,
    OPTIONAL_METRICS_V2_E2E,
)

# The fixture runs five Linkerd control-plane proxies and four Emojivoto proxies.
LINKERD_DISCOVERY_INSTANCES = 9


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def get_response(filename):
    metrics_file_path = get_fixture_path(filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


def test_linkerd(aggregator, dd_run_check, fake_http, fake_http_response):
    """
    Test the full check
    """
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    fake_http_response('http://fake.tld/prometheus', get_response('linkerd.txt'))
    dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://fake.tld/prometheus')]

    for metric in LINKERD_FIXTURE_VALUES:
        aggregator.assert_metric(metric, LINKERD_FIXTURE_VALUES[metric])

    aggregator.assert_metric('linkerd.prometheus.health', metric_type=aggregator.GAUGE)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=check.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_linkerd_v2(aggregator, dd_run_check, fake_http, fake_http_response):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    fake_http_response('http://fake.tld/prometheus', get_response('linkerd_v2.txt'))
    dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://fake.tld/prometheus')]

    for metric_name, metric_type in EXPECTED_METRICS_V2.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=LinkerdCheck.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_linkerd_v2_new(aggregator, dd_run_check, fake_http, fake_http_response):
    fake_http_response('http://fake.tld/prometheus', get_response('linkerd_v2.txt'))
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE_NEW])
    dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://fake.tld/prometheus')]

    for metric_name, metric_type in EXPECTED_METRICS_V2_NEW.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.openmetrics.health', status=LinkerdCheck.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_openmetrics_error(dd_run_check, fake_http):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    fake_http.register_response('GET', 'http://fake.tld/prometheus', HTTPClientConnectionError('unavailable'))
    with pytest.raises(Exception, match='unavailable'):
        dd_run_check(check)
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == [('GET', 'http://fake.tld/prometheus')]


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric_name, metric_type in EXPECTED_METRICS_V2_E2E.items():
        if metric_name in OPTIONAL_METRICS_V2_E2E:
            aggregator.assert_metric(metric_name, metric_type=metric_type, at_least=0)
        else:
            aggregator.assert_metric(metric_name, metric_type=metric_type)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('linkerd.prometheus.health', status=LinkerdCheck.OK, count=2)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery) -> None:
    aggregator = dd_agent_check_discovery(
        check_rate=True,
        discovery_min_instances=LINKERD_DISCOVERY_INSTANCES,
        discovery_timeout=60,
    )
    # These traffic metrics are consistently exposed by every injected Linkerd proxy in the fixture.
    for metric_name in (
        'linkerd.request.count',
        'linkerd.response.count',
        'linkerd.tcp.read_bytes.count',
        'linkerd.tcp.write_bytes.count',
    ):
        aggregator.assert_metric(metric_name)

    aggregator.assert_service_check(
        'linkerd.openmetrics.health',
        status=LinkerdCheck.OK,
        count=2 * LINKERD_DISCOVERY_INSTANCES,
    )


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check, linkerd_kubeconfig: str) -> None:
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        LinkerdCheck,
        linkerd_kubeconfig,
        namespace='linkerd',
        pod_selector='linkerd.io/control-plane-component=controller',
        container_name='linkerd-proxy',
    )
