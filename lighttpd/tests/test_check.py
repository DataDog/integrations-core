# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals

import pytest

from datadog_checks.lighttpd import Lighttpd

from . import common

CHECK_GAUGES = [
    'lighttpd.net.bytes',
    'lighttpd.net.bytes_per_s',
    'lighttpd.net.hits',
    'lighttpd.net.request_per_s',
    'lighttpd.performance.busy_servers',
    'lighttpd.performance.idle_server',
    'lighttpd.performance.uptime',
]


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_lighttpd(aggregator, check, instance):
    """
    """
    tags = ['host:{}'.format(common.HOST), 'port:9449', 'instance:first']
    check.check(instance)

    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.OK, tags=tags)

    for gauge in CHECK_GAUGES:
        aggregator.assert_metric(gauge, tags=['instance:first'], count=1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_service_check_ko(aggregator, check, instance):
    """
    """
    instance['lighttpd_status_url'] = 'http://localhost:1337'
    tags = ['host:localhost', 'port:1337', 'instance:first']
    with pytest.raises(Exception):
        check.check(instance)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.CRITICAL, tags=tags)
