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
                'status:{}'.format(interface.status),
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

    assert_check_metrics(aggregator)

    # Assert coverage for this check on this instance
    aggregator.assert_all_metrics_covered()


def assert_fabric_port_ingr_metrics(aggregator):
    metric_name = 'cisco_aci.fabric.port.ingr_total.bytes.cum'
    aggregator.assert_metric(metric_name, value=1675297119938.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=1671489933399.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=1672846899143.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=1670820627869.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.flood'
    aggregator.assert_metric(metric_name, value=72037037.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=40530849.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=95792629.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=86137773.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.flood.cum'
    aggregator.assert_metric(metric_name, value=1675362699996.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(metric_name, value=1666006928703.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(metric_name, value=1684600000562.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(metric_name, value=1672454392057.0, tags=interface_tags_102_eth2, hostname=hn102)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.multicast'
    aggregator.assert_metric(name=metric_name, value=52378511.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=65700640.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=11168323.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=54999085.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=58960634.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=85858244.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.multicast.cum'
    aggregator.assert_metric(name=metric_name, value=1683545926517.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670381374528.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1660441184789.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1676380152464.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=89806584162.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=90202911073.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.unicast'
    aggregator.assert_metric(name=metric_name, value=50443812.0, tags=interface_tags_101_eth1, hostname=hn101),
    aggregator.assert_metric(name=metric_name, value=70147142.0, tags=interface_tags_101_eth2, hostname=hn101),
    aggregator.assert_metric(name=metric_name, value=32704715.0, tags=interface_tags_102_eth1, hostname=hn102),
    aggregator.assert_metric(name=metric_name, value=23770059.0, tags=interface_tags_102_eth2, hostname=hn102),
    aggregator.assert_metric(name=metric_name, value=105702610.0, tags=interface_tags_201_eth1, hostname=hn201),
    aggregator.assert_metric(name=metric_name, value=29485355.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_bytes.unicast.cum'
    aggregator.assert_metric(name=metric_name, value=1675139222191.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1672360868187.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670246291096.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1671433541603.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=91884083475.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=89489460623.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_total.bytes.rate'
    aggregator.assert_metric(name=metric_name, value=6956222.344972, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5982729.140943, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=6364450.663467, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=6306235.087953, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=6856048.66832, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=8136970.057186, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_total.pkts'
    aggregator.assert_metric(name=metric_name, value=6134790.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=9417736.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1283587.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=2523746.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=4395152.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=8179023.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.ingr_total.pkts.rate'
    aggregator.assert_metric(name=metric_name, value=668161.02377, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=535540.893299, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=659485.489255, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=539835.180155, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=663144.955211, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=491355.434696, tags=interface_tags_201_eth2, hostname=hn201)


def assert_fabric_port_egr_metrics(aggregator):
    metric_name = 'cisco_aci.fabric.port.egr_bytes.flood'
    aggregator.assert_metric(name=metric_name, value=104004695.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=56064447.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=104445269.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=56895557.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=113990420.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=94615739.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.flood.cum'
    aggregator.assert_metric(name=metric_name, value=1676377889535.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670589187638.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1679981059227.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1670301584332.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=92087744539.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=90271151687.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.multicast'
    aggregator.assert_metric(name=metric_name, value=71889611.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=106111131.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=27578882.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=37234011.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=34219648.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=13281532.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.multicast.cum'
    aggregator.assert_metric(name=metric_name, value=1680127522943.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1676144173003.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1676466708628.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1666025595868.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=89826571867.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=91603890026.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.unicast'
    aggregator.assert_metric(name=metric_name, value=72418019.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=73098992.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=20751017.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=75906220.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=107694686.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=83932303.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_bytes.unicast.cum'
    aggregator.assert_metric(name=metric_name, value=1670890020444.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670549333856.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670486675842.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1666001799571.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=90218859190.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=89849409871.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.buffer'
    aggregator.assert_metric(name=metric_name, value=270.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=47.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=53.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=48.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=79.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=212.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.buffer.cum'
    aggregator.assert_metric(name=metric_name, value=5642170.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5627840.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5635225.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=5624957.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=309747.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=316071.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_drop_pkts.errors'
    aggregator.assert_metric(name=metric_name, value=5628789.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5620169.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5603128.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=5616188.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=300591.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=304779.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_total.bytes.cum'
    aggregator.assert_metric(name=metric_name, value=1675133556076.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1666659548273.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=1670187404090.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=1675540544688.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=88024859871.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=91306228204.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_total.bytes.rate'
    aggregator.assert_metric(name=metric_name, value=5912983.438726, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=4571615.606489, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=5993816.23426, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=6111042.629652, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=7441353.135248, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=5641867.661761, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_total.pkts'
    aggregator.assert_metric(name=metric_name, value=4276778.0, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=6653961.0, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=6550971.0, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=2521895.0, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=617161.0, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=10110431.0, tags=interface_tags_201_eth2, hostname=hn201)

    metric_name = 'cisco_aci.fabric.port.egr_total.pkts.rate'
    aggregator.assert_metric(name=metric_name, value=544477.282611, tags=interface_tags_101_eth1, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=522656.617261, tags=interface_tags_101_eth2, hostname=hn101)
    aggregator.assert_metric(name=metric_name, value=644033.870439, tags=interface_tags_102_eth1, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=561897.727715, tags=interface_tags_102_eth2, hostname=hn102)
    aggregator.assert_metric(name=metric_name, value=481008.637927, tags=interface_tags_201_eth1, hostname=hn201)
    aggregator.assert_metric(name=metric_name, value=609451.091738, tags=interface_tags_201_eth2, hostname=hn201)


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
    aggregator.assert_metric(metric_name, value=10.0, tags=tagsapic1, hostname=hn1)


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
    aggregator.assert_metric(metric_name, value=14.0, tags=tagsapic1, hostname=hn1)


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
    aggregator.assert_metric(metric_name, value=10.0, tags=tagsapic1, hostname=hn1)


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
    aggregator.assert_metric(metric_name, value=10814699.0, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=43008145.0, tags=tagsapic1, hostname=hn1)


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
    aggregator.assert_metric(metric_name, value=10823444.0, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=43199760.0, tags=tagsapic1, hostname=hn1)


def assert_fabric_node_mem_min(aggregator):
    metric_name = 'cisco_aci.fabric.node.mem.min'
    aggregator.assert_metric(metric_name, value=10534296.0, tags=tagsleaf101, hostname=hn101)
    aggregator.assert_metric(metric_name, value=10462616.0, tags=tagsleaf102, hostname=hn102)
    aggregator.assert_metric(metric_name, value=10788240.0, tags=tagsspine201, hostname=hn201)
    aggregator.assert_metric(metric_name, value=42962460.0, tags=tagsapic1, hostname=hn1)


def assert_fabric_node_utilized(aggregator):
    metric_name = 'cisco_aci.capacity.apic.fabric_node.utilized'
    aggregator.assert_metric(metric_name, value=0.0, tags=['cisco', 'project:cisco_aci'], hostname='')


def assert_check_metrics(aggregator):
    aggregator.assert_metric(
        'datadog.cisco_aci.check_interval', metric_type=aggregator.MONOTONIC_COUNT, count=1, tags=['cisco']
    )
    aggregator.assert_metric('datadog.cisco_aci.check_duration', metric_type=aggregator.GAUGE, count=1, tags=['cisco'])
