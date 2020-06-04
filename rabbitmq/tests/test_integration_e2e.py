# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import time
from contextlib import closing

import pika
import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.rabbitmq import RabbitMQ

from . import common, metrics

log = logging.getLogger(__file__)


@pytest.mark.e2e
def test_rabbitm_e2e(dd_agent_check):
    aggregator = dd_agent_check(common.CONFIG)
    assert_metric_covered(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_rabbitmq(aggregator, check):
    check.check(common.CONFIG)
    assert_metric_covered(aggregator)


def assert_metric_covered(aggregator):
    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.node.partitions', value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=0, count=1)
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], value=0, count=1
    )
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], value=0, count=1
    )

    # Queue attributes, should be only one queue fetched
    for mname in metrics.Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=1)
    # Exchange attributes, should be only one exchange fetched
    for mname in metrics.E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test1', count=1)
    # Overview attributes
    for mname in metrics.OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in metrics.OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check(
        'rabbitmq.aliveness', tags=['vhost:myothervhost', "tag1:1", "tag2"], status=RabbitMQ.OK
    )

    aggregator.assert_service_check('rabbitmq.status', tags=["tag1:1", "tag2"], status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_regex(aggregator, check):
    check.check(common.CONFIG_REGEX)

    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)

    # Exchange attributes
    for mname in metrics.E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test1', count=1)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:test5', count=1)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange:tralala', count=0)

    # Queue attributes
    for mname in metrics.Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test5', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:tralala', count=0)

    # Overview attributes
    for mname in metrics.OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in metrics.OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_limit_vhosts(aggregator, check):
    check.check(common.CONFIG_REGEX)

    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)

    for mname in metrics.Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test1', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:test5', count=3)
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue:tralala', count=0)
    for mname in metrics.E_METRICS:
        aggregator.assert_metric(mname, count=2)

    # Overview attributes
    for mname in metrics.OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in metrics.OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    # Service checks
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_family_tagging(aggregator, check):
    check.check(common.CONFIG_WITH_FAMILY)

    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric_has_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    for mname in metrics.E_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_exchange_family:test', count=2)

    for mname in metrics.Q_METRICS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_queue_family:test', count=6)
    # Overview attributes
    for mname in metrics.OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', count=1)
    for mname in metrics.OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric_has_tag(mname, 'rabbitmq_cluster:rabbitmqtest', at_least=0)

    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost'], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.status', status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_connections(aggregator, check):
    # no connections and no 'vhosts' list in the conf don't produce 'connections' metric
    check.check(common.CONFIG)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=0, count=1)
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], value=0, count=1
    )
    aggregator.assert_metric(
        'rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], value=0, count=1
    )

    # no connections with a 'vhosts' list in the conf produce one metrics per vhost
    aggregator.reset()
    check.check(common.CONFIG_TEST_VHOSTS)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', count=2)

    params = pika.ConnectionParameters(common.HOST)
    with closing(pika.BlockingConnection(params)), closing(pika.BlockingConnection(params)):
        time.sleep(5)

        aggregator.reset()
        check.check(common.CONFIG)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=2, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=3)
        aggregator.assert_metric(
            'rabbitmq.connections.state', tags=['rabbitmq_conn_state:running', "tag1:1", "tag2"], value=2, count=1
        )

        aggregator.reset()
        check.check(common.CONFIG_DEFAULT_VHOSTS)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=2, count=1)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=2)
        aggregator.assert_metric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)

        aggregator.reset()
        check.check(common.CONFIG_TEST_VHOSTS)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
        aggregator.assert_metric('rabbitmq.connections', count=2)
        aggregator.assert_metric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)
