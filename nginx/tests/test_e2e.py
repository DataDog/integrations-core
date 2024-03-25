# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.nginx import Nginx

from . import common


@pytest.mark.e2e
@pytest.mark.skipif(common.USING_VTS, reason="Non-VTS test")
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for m in ('nginx.net.conn_dropped_per_s', 'nginx.net.conn_opened_per_s', 'nginx.net.request_per_s'):
        aggregator.assert_metric(m, count=1, tags=common.TAGS_WITH_HOST_AND_PORT)
    for m in ('nginx.net.writing', 'nginx.net.reading', 'nginx.net.waiting', 'nginx.net.connections'):
        aggregator.assert_metric(m, count=2, tags=common.TAGS_WITH_HOST_AND_PORT)

    aggregator.assert_service_check('nginx.can_connect', status=Nginx.OK, tags=common.TAGS_WITH_HOST_AND_PORT)


@pytest.mark.e2e
@pytest.mark.skipif(not common.USING_VTS, reason="VTS test")
def test_e2e_vts(dd_agent_check, instance_vts):
    aggregator = dd_agent_check(instance_vts, rate=True)

    for m in (
        'nginx.net.writing',
        'nginx.net.reading',
        'nginx.net.waiting',
        'nginx.connections.active',
        'nginx.requests.total',
        'nginx.timestamp',
        'nginx.load_timestamp',
        'nginx.connections.accepted',
    ):
        aggregator.assert_metric(m, count=2, tags=common.TAGS_WITH_HOST_AND_PORT)
    for m in (
        'nginx.net.conn_dropped_per_s',
        'nginx.net.conn_opened_per_s',
        'nginx.net.request_per_s',
        'nginx.connections.accepted_count',
        'nginx.requests.total_count',
    ):
        aggregator.assert_metric(m, count=1, tags=common.TAGS_WITH_HOST_AND_PORT)

    tags_server_zone = common.TAGS_WITH_HOST_AND_PORT + ['server_zone:*']
    for m, count in (
        ('nginx.server_zone.sent', 2),
        ('nginx.server_zone.sent_count', 1),
        ('nginx.server_zone.received', 2),
        ('nginx.server_zone.received_count', 1),
        ('nginx.server_zone.requests_count', 1),
        ('nginx.server_zone.requests', 2),
        ('nginx.server_zone.responses.1xx_count', 1),
        ('nginx.server_zone.responses.2xx_count', 1),
        ('nginx.server_zone.responses.3xx_count', 1),
        ('nginx.server_zone.responses.4xx_count', 1),
        ('nginx.server_zone.responses.5xx_count', 1),
        ('nginx.server_zone.responses.1xx', 2),
        ('nginx.server_zone.responses.2xx', 2),
        ('nginx.server_zone.responses.3xx', 2),
        ('nginx.server_zone.responses.4xx', 2),
        ('nginx.server_zone.responses.5xx', 2),
    ):
        aggregator.assert_metric(m, count=count, tags=tags_server_zone)

    aggregator.assert_all_metrics_covered()

    aggregator.assert_service_check('nginx.can_connect', status=Nginx.OK, tags=common.TAGS_WITH_HOST_AND_PORT)
