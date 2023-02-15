# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import time
from contextlib import closing

import pika
import pytest

from datadog_checks.rabbitmq import RabbitMQ

from .common import (
    CONFIG,
    CONFIG_DEFAULT_VHOSTS,
    CONFIG_REGEX,
    CONFIG_TEST_VHOSTS,
    CONFIG_WITH_FAMILY,
    CONFIG_WITH_FAMILY_NAMED_GROUP,
    HOST,
    METRICS_PLUGIN,
)
from .metrics import (
    COMMON_METRICS,
    E_METRICS,
    OVERVIEW_METRICS_MESSAGES,
    OVERVIEW_METRICS_TOTALS,
    Q_METRICS,
    assert_metric_covered,
)

log = logging.getLogger(__file__)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(METRICS_PLUGIN == "prometheus", reason="Not testing management plugin metrics."),
]


def test_rabbitmq(aggregator, check):
    check.check(CONFIG)
    assert_metric_covered(aggregator)


def test_regex(aggregator, check):
    check.check(CONFIG_REGEX)

    # Node attributes
    for mname in COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)

    # Exchange attributes
    for mname in E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test1', count=1)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test5', count=1)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:tralala', count=0)

    # Queue attributes
    for mname in Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test5', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:tralala', count=0)

    # Overview attributes
    for mname in OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


def test_limit_vhosts(aggregator, check):
    check.check(CONFIG_REGEX)

    # Node attributes
    for mname in COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)

    for mname in Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test5', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:tralala', count=0)
    for mname in E_METRICS:
        aggregator.assert_metric(mname, count=2)

    # Overview attributes
    for mname in OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    # Service checks
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


def test_family_tagging(aggregator, check):
    check.check(CONFIG_WITH_FAMILY)

    # Node attributes
    for mname in COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    for mname in E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange_family:test', count=2)

    for mname in Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue_family:test', count=6)
    # Overview attributes
    for mname in OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


def test_family_tagging_with_named_groups(aggregator, check):
    check.check(CONFIG_WITH_FAMILY_NAMED_GROUP)

    # Node attributes
    for mname in COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    for mname in E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange_family_first_group:test', count=2)

    for mname in Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue_family_first_group:test', count=6)
    # Overview attributes
    for mname in OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


def test_connections(aggregator, check):
    # no connections and no 'vhosts' list in the conf don't produce 'connections' metric
    check.check(CONFIG)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=0, count=1)
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], value=0, count=1
    )
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], value=0, count=1
    )

    # no connections with a 'vhosts' list in the conf produce one metrics per vhost
    aggregator.reset()
    check.check(CONFIG_TEST_VHOSTS)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', count=2)

    params = pika.ConnectionParameters(HOST)
    with closing(pika.BlockingConnection(params)), closing(pika.BlockingConnection(params)):
        time.sleep(5)

        aggregator.reset()
        check.check(CONFIG)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=2, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=3)
        aggregator.assert_metric(
            'rabbitmq.connections.state', tags=['rabbitmq_conn_state:running', "tag1:1", "tag2"], value=2, count=1
        )

        aggregator.reset()
        check.check(CONFIG_DEFAULT_VHOSTS)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=2, count=1)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=2)
        aggregator.assert_metric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)

        aggregator.reset()
        check.check(CONFIG_TEST_VHOSTS)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=2)
        aggregator.assert_metric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)
