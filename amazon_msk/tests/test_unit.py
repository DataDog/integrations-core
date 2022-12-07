# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import mock
import pytest
from six import PY2

from datadog_checks.amazon_msk import AmazonMskCheck
from datadog_checks.amazon_msk.metrics import (
    JMX_METRICS_MAP,
    JMX_METRICS_OVERRIDES,
    METRICS_WITH_NAME_AS_LABEL,
    NODE_METRICS_MAP,
    NODE_METRICS_OVERRIDES,
)

from .common import INSTANCE, INSTANCE_LEGACY, METRICS_FROM_LABELS


@pytest.mark.usefixtures('mock_data')
def test_node_check_legacy(aggregator, instance_legacy, mock_client):
    c = AmazonMskCheck('amazon_msk', {}, [instance_legacy])
    assert not c.run()

    caller, client = mock_client
    cluster_arn = instance_legacy['cluster_arn']
    region_name = cluster_arn.split(':')[3]

    caller.assert_called_once_with('kafka', region_name=region_name, config=mock.ANY)
    client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name)]
    global_tags.extend(instance_legacy['tags'])
    aggregator.assert_service_check(c.SERVICE_CHECK_CONNECT, c.OK, tags=global_tags)

    for node_info in client.list_nodes()['NodeInfoList']:
        broker_info = node_info['BrokerNodeInfo']
        broker_tags = ['broker_id:{}'.format(broker_info['BrokerId'])]
        broker_tags.extend(global_tags)

        assert_node_metrics_legacy(aggregator, broker_tags)
        assert_jmx_metrics_legacy(aggregator, broker_tags)

        for endpoint in broker_info['Endpoints']:
            for port in (11001, 11002):
                service_check_tags = ['endpoint:http://{}:{}/metrics'.format(endpoint, port)]
                service_check_tags.extend(global_tags)

                aggregator.assert_service_check('aws.msk.prometheus.health', c.OK, tags=service_check_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('mock_data')
@pytest.mark.parametrize(
    'jmx_exporter_port, node_exporter_port, assert_jmx_metrics_enabled, assert_node_metrics_enabled',
    [
        pytest.param(0, 0, False, False, id='both disabled'),
        pytest.param(11001, 0, True, False, id='node disabled'),
        pytest.param(0, 11002, False, True, id='jmx disabled'),
        pytest.param(11001, 11002, True, True, id='both enabled'),
    ],
)
def test_disabled_exporter_legacy(
    aggregator,
    dd_run_check,
    instance_legacy,
    mock_client,
    jmx_exporter_port,
    node_exporter_port,
    assert_jmx_metrics_enabled,
    assert_node_metrics_enabled,
):
    inst = copy.deepcopy(instance_legacy)

    # Test both JMX and NODE exporters disabled
    inst.update(
        {
            "jmx_exporter_port": jmx_exporter_port,
            "node_exporter_port": node_exporter_port,
        }
    )
    c = AmazonMskCheck('amazon_msk', {}, [inst])
    assert not c.run()

    assert_jmx_metrics(aggregator, [], is_enabled=assert_jmx_metrics_enabled)
    assert_node_metrics(aggregator, [], is_enabled=assert_node_metrics_enabled)


@pytest.mark.usefixtures('mock_data')
@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_node_check(aggregator, dd_run_check, instance, mock_client):
    c = AmazonMskCheck('amazon_msk', {}, [instance])
    dd_run_check(c)

    caller, client = mock_client
    cluster_arn = instance['cluster_arn']
    region_name = cluster_arn.split(':')[3]

    caller.assert_called_once_with('kafka', config=mock.ANY, region_name=region_name)
    client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name)]
    global_tags.extend(instance['tags'])
    aggregator.assert_service_check('aws.msk.{}'.format(c.SERVICE_CHECK_CONNECT), c.OK, tags=global_tags)

    for node_info in client.list_nodes()['NodeInfoList']:
        broker_info = node_info['BrokerNodeInfo']
        broker_tags = ['broker_id:{}'.format(broker_info['BrokerId'])]
        broker_tags.extend(global_tags)

        for endpoint in broker_info['Endpoints']:
            for port, metric_assertion in ((11001, assert_jmx_metrics), (11002, assert_node_metrics)):
                endpoint_tag = 'endpoint:http://{}:{}/metrics'.format(endpoint, port)

                metric_tags = [endpoint_tag]
                metric_tags.extend(broker_tags)
                metric_assertion(aggregator, metric_tags)

                service_check_tags = [endpoint_tag]
                service_check_tags.extend(global_tags)
                aggregator.assert_service_check('aws.msk.openmetrics.health', c.OK, tags=service_check_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('mock_data')
@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
@pytest.mark.parametrize(
    'jmx_exporter_port, node_exporter_port, assert_jmx_metrics_enabled, assert_node_metrics_enabled',
    [
        pytest.param(0, 0, False, False, id='both disabled'),
        pytest.param(11001, 0, True, False, id='node disabled'),
        pytest.param(0, 11002, False, True, id='jmx disabled'),
        pytest.param(11001, 11002, True, True, id='both enabled'),
    ],
)
def test_disabled_exporter_check(
    aggregator,
    dd_run_check,
    instance,
    mock_client,
    jmx_exporter_port,
    node_exporter_port,
    assert_jmx_metrics_enabled,
    assert_node_metrics_enabled,
):
    inst = copy.deepcopy(instance)

    # Test both JMX and NODE exporters disabled
    inst.update(
        {
            "jmx_exporter_port": jmx_exporter_port,
            "node_exporter_port": node_exporter_port,
        }
    )
    c = AmazonMskCheck('amazon_msk', {}, [inst])
    dd_run_check(c)

    assert_jmx_metrics(aggregator, [], is_enabled=assert_jmx_metrics_enabled)
    assert_node_metrics(aggregator, [], is_enabled=assert_node_metrics_enabled)


def assert_node_metrics_legacy(aggregator, tags, is_enabled=True):
    metrics = set(NODE_METRICS_MAP.values())

    # Summaries
    for metric in ('go.gc.duration.seconds',):
        metrics.remove(metric)
        metrics.update({'{}.count'.format(metric), '{}.quantile'.format(metric), '{}.sum'.format(metric)})

    for metric in sorted(metrics):
        metric = 'aws.msk.{}'.format(metric)
        if is_enabled:
            for tag in tags:
                aggregator.assert_metric_has_tag(metric, tag)
        else:
            aggregator.assert_metric(metric, count=0)


def assert_jmx_metrics_legacy(aggregator, tags, is_enabled=True):
    for metric in sorted(JMX_METRICS_MAP.values()):
        metric = 'aws.msk.{}'.format(metric)
        if is_enabled:
            for tag in tags:
                aggregator.assert_metric_has_tag(metric, tag)
        else:
            aggregator.assert_metric(metric, count=0)


def assert_node_metrics(aggregator, tags, is_enabled=True):
    expected_metrics = set()

    for raw_metric_name, metric_name in NODE_METRICS_MAP.items():
        if raw_metric_name.endswith('_total') and raw_metric_name not in NODE_METRICS_OVERRIDES:
            expected_metrics.add('{}.count'.format(metric_name[:-6]))
        else:
            expected_metrics.add(metric_name)

    # Summaries
    for metric in ('go.gc.duration.seconds',):
        expected_metrics.remove(metric)
        expected_metrics.update({'{}.count'.format(metric), '{}.quantile'.format(metric), '{}.sum'.format(metric)})

    for metric in sorted(expected_metrics):
        metric = 'aws.msk.{}'.format(metric)
        if is_enabled:
            for tag in tags:
                aggregator.assert_metric_has_tag(metric, tag)
        else:
            aggregator.assert_metric(metric, count=0)


def assert_jmx_metrics(aggregator, tags, is_enabled=True):
    expected_metrics = set()

    for raw_metric_name, metric_name in JMX_METRICS_MAP.items():
        if raw_metric_name.endswith('_total') and raw_metric_name not in JMX_METRICS_OVERRIDES:
            expected_metrics.add('{}.count'.format(metric_name[:-6]))
        else:
            expected_metrics.add(metric_name)

    expected_metrics.update(METRICS_FROM_LABELS)
    expected_metrics.update(data['legacy_name'] for data in METRICS_WITH_NAME_AS_LABEL.values())

    for metric in sorted(expected_metrics):
        metric = 'aws.msk.{}'.format(metric)
        if is_enabled:
            for tag in tags:
                aggregator.assert_metric_has_tag(metric, tag)
        else:
            aggregator.assert_metric(metric, count=0)


@pytest.mark.usefixtures('mock_data')
def test_custom_metric_path(aggregator, instance_legacy, mock_client):
    instance_legacy['prometheus_metrics_path'] = '/'
    c = AmazonMskCheck('amazon_msk', {}, [instance_legacy])
    assert not c.run()

    caller, client = mock_client
    cluster_arn = instance_legacy['cluster_arn']
    region_name = cluster_arn.split(':')[3]

    caller.assert_called_once_with('kafka', region_name=region_name, config=mock.ANY)
    client.list_nodes.assert_called_once_with(ClusterArn=cluster_arn)

    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name)]
    global_tags.extend(instance_legacy['tags'])
    aggregator.assert_service_check(c.SERVICE_CHECK_CONNECT, c.OK, tags=global_tags)

    for node_info in client.list_nodes()['NodeInfoList']:
        broker_info = node_info['BrokerNodeInfo']
        broker_tags = ['broker_id:{}'.format(broker_info['BrokerId'])]
        broker_tags.extend(global_tags)

        assert_node_metrics_legacy(aggregator, broker_tags)
        assert_jmx_metrics_legacy(aggregator, broker_tags)

        for endpoint in broker_info['Endpoints']:
            for port in (11001, 11002):
                service_check_tags = ['endpoint:http://{}:{}/'.format(endpoint, port)]
                service_check_tags.extend(global_tags)

                aggregator.assert_service_check('aws.msk.prometheus.health', c.OK, tags=service_check_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'instance',
    [
        pytest.param(INSTANCE_LEGACY, id='legacy config proxy'),
        pytest.param(
            INSTANCE, id='new config proxy', marks=pytest.mark.skipif(PY2, reason='Test only available on Python 3')
        ),
    ],
)
def test_proxy_config(instance):
    HTTP_PROXY = {"http": "example.com"}
    init_config = {"proxy": HTTP_PROXY}
    c = AmazonMskCheck('amazon_msk', init_config, [instance])
    assert c._boto_config.proxies == HTTP_PROXY


@pytest.mark.parametrize(
    'instance',
    [
        pytest.param(INSTANCE_LEGACY, id='legacy config proxy'),
        pytest.param(
            INSTANCE, id='new config proxy', marks=pytest.mark.skipif(PY2, reason='Test only available on Python 3')
        ),
    ],
)
def test_boto_config(instance):
    instance = copy.deepcopy(instance)
    HTTP_PROXY = {"http": "example.com"}
    init_config = {"proxy": HTTP_PROXY}
    instance["boto_config"] = {"proxies_config": {"proxy_use_forwarding_for_https": True}, "read_timeout": 60}
    c = AmazonMskCheck('amazon_msk', init_config, [instance])
    assert c._boto_config.proxies == HTTP_PROXY
    assert c._boto_config.proxies_config.get("proxy_use_forwarding_for_https")
    assert c._boto_config.read_timeout == 60


@pytest.mark.integration
@pytest.mark.parametrize(
    'instance',
    [
        pytest.param(INSTANCE_LEGACY, id='legacy config proxy'),
        pytest.param(
            INSTANCE, id='new config proxy', marks=pytest.mark.skipif(PY2, reason='Test only available on Python 3')
        ),
    ],
)
def test_invalid_boto_config(aggregator, instance, dd_run_check, caplog):
    instance = copy.deepcopy(instance)
    HTTP_PROXY = {"http": "example.com"}
    init_config = {"proxy": HTTP_PROXY}
    instance["boto_config"] = {"proxies_config": {}, "read_timeout": True}
    c = AmazonMskCheck('amazon_msk', init_config, [instance])
    with pytest.raises(Exception, match=r'Timeout cannot be a boolean value. It must be an int, float or None.'):
        dd_run_check(c)

    cluster_arn = instance['cluster_arn']
    region_name = cluster_arn.split(':')[3]
    global_tags = ['cluster_arn:{}'.format(cluster_arn), 'region_name:{}'.format(region_name), 'test:msk']
    aggregator.assert_service_check(
        AmazonMskCheck.SERVICE_CHECK_CONNECT,
        AmazonMskCheck.CRITICAL,
        message="Timeout cannot be a boolean value. It must be an int, float or None.",
        tags=global_tags,
    )
    assert c._boto_config.proxies == HTTP_PROXY
