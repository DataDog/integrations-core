# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.rabbitmq import RabbitMQ

from . import common, metrics

def test_rabbitmq(aggregator, spin_up_rabbitmq, setup_rabbitmq, check):
    check.check(common.CONFIG)

    # Node attributes
    for mname in metrics.COMMON_METRICS:
        aggregator.assert_metric_tag_prefix(mname, 'rabbitmq_node', count=1)

    aggregator.assert_metric('rabbitmq.node.partitions', value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], value=0, count=1)
    aggregator.assert_metric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], value=0, count=1)

    # Queue attributes, should be only one queue fetched
    for mname in metrics.Q_METRICS:
        aggregator.assert_metric_tag('rabbitmq.queue.%s' %
                                     mname, 'rabbitmq_queue:test1', count=1)

    # Exchange attributes, should be only one exchange fetched
    for mname in metrics.E_METRICS:
        aggregator.assert_metric_tag('rabbitmq.exchange.%s' %
                                     mname, 'rabbitmq_exchange:test1', count=1)

    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:/', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myvhost', "tag1:1", "tag2"], status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', tags=['vhost:myothervhost', "tag1:1", "tag2"], status=RabbitMQ.OK)

    aggregator.assert_service_check('rabbitmq.status', tags=["tag1:1", "tag2"], status=RabbitMQ.OK)

    aggregator.assert_all_metrics_covered()


    # def test_regex(self):
    #     self.run_check(CONFIG_REGEX)
    #
    #     # Node attributes
    #     for mname in COMMON_METRICS:
    #         self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)
    #
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    #
    #     # Exchange attributes
    #     for mname in E_METRICS:
    #         self.assertMetricTag('rabbitmq.exchange.%s' %
    #                              mname, 'rabbitmq_exchange:test1', count=1)
    #         self.assertMetricTag('rabbitmq.exchange.%s' %
    #                              mname, 'rabbitmq_exchange:test5', count=1)
    #         self.assertMetricTag('rabbitmq.exchange.%s' %
    #                              mname, 'rabbitmq_exchange:tralala', count=0)
    #
    #     # Queue attributes
    #     for mname in Q_METRICS:
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:test1', count=3)
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:test5', count=3)
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:tralala', count=0)
    #
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myvhost'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myothervhost'])
    #     self.assertServiceCheckOK('rabbitmq.status')
    #
    #     self.coverage_report()
    #
    # def test_limit_vhosts(self):
    #     self.run_check(CONFIG_REGEX)
    #
    #     # Node attributes
    #     for mname in COMMON_METRICS:
    #         self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)
    #
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    #
    #     for mname in Q_METRICS:
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:test1', count=3)
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:test5', count=3)
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue:tralala', count=0)
    #     for mname in E_METRICS:
    #         self.assertMetric('rabbitmq.exchange.%s' % mname, count=2)
    #
    #     # Service checks
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myvhost'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myothervhost'])
    #     self.assertServiceCheckOK('rabbitmq.status')
    #
    #     self.coverage_report()
    #
    # def test_family_tagging(self):
    #     self.run_check(CONFIG_WITH_FAMILY)
    #
    #     # Node attributes
    #     for mname in COMMON_METRICS:
    #         self.assertMetricTagPrefix(mname, 'rabbitmq_node', count=1)
    #
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost'], value=0, count=1)
    #     for mname in E_METRICS:
    #         self.assertMetricTag('rabbitmq.exchange.%s' %
    #                              mname, 'rabbitmq_exchange_family:test', count=2)
    #
    #     for mname in Q_METRICS:
    #         self.assertMetricTag('rabbitmq.queue.%s' %
    #                              mname, 'rabbitmq_queue_family:test', count=6)
    #
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=0, count=1)
    #
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:/'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myvhost'])
    #     self.assertServiceCheckOK('rabbitmq.aliveness', tags=['vhost:myothervhost'])
    #     self.assertServiceCheckOK('rabbitmq.status')
    #
    #     self.coverage_report()
    #
    # def test_connections(self):
    #     # no connections and no 'vhosts' list in the conf don't produce 'connections' metric
    #     self.run_check(CONFIG)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myvhost', "tag1:1", "tag2"], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:myothervhost', "tag1:1", "tag2"], value=0, count=1)
    #
    #
    #     # no connections with a 'vhosts' list in the conf produce one metrics per vhost
    #     self.run_check(CONFIG_TEST_VHOSTS, force_reload=True)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
    #     self.assertMetric('rabbitmq.connections', count=2)
    #
    #     # create connections
    #     connection1 = pika.BlockingConnection()
    #     connection2 = pika.BlockingConnection()
    #     try:
    #         self.run_check(CONFIG, force_reload=True)
    #         self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/', "tag1:1", "tag2"], value=2, count=1)
    #         self.assertMetric('rabbitmq.connections', count=3)
    #         self.assertMetric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running', "tag1:1", "tag2"], value=2, count=1)
    #
    #         self.run_check(CONFIG_DEFAULT_VHOSTS, force_reload=True)
    #         self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:/'], value=2, count=1)
    #         self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
    #         self.assertMetric('rabbitmq.connections', count=2)
    #         self.assertMetric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)
    #
    #         self.run_check(CONFIG_TEST_VHOSTS, force_reload=True)
    #         self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:test'], value=0, count=1)
    #         self.assertMetric('rabbitmq.connections', tags=['rabbitmq_vhost:test2'], value=0, count=1)
    #         self.assertMetric('rabbitmq.connections', count=2)
    #         self.assertMetric('rabbitmq.connections.state', tags=['rabbitmq_conn_state:running'], value=0, count=0)
    #     except Exception as e:
    #         raise e
    #     finally:
    #         # if these are not closed it makes all the other tests fail, too
    #         connection1.close()
    #         connection2.close()
