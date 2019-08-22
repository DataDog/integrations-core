import pytest

from datadog_checks.rabbitmq import RabbitMQ

from . import common, metrics


@pytest.mark.e2e
def test_rabbitmq(dd_agent_check):
    aggregator = dd_agent_check(common.CONFIG)

    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric(mname)

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
        aggregator.assert_metric(mname)
    # Exchange attributes, should be only one exchange fetched
    for mname in metrics.E_METRICS:
        aggregator.assert_metric(mname)
    for mname in metrics.E_METRICS_35:
        aggregator.assert_metric(mname)
    # Overview attributes
    for mname in metrics.OVERVIEW_METRICS_TOTALS:
        aggregator.assert_metric(mname)
    for mname in metrics.OVERVIEW_METRICS_MESSAGES:
        # All messages metrics are not always present, so we assert with at_least=0
        aggregator.assert_metric(mname, at_least=0)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check(
        'rabbitmq.aliveness', tags=['vhost:myothervhost', "tag1:1", "tag2"], status=RabbitMQ.OK
    )

    aggregator.assert_service_check('rabbitmq.status', tags=["tag1:1", "tag2"], status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()
