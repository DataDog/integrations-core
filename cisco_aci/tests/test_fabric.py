# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from freezegun import freeze_time

from datadog_checks.base.utils.containers import hash_mutable
from datadog_checks.cisco_aci import CiscoACICheck
from datadog_checks.cisco_aci.api import Api

from . import common
from .fixtures.metadata import (
    EXPECTED_INTERFACE_METADATA,
    EXPECTED_METADATA_EVENTS,
)

node101 = '10.0.200.0'
node102 = '10.0.200.1'
node201 = '10.0.200.5'
node1 = '10.0.200.4'

hn101 = 'pod-1-node-101'
hn102 = 'pod-1-node-102'
hn201 = 'pod-1-node-201'
hn1 = 'pod-1-node-1'

device_hn101 = 'leaf101'
device_hn102 = 'leaf102'
device_hn201 = 'spine201'
device_hn1 = 'apic1'

namespace = 'default'

node101_port1 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.0:1'
node101_port2 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.0:2'
node102_port1 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.1:1'
node102_port2 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.1:2'
node201_port1 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.5:1'
node201_port2 = 'dd.internal.resource:ndm_interface_user_tags:default:10.0.200.5:2'

device_tags_101 = [
    'device_hostname:{}'.format(device_hn101),
    'device_id:{}:{}'.format(namespace, node101),
    'device_ip:{}'.format(node101),
    'device_namespace:{}'.format(namespace),
    'dd.internal.resource:ndm_device_user_tags:default:10.0.200.0',
]
device_tags_102 = [
    'device_hostname:{}'.format(device_hn102),
    'device_id:{}:{}'.format(namespace, node102),
    'device_ip:{}'.format(node102),
    'device_namespace:{}'.format(namespace),
    'dd.internal.resource:ndm_device_user_tags:default:10.0.200.1',
]
device_tags_201 = [
    'device_hostname:{}'.format(device_hn201),
    'device_id:{}:{}'.format(namespace, node201),
    'device_ip:{}'.format(node201),
    'device_namespace:{}'.format(namespace),
    'dd.internal.resource:ndm_device_user_tags:default:10.0.200.5',
]
device_tags_1 = [
    'device_hostname:{}'.format(device_hn1),
    'device_id:{}:{}'.format(namespace, node1),
    'device_ip:{}'.format(node1),
    'device_namespace:{}'.format(namespace),
    'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
]

tags000 = ['cisco', 'project:cisco_aci', 'medium:broadcast', 'snmpTrapSt:enable', 'fabric_pod_id:1']
tags101 = tags000 + ['node_id:101'] + device_tags_101
tags102 = tags000 + ['node_id:102'] + device_tags_102
tags201 = tags000 + ['node_id:201'] + device_tags_201
tags = ['fabric_state:active', 'fabric_pod_id:1', 'cisco', 'project:cisco_aci']
leaf101 = ['switch_role:leaf', 'apic_role:leaf', 'node_id:101']
leaf102 = ['switch_role:leaf', 'apic_role:leaf', 'node_id:102']
leaf201 = ['switch_role:spine', 'apic_role:spine', 'node_id:201']

tagsleaf101 = tags + leaf101 + device_tags_101
tagsleaf102 = tags + leaf102 + device_tags_102
tagsspine201 = tags + leaf201 + device_tags_201
tagsapic1 = [
    'apic_role:controller',
    'node_id:1',
    'fabric_state:unknown',
    'fabric_pod_id:1',
    'cisco',
    'project:cisco_aci',
] + device_tags_1

interface_tags_101_eth1 = tags101 + ['port:eth1/1', node101_port1]
interface_tags_101_eth2 = tags101 + ['port:eth1/2', node101_port2]
interface_tags_102_eth1 = tags102 + ['port:eth1/1', node102_port1]
interface_tags_102_eth2 = tags102 + ['port:eth1/2', node102_port2]
interface_tags_201_eth1 = tags201 + ['port:eth5/1', node201_port1]
interface_tags_201_eth2 = tags201 + ['port:eth5/2', node201_port2]


def test_fabric_mocked(aggregator):
    check = CiscoACICheck(common.CHECK_NAME, {}, [common.CONFIG_WITH_TAGS])
    api = Api(common.ACI_URLS, check.http, common.USERNAME, password=common.PASSWORD, log=check.log)
    api.wrapper_factory = common.FakeFabricSessionWrapper
    check._api_cache[hash_mutable(common.CONFIG_WITH_TAGS)] = api

    with freeze_time("2012-01-14 03:21:34"):
        check.check({})

        ndm_metadata = aggregator.get_event_platform_events("network-devices-metadata")
        expected_metadata = [event.model_dump(mode="json", exclude_none=True) for event in EXPECTED_METADATA_EVENTS]
        assert ndm_metadata == expected_metadata

        interface_tag_mapping = {
            'default:10.0.200.0': (device_hn101, hn101),
            'default:10.0.200.1': (device_hn102, hn102),
            'default:10.0.200.5': (device_hn201, hn201),
        }

        for interface in EXPECTED_INTERFACE_METADATA:
            device_hn, hn = interface_tag_mapping.get(interface.device_id)
            device_namespace, device_ip = interface.device_id.split(':')
            interface_tags = [
                'port:{}'.format(interface.name),
                'medium:broadcast',
                'snmpTrapSt:enable',
                'node_id:{}'.format(hn.split('-')[-1]),
                'fabric_pod_id:1',
                'device_ip:{}'.format(device_ip),
                'device_namespace:{}'.format(device_namespace),
                'device_hostname:{}'.format(device_hn),
                'device_id:{}'.format(interface.device_id),
                'port.status:{}'.format(interface.status),
                'dd.internal.resource:ndm_device_user_tags:{}'.format(interface.device_id),
                'dd.internal.resource:ndm_interface_user_tags:{}:{}'.format(interface.device_id, interface.index),
            ]
            aggregator.assert_metric('cisco_aci.fabric.port.status', value=1.0, tags=interface_tags, hostname=device_hn)

    ### Fabric Node Metrics ###
    assert_fabric_node_cpu_avg(aggregator)
    assert_fabric_node_cpu_idle_avg(aggregator)
    assert_fabric_node_cpu_idle_max(aggregator)
    assert_fabric_node_cpu_idle_min(aggregator)
    assert_fabric_node_cpu_max(aggregator)
    assert_fabric_node_cpu_min(aggregator)
    assert_fabric_node_health_cur(aggregator)
    assert_fabric_node_health_max(aggregator)
    assert_fabric_node_health_min(aggregator)
    assert_fabric_node_mem_avg(aggregator)
    assert_fabric_node_mem_free_avg(aggregator)
    assert_fabric_node_mem_free_max(aggregator)
    assert_fabric_node_mem_free_min(aggregator)
    assert_fabric_node_mem_max(aggregator)
    assert_fabric_node_mem_min(aggregator)

    assert_fabric_node_utilized(aggregator)

    ### Fabric Port Metrics ###
    assert_fabric_port_egr_metrics(aggregator)
    assert_fabric_port_ingr_metrics(aggregator)
    assert_fabric_port_fault_counters(aggregator)

    ### Check Metrics ###
    aggregator.assert_metric(
        'datadog.cisco_aci.check_interval', metric_type=aggregator.MONOTONIC_COUNT, count=1, tags=['cisco']
    )
    aggregator.assert_metric('datadog.cisco_aci.check_duration', metric_type=aggregator.GAUGE, count=1, tags=['cisco'])

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def assert_fabric_node_cpu_avg(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.avg'

    aggregator.assert_metric(metric_name, value=5.099699999999999, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.6183149999999955, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.986987999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.5842289999999934, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=5.004906000000005, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.652297000000004, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.986576999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.6488959999999935, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=5.079667000000001, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.514444999999995, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=5.043931999999998, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.568399999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=4.930536000000004, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.497870000000006, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.910968999999994, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.510873000000004, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.940123999999997, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.563612000000006, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.955282999999994, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.540270000000007, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=5.002808999999999, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.462749000000002, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.969452000000004, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=4.465964999999997, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=19.234358, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.76097, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=19.010105999999993, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.649265, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=18.986099999999993, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.444975, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=19.101067999999998, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.846044000000006, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=18.921163000000007, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.827544000000003, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=19.068934999999996, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=17.649720000000002, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(
        metric_name,
        value=10.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )


def assert_fabric_node_cpu_idle_avg(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.idle.avg'
    aggregator.assert_metric(metric_name, value=94.9003, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.381685, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.013012, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.415771, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=94.995094, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.347703, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.013423, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.351104, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=94.920333, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.485555, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=94.956068, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.4316, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95.069464, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.50213, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.089031, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.489127, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.059876, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.436388, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.044717, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.45973, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=94.997191, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.537251, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.030548, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=95.534035, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=80.765642, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.23903, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=80.989894, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.350735, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=81.0139, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.555025, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=80.898932, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.153956, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=81.078837, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.172456, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=80.931065, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=82.35028, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_cpu_idle_max(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.idle.max'
    aggregator.assert_metric(metric_name, value=96.391948, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.448433, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.325758, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.400152, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.387064, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.435343, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.396966, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.382037, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.29256, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.363177, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.432186, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.364095, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=96.663283, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.51295, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.569987, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.614452, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.5012, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.490342, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.445677, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.46286, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.452916, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.611027, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.499874, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=96.529531, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=88.118307, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=87.630706, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.107417, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.193384, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.364379, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.184365, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.27129, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=87.903431, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.510747, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.244314, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=88.002047, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=87.982613, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_cpu_idle_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.idle.min'
    aggregator.assert_metric(metric_name, value=83.786848, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=92.911296, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=86.315524, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=93.498803, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=85.685484, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=92.499371, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=86.347003, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=93.486493, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=85.575467, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=93.764988, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=85.712484, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=93.505349, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=86.685125, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=93.787802, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=85.80775, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=93.592331, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=86.875946, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=94.04867, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=85.712486, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=93.072061, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=86.072144, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=93.783102, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=85.889029, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=93.796495, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=59.512319, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=68.422392, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=59.588519, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=66.581892, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=59.29878, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=66.844242, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=59.42435, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=71.120142, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=60.621498, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=67.77891, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=60.925973, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=68.634969, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_cpu_max(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.max'
    aggregator.assert_metric(metric_name, value=3.6080520000000007, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.5515670000000057, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.6742420000000067, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.5998479999999944, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.612936000000005, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.564656999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.603033999999994, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.617963000000003, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.7074400000000054, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.636823000000007, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.5678139999999985, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.635904999999994, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=3.336716999999993, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.4870499999999964, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.4300130000000024, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.385548, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.498800000000003, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.5096580000000017, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.5543229999999966, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.5371399999999937, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.547083999999998, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.388972999999993, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.5001259999999945, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=3.4704689999999943, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(
        metric_name,
        value=14.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )
    aggregator.assert_metric(metric_name, value=11.881692999999999, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=12.369293999999996, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.892583000000002, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.806616000000005, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.635621, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.815635, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.728710000000007, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=12.096569000000002, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.489253000000005, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.755685999999997, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=11.997952999999995, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=12.017387, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_cpu_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.cpu.min'
    aggregator.assert_metric(metric_name, value=16.213151999999994, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=7.088704000000007, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13.684476000000004, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=6.501197000000005, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=14.314515999999998, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=7.5006290000000035, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13.652997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=6.513507000000004, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=14.424532999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=6.235011999999998, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=14.287515999999997, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=6.494651000000005, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13.314875, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=6.212198000000001, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=14.192250000000001, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=6.4076689999999985, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=13.124054000000001, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=5.951329999999999, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=14.287514000000002, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=6.927938999999995, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=13.927856000000006, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=6.2168980000000005, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=14.110971000000006, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=6.203505000000007, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(
        metric_name,
        value=10.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )
    aggregator.assert_metric(metric_name, value=40.487681, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=31.577607999999998, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=40.411481, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=33.418108000000004, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=40.70122, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=33.155758000000006, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=40.57565, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=28.879858, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=39.378502, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=32.221090000000004, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=39.074027, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=31.365031000000002, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_health_cur(aggregator):
    metric_name = 'cisco_aci.fabric.node.health.cur'
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=99.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_health_max(aggregator):
    metric_name = 'cisco_aci.fabric.node.health.max'
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=99.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_health_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.health.min'
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=72.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=99.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_avg(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.avg'
    aggregator.assert_metric(metric_name, value=10559963.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=10491187.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(
        metric_name,
        value=43008145.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )
    aggregator.assert_metric(metric_name, value=10814699.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_free_avg(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.free.avg'
    aggregator.assert_metric(metric_name, value=13878048.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13946824.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=5453784.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_free_max(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.free.max'
    aggregator.assert_metric(metric_name, value=13903716.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13975396.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=5480244.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_free_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.free.min'
    aggregator.assert_metric(metric_name, value=13867492.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=13928332.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=5445040.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_max(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.max'
    aggregator.assert_metric(metric_name, value=10570520.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=10509680.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(
        metric_name,
        value=43199760.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )
    aggregator.assert_metric(metric_name, value=10823444.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_mem_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.min'
    aggregator.assert_metric(metric_name, value=10534296.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=10462616.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(
        metric_name,
        value=42962460.0,
        tags=[
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'fabric_pod_id:1',
            'cisco',
            'project:cisco_aci',
            'dd.internal.resource:ndm_device_user_tags:default:10.0.200.4',
        ],
        hostname='pod-1-node-1',
    )
    aggregator.assert_metric(metric_name, value=10788240.0, tags=tagsspine201, hostname=hn201)


def assert_fabric_node_utilized(aggregator):
    metric_name = 'cisco_aci.capacity.apic.fabric_node.utilized'
    aggregator.assert_metric(metric_name, value=0.0, tags=['cisco', 'project:cisco_aci'], hostname='')


def assert_fabric_port_fault_counters(aggregator):
    metric_name = 'cisco_aci.fabric.port.fault_counter.crit'
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.fault_counter.warn'
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)


def assert_fabric_port_ingr_metrics(aggregator):
    metric_name = 'cisco_aci.fabric.port.ingr_bytes.flood'
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.flood.cum'
    aggregator.assert_metric(metric_name, value=94.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=188.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=94.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=188.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.multicast'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.multicast.cum'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.unicast'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101),
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101),
    aggregator.assert_metric(name=metric_name, value=572700.0, tags=interface_tags_102_eth1, hostname=hn102),
    aggregator.assert_metric(name=metric_name, value=830768.0, tags=interface_tags_102_eth2, hostname=hn102),

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.unicast.cum'
    aggregator.assert_metric(name=metric_name, value=348576910354.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=261593756336.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=163927500335.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=156170003449.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_total.bytes.cum'
    aggregator.assert_metric(metric_name, value=348576910448.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=261593756524.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=163927500429.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=156170003637.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_total.bytes.rate'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=73281.118519, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=101114.177778, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_total.pkts'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=3240.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=4750.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_total.pkts.rate'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=401.2, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=583.388889, tags=interface_tags_102_eth2, hostname=hn102)


def assert_fabric_port_egr_metrics(aggregator):
    metric_name = 'cisco_aci.fabric.port.egr_bytes.flood'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.flood.cum'
    aggregator.assert_metric(name=metric_name, value=3196.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=3196.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=2992.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=2992.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.multicast'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.multicast.cum'
    aggregator.assert_metric(name=metric_name, value=236383592.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=236450478.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=236470350.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=236534244.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.unicast'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=758598.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=770134.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.unicast.cum'
    aggregator.assert_metric(name=metric_name, value=370475792067.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=263131271762.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=134113229564.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=203653209556.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.buffer'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.buffer.cum'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.errors'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_total.bytes.cum'
    aggregator.assert_metric(name=metric_name, value=370712178855.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=263367725436.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=134349702906.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=203889746792.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_total.bytes.rate'
    aggregator.assert_metric(name=metric_name, value=12.69, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=12.69, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=91797.314815, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=127111.525926, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_total.pkts'
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=4491.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=3611.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.egr_total.pkts.rate'
    aggregator.assert_metric(name=metric_name, value=0.03, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=0.03, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=535.933333, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=480.72963, tags=interface_tags_102_eth2, hostname=hn102)
