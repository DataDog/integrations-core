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

    aggregator.assert_metric('nginx.net.writing', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.waiting', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.reading', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.conn_dropped_per_s', count=1, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.conn_opened_per_s', count=1, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.request_per_s', count=1, tags=common.TAGS)

    aggregator.assert_metric('nginx.net.connections', count=2, tags=common.TAGS)

    aggregator.assert_all_metrics_covered()

    tags = common.TAGS + [
        'nginx_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
    ]
    aggregator.assert_service_check('nginx.can_connect', status=Nginx.OK, tags=tags)


@pytest.mark.e2e
@pytest.mark.skipif(not common.USING_VTS, reason="VTS test")
def test_e2e_vts(dd_agent_check, instance_vts):
    aggregator = dd_agent_check(instance_vts, rate=True)

    aggregator.assert_metric('nginx.net.writing', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.waiting', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.reading', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.conn_dropped_per_s', count=1, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.conn_opened_per_s', count=1, tags=common.TAGS)
    aggregator.assert_metric('nginx.net.request_per_s', count=1, tags=common.TAGS)

    tags_server_zone = common.TAGS + ['server_zone:*']

    aggregator.assert_metric('nginx.connections.active', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.server_zone.sent', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.sent_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.received', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.received_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.requests.total_count', count=1, tags=common.TAGS)
    aggregator.assert_metric('nginx.requests.total', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.timestamp', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.server_zone.requests_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.load_timestamp', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.server_zone.requests', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.connections.accepted', count=2, tags=common.TAGS)
    aggregator.assert_metric('nginx.connections.accepted_count', count=1, tags=common.TAGS)

    aggregator.assert_metric('nginx.server_zone.responses.1xx_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.2xx_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.3xx_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.4xx_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.5xx_count', count=1, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.1xx', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.2xx', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.3xx', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.4xx', count=2, tags=tags_server_zone)
    aggregator.assert_metric('nginx.server_zone.responses.5xx', count=2, tags=tags_server_zone)

    aggregator.assert_all_metrics_covered()

    tags = common.TAGS + [
        'nginx_host:{}'.format(common.HOST),
        'port:{}'.format(common.PORT),
    ]
    aggregator.assert_service_check('nginx.can_connect', status=Nginx.OK, tags=tags)
