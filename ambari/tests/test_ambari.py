# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import MagicMock

from datadog_checks.ambari import AmbariCheck
from datadog_checks.base.checks import AgentCheck
from datadog_checks.base.errors import CheckException

from . import responses


def test_flatten_service_metrics():
    metrics = AmbariCheck.flatten_service_metrics(
        {
            "metric_a": 10,
            "metric_b": 15,
            "metric_c": {"submetric_c": "hello"},
            "metric_d": {"submetric_d": {'subsub_d': 25}},
        },
        "pfx",
    )
    assert metrics == {'pfx.metric_a': 10, 'pfx.metric_b': 15, 'pfx.submetric_c': 'hello', 'pfx.subsub_d': 25}


def test_flatten_host_metrics():
    metrics = AmbariCheck.flatten_host_metrics(responses.HOST_METRICS)
    assert metrics == {
        'boottime': 1555934503.0,
        'cpu.cpu_idle': 62.8,
        'cpu.cpu_nice': 0.0,
        'cpu.cpu_num': 4.0,
        'cpu.cpu_system': 5.1,
        'cpu.cpu_user': 32.0,
        'cpu.cpu_wio': 0.0,
        'disk.disk_free': 124.35,
        'disk.disk_total': 148.29,
        'disk.read_bytes': 1594053632.0,
        'disk.read_count': 42717.0,
        'disk.read_time': 240986.0,
        'disk.write_bytes': 117000843264.0,
        'disk.write_count': 499318.0,
        'disk.write_time': 5946304.0,
        'load.load_fifteen': 0.99,
        'load.load_five': 1.35,
        'load.load_one': 0.57,
        'memory.mem_cached': 3554248.0,
        'memory.mem_free': 11327848.0,
        'memory.mem_shared': 0.0,
        'memory.mem_total': 15399208.0,
        'memory.swap_free': 0.0,
        'memory.swap_total': 0.0,
        'network.bytes_in': 683.2346950556641,
        'network.bytes_out': 12517.203580542699,
        'network.pkts_in': 8.499187630576825,
        'network.pkts_out': 10.498996484830196,
        'process.proc_run': 0.0,
        'process.proc_total': 128.0,
    }


def test_cant_connect(init_config, instance, aggregator):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=None)

    try:
        ambari.get_clusters('localhost', ['foo:bar'])
    except CheckException:
        pass
    aggregator.assert_service_check(
        name="ambari.can_connect", status=AgentCheck.CRITICAL, tags=['foo:bar', 'url:localhost']
    )


def test_get_clusters(init_config, instance, aggregator):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(
        return_value={
            'href': 'localhost/api/v1/clusters',
            'items': [{'href': 'localhost/api/v1/clusters/LabCluster', 'Clusters': {'cluster_name': 'LabCluster'}}],
        }
    )

    clusters = ambari.get_clusters('localhost', ['foo:bar'])

    ambari._make_request.assert_called_with('localhost/api/v1/clusters')
    aggregator.assert_service_check(name="ambari.can_connect", status=AgentCheck.OK, tags=['foo:bar', 'url:localhost'])
    assert clusters == ['LabCluster']


def test_get_hosts(init_config, instance):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(
        return_value={'href': 'localhost/api/v1/clusters/myCluster/hosts?fields=metrics', 'items': responses.HOSTS_INFO}
    )
    hosts = ambari._get_hosts_info('localhost', 'myCluster')
    ambari._make_request.assert_called_with('localhost/api/v1/clusters/myCluster/hosts?fields=metrics')
    assert len(hosts) == 2
    assert hosts[0]['Hosts']['host_name'] == 'my_host_1'
    assert hosts[1]['Hosts']['host_name'] == 'my_host_2'
    assert hosts[1]['metrics'] is not None


def test_get_host_metrics(instance, aggregator):
    ambari = AmbariCheck(instances=[instance])
    ambari._get_hosts_info = MagicMock(return_value=responses.HOSTS_INFO)
    ambari.set_external_tags = MagicMock()
    cluster_tag = ['ambari_cluster:cluster1']

    ambari.get_host_metrics('localhost', ['cluster1'])
    ambari.set_external_tags.assert_called_with(
        [('my_host_1', {'ambari': cluster_tag}), ('my_host_2', {'ambari': cluster_tag})]
    )

    metrics = [
        ('boottime', 1555934503.0),
        ('cpu.cpu_idle', 62.8),
        ('cpu.cpu_nice', 0.0),
        ('cpu.cpu_num', 4.0),
        ('cpu.cpu_system', 5.1),
        ('cpu.cpu_user', 32.0),
        ('cpu.cpu_wio', 0.0),
        ('disk.disk_free', 124.35),
        ('disk.disk_total', 148.29),
        ('disk.read_bytes', 1594053632.0),
        ('disk.read_count', 42717.0),
        ('disk.read_time', 240986.0),
        ('disk.write_bytes', 117000843264.0),
        ('disk.write_count', 499318.0),
        ('disk.write_time', 5946304.0),
        ('load.load_fifteen', 0.99),
        ('load.load_five', 1.35),
        ('load.load_one', 0.57),
        ('memory.mem_cached', 3554248.0),
        ('memory.mem_free', 11327848.0),
        ('memory.mem_shared', 0.0),
        ('memory.mem_total', 15399208.0),
        ('memory.swap_free', 0.0),
        ('memory.swap_total', 0.0),
        ('network.bytes_in', 683.2346950556641),
        ('network.bytes_out', 12517.203580542699),
        ('network.pkts_in', 8.499187630576825),
        ('network.pkts_out', 10.498996484830196),
        ('process.proc_run', 0.0),
        ('process.proc_total', 128.0),
    ]
    for m in metrics:
        aggregator.assert_metric(name='ambari.{}'.format(m[0]), value=m[1], tags=cluster_tag, hostname='my_host_2')


def test_get_component_metrics(init_config, instance, aggregator):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=responses.COMPONENT_METRICS)
    namenode_tags = ['ambari_cluster:LabCluster', 'ambari_service:hdfs', 'ambari_component:namenode']

    ambari.get_component_metrics(
        'localhost',
        'LabCluster',
        'HDFS',
        base_tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs'],
        component_whitelist={'NAMENODE': ['cpu']},
    )

    ambari._make_request.assert_called_with(
        'localhost/api/v1/clusters/LabCluster/services/HDFS/components?fields=metrics'
    )
    metrics = [
        ('cpu.cpu_idle', 90.3),
        ('cpu.cpu_idle._avg', 90.3),
        ('cpu.cpu_idle._max', 90.3),
        ('cpu.cpu_idle._min', 90.3),
        ('cpu.cpu_idle._sum', 90.3),
        ('cpu.cpu_nice', 0.0),
        ('cpu.cpu_nice._avg', 0.0),
        ('cpu.cpu_nice._max', 0.0),
        ('cpu.cpu_nice._min', 0.0),
        ('cpu.cpu_nice._sum', 0.0),
        ('cpu.cpu_system', 1.6333333333333335),
        ('cpu.cpu_system._avg', 1.6333333333333335),
        ('cpu.cpu_system._max', 1.6333333333333335),
        ('cpu.cpu_system._min', 1.6333333333333335),
        ('cpu.cpu_system._sum', 1.6333333333333335),
        ('cpu.cpu_user', 8.033333333333333),
        ('cpu.cpu_user._avg', 8.033333333333333),
        ('cpu.cpu_user._max', 8.033333333333333),
        ('cpu.cpu_user._min', 8.033333333333333),
        ('cpu.cpu_user._sum', 8.033333333333333),
        ('cpu.cpu_wio', 0.0),
        ('cpu.cpu_wio._avg', 0.0),
        ('cpu.cpu_wio._max', 0.0),
        ('cpu.cpu_wio._min', 0.0),
        ('cpu.cpu_wio._sum', 0.0),
    ]
    for m in metrics:
        aggregator.assert_metric(name='ambari.{}'.format(m[0]), value=m[1], tags=namenode_tags)


def test_get_service_health(init_config, instance, aggregator):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=responses.SERVICE_HEALTH_METRICS)

    ambari.get_service_checks(
        'localhost', 'LabCluster', 'HDFS', service_tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs']
    )

    ambari._make_request.assert_called_with('localhost/api/v1/clusters/LabCluster/services/HDFS?fields=ServiceInfo')
    aggregator.assert_service_check(
        name="ambari.state",
        status=AgentCheck.OK,
        tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs', 'state:INSTALLED'],
        message='INSTALLED',
    )


def test_get_service_health_no_response(init_config, instance, aggregator):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=None)

    ambari.get_service_checks(
        'localhost', 'LabCluster', 'HDFS', service_tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs']
    )

    ambari._make_request.assert_called_with('localhost/api/v1/clusters/LabCluster/services/HDFS?fields=ServiceInfo')
    aggregator.assert_service_check(
        name="ambari.state", status=AgentCheck.CRITICAL, tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs']
    )


def test_default_config(instance):
    ambari = AmbariCheck(init_config={}, instances=[instance])

    assert ambari._should_collect_service_metrics() is True
    assert ambari._should_collect_service_status() is False


def test_should_not_collect_if_disabled(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': False, 'collect_service_status': False}, instances=[instance]
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_service_status_and_metrics = MagicMock()
    ambari.check(instance)

    assert not ambari.get_service_status_and_metrics.called


def test_should_collect_host_metrics(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': False, 'collect_service_status': False}, instances=[instance]
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_service_status_and_metrics = MagicMock()
    ambari.check(instance)

    assert ambari.get_host_metrics.called
    assert not ambari.get_service_status_and_metrics.called


def test_should_collect_service_metrics(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': True, 'collect_service_status': False}, instances=[instance]
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_component_metrics = MagicMock()
    ambari.get_service_checks = MagicMock()
    ambari.check(instance)

    assert ambari.get_host_metrics.called
    assert ambari.get_component_metrics.called
    assert not ambari.get_service_checks.called


def test_should_collect_service_status(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': False, 'collect_service_status': True}, instances=[instance]
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_component_metrics = MagicMock()
    ambari.get_service_checks = MagicMock()
    ambari.check(instance)

    assert ambari.get_host_metrics.called
    assert not ambari.get_component_metrics.called
    assert ambari.get_service_checks.called


def _mock_clusters(ambari):
    ambari.get_clusters = MagicMock(return_value=['LabCluster'])
