# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.lighttpd import Lighttpd

from . import common

EXPECTED_METRICS = [
    ('lighttpd.net.bytes', AggregatorStub.GAUGE),
    ('lighttpd.net.bytes_per_s', AggregatorStub.RATE),
    ('lighttpd.net.hits', AggregatorStub.GAUGE),
    ('lighttpd.net.request_per_s', AggregatorStub.RATE),
    ('lighttpd.performance.busy_servers', AggregatorStub.GAUGE),
    ('lighttpd.performance.idle_server', AggregatorStub.GAUGE),
    ('lighttpd.performance.uptime', AggregatorStub.GAUGE),
]


def test_service_check_ko(aggregator, check, instance):
    instance['lighttpd_status_url'] = 'http://localhost:1337'
    tags = ['host:localhost', 'port:1337', 'instance:first']
    with pytest.raises(Exception):
        check.check(instance)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.CRITICAL, tags=tags)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_lighttpd(aggregator, check, instance):
    check.check(instance)

    assert_integration_e2e(aggregator, 1)


@pytest.mark.e2e
def test_e2e_rate(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    assert_integration_e2e(aggregator, 2)


@pytest.mark.e2e
def test_e2e_times(dd_agent_check, instance):
    runs = 5
    aggregator = dd_agent_check(instance, times=runs)

    assert_integration_e2e(aggregator, runs)


def assert_integration_e2e(aggregator, runs):
    tags = ['host:{}'.format(common.HOST), 'port:9449', 'instance:first']
    aggregator.assert_service_check('lighttpd.can_connect', status=Lighttpd.OK, tags=tags)

    tags = ['instance:first']
    for metric_name, metric_type in EXPECTED_METRICS:
        aggregator.assert_metric(metric_name, metric_type=metric_type, tags=tags, count=runs)
    aggregator.assert_all_metrics_covered()
