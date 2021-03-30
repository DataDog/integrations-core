# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.amazon_msk import AmazonMskCheck
from datadog_checks.amazon_msk.metrics import JMX_METRICS_MAP, NODE_METRICS_MAP


@pytest.mark.usefixtures('mock_data')
def test_node_check(aggregator, instance, mock_client):
    c = AmazonMskCheck('amazon_msk', {}, [instance])
    assert not c.run()

    caller, client = mock_client
    cluster_arn = instance['cluster_arn']
    region_name = cluster_arn.split(':')[3]

    caller.assert_called_once_with('kafka', region_name=region_name)
    client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name)]
    global_tags.extend(instance['tags'])
    aggregator.assert_service_check(c.SERVICE_CHECK_CONNECT, c.OK, tags=global_tags)

    for node_info in client.list_nodes()['NodeInfoList']:
        broker_info = node_info['BrokerNodeInfo']
        broker_tags = ['broker_id:{}'.format(broker_info['BrokerId'])]
        broker_tags.extend(global_tags)

        assert_node_metrics(aggregator, broker_tags)
        assert_jmx_metrics(aggregator, broker_tags)

        for endpoint in broker_info['Endpoints']:
            for port in (11001, 11002):
                service_check_tags = ['endpoint:http://{}:{}/metrics'.format(endpoint, port)]
                service_check_tags.extend(global_tags)

                aggregator.assert_service_check('aws.msk.prometheus.health', c.OK, tags=service_check_tags)

    aggregator.assert_all_metrics_covered()


def assert_node_metrics(aggregator, tags):
    metrics = set(NODE_METRICS_MAP.values())

    # Summaries
    for metric in ('go.gc.duration.seconds',):
        metrics.remove(metric)
        metrics.update({'{}.count'.format(metric), '{}.quantile'.format(metric), '{}.sum'.format(metric)})

    for metric in sorted(metrics):
        metric = 'aws.msk.{}'.format(metric)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)


def assert_jmx_metrics(aggregator, tags):
    for metric in sorted(JMX_METRICS_MAP.values()):
        metric = 'aws.msk.{}'.format(metric)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)


@pytest.mark.usefixtures('mock_data')
def test_custom_metric_path(aggregator, instance, mock_client):
    instance['prometheus_metrics_path'] = '/'
    c = AmazonMskCheck('amazon_msk', {}, [instance])
    assert not c.run()

    caller, client = mock_client
    cluster_arn = instance['cluster_arn']
    region_name = cluster_arn.split(':')[3]

    caller.assert_called_once_with('kafka', region_name=region_name)
    client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name)]
    global_tags.extend(instance['tags'])
    aggregator.assert_service_check(c.SERVICE_CHECK_CONNECT, c.OK, tags=global_tags)

    for node_info in client.list_nodes()['NodeInfoList']:
        broker_info = node_info['BrokerNodeInfo']
        broker_tags = ['broker_id:{}'.format(broker_info['BrokerId'])]
        broker_tags.extend(global_tags)

        assert_node_metrics(aggregator, broker_tags)
        assert_jmx_metrics(aggregator, broker_tags)

        for endpoint in broker_info['Endpoints']:
            for port in (11001, 11002):
                service_check_tags = ['endpoint:http://{}:{}/'.format(endpoint, port)]
                service_check_tags.extend(global_tags)

                aggregator.assert_service_check('aws.msk.prometheus.health', c.OK, tags=service_check_tags)

    aggregator.assert_all_metrics_covered()
