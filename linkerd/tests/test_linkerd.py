# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests_mock

from datadog_checks.linkerd import LinkerdCheck

from .common import EXPECTED_METRICS_V2, EXPECTED_METRICS_V2_E2E, LINKERD_FIXTURE_VALUES, MOCK_INSTANCE


def get_response(filename):
    metrics_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    with open(metrics_file_path, 'r') as f:
        response = f.read()
    return response


def test_linkerd(aggregator):
    """
    Test the full check
    """
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', text=get_response('linkerd.txt'))
        check.check(MOCK_INSTANCE)

    for metric in LINKERD_FIXTURE_VALUES:
        aggregator.assert_metric(metric, LINKERD_FIXTURE_VALUES[metric])

    aggregator.assert_metric('linkerd.prometheus.health', metric_type=aggregator.GAUGE)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=check.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_linkerd_v2(aggregator):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', text=get_response('linkerd_v2.txt'))
        check.check(MOCK_INSTANCE)

    for metric_name, metric_type in EXPECTED_METRICS_V2.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check(
        'linkerd.prometheus.health', status=LinkerdCheck.OK, tags=['endpoint:http://fake.tld/prometheus'], count=1
    )


def test_openmetrics_error(monkeypatch):
    check = LinkerdCheck('linkerd', {}, [MOCK_INSTANCE])
    with requests_mock.Mocker() as metric_request:
        metric_request.get('http://fake.tld/prometheus', exc="Exception")
        with pytest.raises(Exception):
            check.check(MOCK_INSTANCE)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    for metric_name, metric_type in EXPECTED_METRICS_V2_E2E.items():
        aggregator.assert_metric(metric_name, metric_type=metric_type)
    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('linkerd.prometheus.health', status=LinkerdCheck.OK, count=2)
