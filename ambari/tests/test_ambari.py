# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from mock import MagicMock, call

from datadog_checks.ambari import AmbariCheck

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


def test_get_clusters(init_config, instance):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(
        return_value={
            'href': 'localhost/api/v1/clusters',
            'items': [{'href': 'localhost/api/v1/clusters/LabCluster', 'Clusters': {'cluster_name': 'LabCluster'}}],
        }
    )

    clusters = ambari.get_clusters('localhost')

    ambari._make_request.assert_called_with('localhost/api/v1/clusters')
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


def test_get_host_metrics(instance):
    ambari = AmbariCheck(instances=[instance])
    ambari._get_hosts_info = MagicMock(return_value=responses.HOSTS_INFO)
    ambari._submit_gauge = MagicMock()
    ambari.set_external_tags = MagicMock()
    cluster_tag = ['ambari_cluster:cluster1']

    ambari.get_host_metrics('localhost', ['cluster1'])
    ambari.set_external_tags.assert_called_with(
        [('my_host_1', {'ambari': cluster_tag}), ('my_host_2', {'ambari': ['ambari_cluster:cluster1']})]
    )

    assert ambari._submit_gauge.call_count == 30
    ambari._submit_gauge.assert_has_calls(
        [
            call('boottime', 1555934503.0, cluster_tag, 'my_host_2'),
            call('cpu.cpu_idle', 62.8, cluster_tag, 'my_host_2'),
            call('cpu.cpu_nice', 0.0, cluster_tag, 'my_host_2'),
            call('cpu.cpu_num', 4.0, cluster_tag, 'my_host_2'),
            call('cpu.cpu_system', 5.1, cluster_tag, 'my_host_2'),
            call('cpu.cpu_user', 32.0, cluster_tag, 'my_host_2'),
            call('cpu.cpu_wio', 0.0, cluster_tag, 'my_host_2'),
            call('disk.disk_free', 124.35, cluster_tag, 'my_host_2'),
            call('disk.disk_total', 148.29, cluster_tag, 'my_host_2'),
            call('disk.read_bytes', 1594053632.0, cluster_tag, 'my_host_2'),
            call('disk.read_count', 42717.0, cluster_tag, 'my_host_2'),
            call('disk.read_time', 240986.0, cluster_tag, 'my_host_2'),
            call('disk.write_bytes', 117000843264.0, cluster_tag, 'my_host_2'),
            call('disk.write_count', 499318.0, cluster_tag, 'my_host_2'),
            call('disk.write_time', 5946304.0, cluster_tag, 'my_host_2'),
            call('load.load_fifteen', 0.99, cluster_tag, 'my_host_2'),
            call('load.load_five', 1.35, cluster_tag, 'my_host_2'),
            call('load.load_one', 0.57, cluster_tag, 'my_host_2'),
            call('memory.mem_cached', 3554248.0, cluster_tag, 'my_host_2'),
            call('memory.mem_free', 11327848.0, cluster_tag, 'my_host_2'),
            call('memory.mem_shared', 0.0, cluster_tag, 'my_host_2'),
            call('memory.mem_total', 15399208.0, cluster_tag, 'my_host_2'),
            call('memory.swap_free', 0.0, cluster_tag, 'my_host_2'),
            call('memory.swap_total', 0.0, cluster_tag, 'my_host_2'),
            call('network.bytes_in', 683.2346950556641, cluster_tag, 'my_host_2'),
            call('network.bytes_out', 12517.203580542699, cluster_tag, 'my_host_2'),
            call('network.pkts_in', 8.499187630576825, cluster_tag, 'my_host_2'),
            call('network.pkts_out', 10.498996484830196, cluster_tag, 'my_host_2'),
            call('process.proc_run', 0.0, cluster_tag, 'my_host_2'),
            call('process.proc_total', 128.0, cluster_tag, 'my_host_2'),
        ],
        any_order=True,
    )


def test_get_component_metrics(init_config, instance):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=responses.COMPONENT_METRICS)
    ambari._submit_gauge = MagicMock()
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
    ambari._submit_gauge.assert_has_calls(
        [
            call('cpu.cpu_idle', 90.3, namenode_tags),
            call('cpu.cpu_idle._avg', 90.3, namenode_tags),
            call('cpu.cpu_idle._max', 90.3, namenode_tags),
            call('cpu.cpu_idle._min', 90.3, namenode_tags),
            call('cpu.cpu_idle._sum', 90.3, namenode_tags),
            call('cpu.cpu_nice', 0.0, namenode_tags),
            call('cpu.cpu_nice._avg', 0.0, namenode_tags),
            call('cpu.cpu_nice._max', 0.0, namenode_tags),
            call('cpu.cpu_nice._min', 0.0, namenode_tags),
            call('cpu.cpu_nice._sum', 0.0, namenode_tags),
            call('cpu.cpu_system', 1.6333333333333335, namenode_tags),
            call('cpu.cpu_system._avg', 1.6333333333333335, namenode_tags),
            call('cpu.cpu_system._max', 1.6333333333333335, namenode_tags),
            call('cpu.cpu_system._min', 1.6333333333333335, namenode_tags),
            call('cpu.cpu_system._sum', 1.6333333333333335, namenode_tags),
            call('cpu.cpu_user', 8.033333333333333, namenode_tags),
            call('cpu.cpu_user._avg', 8.033333333333333, namenode_tags),
            call('cpu.cpu_user._max', 8.033333333333333, namenode_tags),
            call('cpu.cpu_user._min', 8.033333333333333, namenode_tags),
            call('cpu.cpu_user._sum', 8.033333333333333, namenode_tags),
            call('cpu.cpu_wio', 0.0, namenode_tags),
            call('cpu.cpu_wio._avg', 0.0, namenode_tags),
            call('cpu.cpu_wio._max', 0.0, namenode_tags),
            call('cpu.cpu_wio._min', 0.0, namenode_tags),
            call('cpu.cpu_wio._sum', 0.0, namenode_tags),
        ],
        any_order=True,
    )


def test_get_service_health(init_config, instance):
    ambari = AmbariCheck(init_config=init_config, instances=[instance])
    ambari._make_request = MagicMock(return_value=responses.SERVICE_HEALTH_METRICS)
    service_info = ambari._get_service_checks_info(
        'localhost', 'LabCluster', 'HDFS', service_tags=['ambari_cluster:LabCluster', 'ambari_service:hdfs']
    )

    ambari._make_request.assert_called_with('localhost/api/v1/clusters/LabCluster/services/HDFS?fields=ServiceInfo')

    assert service_info == [{'state': 0, 'tags': ['ambari_cluster:LabCluster', 'ambari_service:hdfs']}]


def test_default_config(instance):
    ambari = AmbariCheck(init_config={}, instances=[instance])

    assert ambari._should_collect_service_metrics() is True
    assert ambari._should_collect_service_status() is False


def test_should_not_collect_if_disabled(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': False, 'collect_service_status': False},
        instances=[instance],
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_service_status_and_metrics = MagicMock()
    ambari.check(instance)

    assert not ambari.get_service_status_and_metrics.called


def test_should_collect_host_metrics(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': False, 'collect_service_status': False},
        instances=[instance],
    )
    _mock_clusters(ambari)
    ambari.get_host_metrics = MagicMock()
    ambari.get_service_status_and_metrics = MagicMock()
    ambari.check(instance)

    assert ambari.get_host_metrics.called
    assert not ambari.get_service_status_and_metrics.called


def test_should_collect_service_metrics(instance):
    ambari = AmbariCheck(
        init_config={'collect_service_metrics': True, 'collect_service_status': False},
        instances=[instance],
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
        init_config={'collect_service_metrics': False, 'collect_service_status': True},
        instances=[instance],
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
