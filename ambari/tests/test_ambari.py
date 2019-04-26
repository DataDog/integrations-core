# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.ambari import AmbariCheck
from unittest.mock import MagicMock

HOST_METRICS = {
    'boottime': 1555934503.0,
    'cpu': {
        'cpu_idle': 62.8,
        'cpu_nice': 0.0,
        'cpu_num': 4.0,
        'cpu_system': 5.1,
        'cpu_user': 32.0,
        'cpu_wio': 0.0
    },
    'disk': {
        'disk_free': 124.35,
        'disk_total': 148.29,
        'read_bytes': 1594053632.0,
        'read_count': 42717.0,
        'read_time': 240986.0,
        'write_bytes': 117000843264.0,
        'write_count': 499318.0,
        'write_time': 5946304.0
    },
    'load': {'load_fifteen': 0.99, 'load_five': 1.35, 'load_one': 0.57},
    'memory': {
        'mem_cached': 3554248.0,
        'mem_free': 11327848.0,
        'mem_shared': 0.0,
        'mem_total': 15399208.0,
        'swap_free': 0.0,
        'swap_total': 0.0
    },
    'network': {
        'bytes_in': 683.2346950556641,
        'bytes_out': 12517.203580542699,
        'pkts_in': 8.499187630576825,
        'pkts_out': 10.498996484830196
    },
    'process': {'proc_run': 0.0, 'proc_total': 128.0}
}


def test_flatten_service_metrics():
    metrics = AmbariCheck.flatten_service_metrics({"metric_a": 10,
                                                        "metric_b": 15,
                                                        "metric_c": {"submetric_c": "hello"},
                                                        "metric_d": {"submetric_d": {'subsub_d': 25}}
                                                        }, "pfx")
    assert metrics == {'pfx.metric_a': 10,
                       'pfx.metric_b': 15,
                       'pfx.submetric_c': 'hello',
                       'pfx.subsub_d': 25
                       }


def test_flatten_host_metrics():
    metrics = AmbariCheck.flatten_host_metrics(HOST_METRICS)
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
        'process.proc_total': 128.0
    }


def test_get_clusters(instance, authentication):
    ambari = AmbariCheck(instance=instance)
    ambari.make_request = MagicMock(return_value={
        'href': 'localhost/api/v1/clusters',
        'items': [{'href': 'localhost/api/v1/clusters/LabCluster',
                   'Clusters': {'cluster_name': 'LabCluster'}}
                  ]
    })
    clusters = ambari.get_clusters('localhost', authentication)
    ambari.make_request.assert_called_with('localhost/api/v1/clusters', authentication)
    assert clusters == ['LabCluster']


def test_get_hosts(instance, authentication):
    ambari = AmbariCheck(instance=instance)
    ambari.make_request = MagicMock(return_value={
        'href': 'localhost/api/v1/clusters/myCluster/hosts?fields=metrics',
        'items': [
            {
                'href': 'localhost/api/v1/clusters/myCluster/hosts/my_host_1',
                'Hosts': {
                    'cluster_name': 'myCluster',
                    'host_name': 'my_host_1'
                }
             },
            {
                'href': 'localhost/api/v1/clusters/myCluster/hosts/my_host_2',
                'Hosts': {
                    'cluster_name': 'myCluster',
                    'host_name': 'my_host_2'
                },
                'metrics': HOST_METRICS
            }
        ]
    })
    hosts = ambari.get_hosts('localhost', authentication, 'myCluster')
    ambari.make_request.assert_called_with('localhost/api/v1/clusters/myCluster/hosts?fields=metrics', authentication)
    assert len(hosts) == 2
    assert hosts[0]['Hosts']['host_name'] == 'my_host_1'
    assert hosts[1]['Hosts']['host_name'] == 'my_host_2'
    assert hosts[1]['metrics'] is not None





