# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.docker import get_container_ip
from datadog_checks.dev.utils import get_metadata_metrics
from tests.common import SNMP_CONTAINER_NAME

from . import common, metrics
from .test_e2e_core_metadata import assert_device_metadata

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_v1_with_apc_ups_profile(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'snmp_version': 1,
            'community_string': 'apc_ups',
        }
    )
    assert_apc_ups_metrics(dd_agent_check, config)


def test_e2e_core_v3_no_auth_no_priv(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'user': 'datadogNoAuthNoPriv',
            'snmp_version': 3,
            'context_name': 'apc_ups',
            'community_string': '',
        }
    )
    assert_apc_ups_metrics(dd_agent_check, config)


def test_e2e_core_v3_with_auth_no_priv(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'user': 'datadogMD5NoPriv',
            'snmp_version': 3,
            'authKey': 'doggiepass',
            'authProtocol': 'MD5',
            'context_name': 'apc_ups',
            'community_string': '',
        }
    )
    assert_apc_ups_metrics(dd_agent_check, config)


def test_e2e_v1_with_apc_ups_profile_batch_size_1(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'snmp_version': 1,
            'community_string': 'apc_ups',
            'oid_batch_size': 1,
        }
    )
    assert_apc_ups_metrics(dd_agent_check, config)


def test_e2e_user_profiles(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'loader': 'core',
            'community_string': 'apc_ups_user',
        }
    )
    device_ip = instance['ip_address']

    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)
    profile_tags = [
        'snmp_profile:apc_ups_user',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        'device_namespace:default',
    ]
    tags = profile_tags + [
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    aggregator.assert_metric('snmp.upsAdvBatteryNumOfBattPacks', metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric(
        'snmp.upsAdvBatteryFullCapacity_userMetric', metric_type=aggregator.GAUGE, tags=tags, count=2
    )

    device = {
        'description': 'APC Web/SNMP Management Card (MB:v3.9.2 PF:v3.9.2 '
        'PN:apc_hw02_aos_392.bin AF1:v3.7.2 AN1:apc_hw02_sumx_372.bin '
        'MN:AP9619 HR:A10 SN: 5A1827E00000 MD:12/04/2007) (Embedded '
        'PowerNet SNMP Agent SW v2.2 compatible)',
        'id': 'default:' + device_ip,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'AP9619',
        'os_name': 'AOS',
        'os_version': 'v3.9.2',
        'product_name': 'APC Smart-UPS 600',
        'profile': 'apc_ups_user',
        'serial_number': 'fake-user-serial-num',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.318.1.999',
        'tags': [
            'device_namespace:default',
            "device_id:default:" + device_ip,
            "device_ip:" + device_ip,
            'firmware_version:2.0.3-test',
            'model:APC Smart-UPS 600',
            'serial_num:test_serial',
            'snmp_device:' + device_ip,
            'snmp_profile:apc_ups_user',
            'ups_name:testIdentName',
        ],
        'vendor': 'apc',
        'version': '2.0.3-test',
        'device_type': 'ups',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_user_profiles_that_extend_profile_with_same_name(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'loader': 'core',
            'community_string': 'palo-alto',
        }
    )
    device_ip = instance['ip_address']

    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)
    profile_tags = [
        'snmp_profile:palo-alto',
        'device_namespace:default',
    ]
    tags = profile_tags + [
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    aggregator.assert_metric('snmp.panSessionUtilization', metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric('snmp.panSessionUtilization_user', metric_type=aggregator.GAUGE, tags=tags, count=2)

    device = {
        'description': 'Palo Alto Networks PA-3000 series firewall',
        'id': 'default:' + device_ip,
        'id_tags': ['device_namespace:default', 'snmp_device:' + device_ip],
        'ip_address': device_ip,
        'model': 'PA-3020',
        'os_name': 'PAN-OS',
        'os_version': '9.0.5',
        'product_name': 'user palo-alto product name',
        'profile': 'palo-alto',
        'serial_number': '015351000009999',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25461.2.3.18',
        'tags': [
            'device_namespace:default',
            "device_id:default:" + device_ip,
            "device_ip:" + device_ip,
            'snmp_device:' + device_ip,
            'snmp_profile:palo-alto',
        ],
        'vendor': 'paloaltonetworks',
        'version': '9.0.5',
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)


def assert_apc_ups_metrics(dd_agent_check, config):
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    profile_tags = [
        'snmp_profile:apc_ups',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        'device_vendor:apc',
        'device_namespace:default',
    ]
    device_ip = instance['ip_address']

    tags = profile_tags + [
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')
    aggregator.assert_metric(
        'datadog.snmp.submitted_metrics', metric_type=aggregator.GAUGE, tags=tags + ['loader:core'], value=32
    )

    for metric in metrics.APC_UPS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)

    for metric, value in metrics.APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS:
        aggregator.assert_metric(metric, value=value, metric_type=aggregator.GAUGE, count=2, tags=tags)

    group_state_tags = tags + [
        'outlet_group_name:test_outlet',
        'ups_outlet_group_status_group_state:ups_outlet_group_status_unknown',
    ]

    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=group_state_tags,
    )
    aggregator.assert_metric('snmp.upsOutletGroupStatus', metric_type=aggregator.GAUGE, tags=group_state_tags, value=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_memory_cpu_f5_big_ip(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'f5-big-ip',
        }
    )
    # run a rate check, will execute two check runs to evaluate rate metrics
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    tags = [
        'device_namespace:default',
        'device_vendor:f5',
        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'snmp_profile:f5-big-ip',
    ]
    device_ip = instance['ip_address']

    tags += [
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')

    memory_metrics = ['memory.total', 'memory.used']

    for metric in memory_metrics:
        aggregator.assert_metric(
            'snmp.{}'.format(metric),
            metric_type=aggregator.GAUGE,
            tags=tags,
            count=2,
        )

    cpu_metrics = ['cpu.usage']
    cpu_indexes = ['0', '1']
    for metric in cpu_metrics:
        for cpu_index in cpu_indexes:
            cpu_tags = tags + ['cpu:{}'.format(cpu_index)]
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=cpu_tags,
                count=2,
            )


def test_e2e_core_discovery(dd_agent_check):
    config = common.generate_container_profile_config_with_ad('apc_ups')
    config['init_config']['loader'] = 'core'
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=False, times=3, pause=500)

    network = config['instances'][0]['network_address']
    ip_address = get_container_ip(SNMP_CONTAINER_NAME)
    tags = [
        # profile
        'snmp_profile:apc_ups',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        'device_vendor:apc',
        'device_namespace:default',
        # autodiscovery
        'autodiscovery_subnet:' + network,
        'snmp_device:' + ip_address,
        "device_ip:" + ip_address,
        "device_id:default:" + ip_address,
    ]

    tags_with_loader = tags + ['loader:core']

    # test that for a specific metric we are getting as many times as we are running the check
    # it might be off by 1 due to devices not being discovered yet at first check run
    aggregator.assert_metric(
        'snmp.devices_monitored', metric_type=aggregator.GAUGE, tags=tags_with_loader, at_least=2, value=1
    )
    aggregator.assert_metric('snmp.upsAdvBatteryTemperature', metric_type=aggregator.GAUGE, tags=tags, at_least=2)


def test_e2e_regex_match(dd_agent_check):
    metrics = [
        {
            'MIB': "IF-MIB",
            'table': {
                "name": "ifTable",
                "OID": "1.3.6.1.2.1.2.2",
            },
            'symbols': [
                {
                    "name": "ifInOctets",
                    "OID": "1.3.6.1.2.1.2.2.1.10",
                },
                {
                    "name": "ifOutOctets",
                    "OID": "1.3.6.1.2.1.2.2.1.16",
                },
            ],
            'metric_tags': [
                {
                    'tag': "interface",
                    'column': {
                        "name": "ifDescr",
                        "OID": "1.3.6.1.2.1.2.2.1.2",
                    },
                },
                {
                    'column': {
                        "name": "ifDescr",
                        "OID": "1.3.6.1.2.1.2.2.1.2",
                    },
                    'match': '(\\w)(\\w+)',
                    'tags': {'prefix': '\\1', 'suffix': '\\2'},
                },
            ],
        }
    ]
    config = common.generate_container_instance_config(metrics)
    instance = config['instances'][0]
    instance['metric_tags'] = [
        {
            "OID": "1.3.6.1.2.1.1.5.0",
            "symbol": "sysName",
            "match": "(\\d+)(\\w+)",
            "tags": {
                "digits": "\\1",
                "remainder": "\\2",
            },
        },
        {
            "OID": "1.3.6.1.2.1.1.5.0",
            "symbol": "sysName",
            "match": "(\\w)(\\w)",
            "tags": {
                "letter1": "\\1",
                "letter2": "\\2",
            },
        },
    ]
    config['init_config']['loader'] = 'core'
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)
    device_ip = instance['ip_address']

    # raw sysName: 41ba948911b9
    aggregator.assert_metric(
        'snmp.devices_monitored',
        tags=[
            'digits:41',
            'remainder:ba948911b9',
            'letter1:4',
            'letter2:1',
            'loader:core',
            'snmp_device:' + device_ip,
            'device_ip:' + device_ip,
            'device_id:default:' + device_ip,
            'device_namespace:default',
        ],
    )


def test_e2e_meraki_cloud_controller(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'meraki-cloud-controller',
        }
    )
    # run a rate check, will execute two check runs to evaluate rate metrics
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_container_ip(SNMP_CONTAINER_NAME)
    common_tags = [
        'snmp_profile:meraki-cloud-controller',
        'snmp_host:dashboard.meraki.com',
        'device_hostname:dashboard.meraki.com',
        'device_vendor:meraki',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        "device_ip:" + ip_address,
        "device_id:default:" + ip_address,
    ]

    common.assert_common_metrics(aggregator, tags=common_tags, is_e2e=True, loader='core')

    aggregator.assert_metric('snmp.ifNumber', metric_type=aggregator.GAUGE, tags=common_tags)

    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = [
        'device_name:Gymnasium',
        'product:MR16-HW',
        'network:L_NETWORK',
        'mac_address:02:02:00:66:f5:7f',
    ] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=2)

    tag_rows = [
        [
            'device_name:Gymnasium',
            'mac_address:02:02:00:66:f5:7f',
            'network:L_NETWORK',
            'product:MR16-HW',
            'status:online',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.meraki.dev', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    if_tags = ['interface:wifi0', 'index:4', 'mac_address:02:02:00:66:f5:00'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    # IF-MIB
    if_tags = ['interface:eth0', 'interface_index:11'] + common_tags
    for metric in metrics.IF_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=if_tags, count=1)

    for metric in metrics.IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    for metric in metrics.IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in metrics.IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    custom_speed_tags = ['interface:eth0', 'interface_index:11', 'speed_source:device'] + common_tags
    for metric in metrics.IF_CUSTOM_SPEED_GAUGES:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=custom_speed_tags, count=2
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=2, tags=common_tags)
    aggregator.assert_metric(
        'snmp.interface.status',
        metric_type=aggregator.GAUGE,
        tags=[
            'interface:eth0',
            'interface_index:11',
            'status:warning',
            'admin_status:down',
            'oper_status:lower_layer_down',
        ]
        + common_tags,
        value=1,
    )
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_core_detect_metrics_using_apc_ups_metrics(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'snmp_version': 1,
            'community_string': 'apc_ups_no_sysobjectid',
            'experimental_detect_metrics_enabled': True,
        }
    )
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    global_metric_tags = [
        # metric_tags from apc_ups.yaml
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        # metric_tags from _base.yaml
        'snmp_host:APC_UPS_NAME',
        'device_hostname:APC_UPS_NAME',
    ]
    device_ip = instance['ip_address']

    tags = global_metric_tags + [
        'device_namespace:default',
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')

    for metric in metrics.APC_UPS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric(
        'snmp.upsAdvBatteryFullCapacity_userMetric', metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    for metric, value in metrics.APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS:
        aggregator.assert_metric(metric, value=value, metric_type=aggregator.GAUGE, count=2, tags=tags)

    group_state_tags = tags + [
        'outlet_group_name:test_outlet',
        'ups_outlet_group_status_group_state:ups_outlet_group_status_unknown',
    ]

    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=group_state_tags,
    )

    interface_tags = ['interface:mgmt', 'interface_alias:desc1', 'interface_index:32'] + tags
    aggregator.assert_metric(
        'snmp.ifInErrors',
        metric_type=aggregator.COUNT,
        tags=interface_tags,
    )
    aggregator.assert_metric(
        'snmp.ifInErrors.rate',
        metric_type=aggregator.GAUGE,
        tags=interface_tags,
    )
    if_in_error_metrics = aggregator.metrics('snmp.ifInErrors.rate')
    assert len(if_in_error_metrics) == 1
    assert if_in_error_metrics[0].value > 0

    aggregator.assert_all_metrics_covered()


def test_e2e_core_cisco_csr(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update({'community_string': 'cisco-csr1000v'})
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)
    device_ip = instance['ip_address']

    global_tags = [
        'snmp_profile:cisco-csr1000v',
        'device_vendor:cisco',
        'device_namespace:default',
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
    ]

    common.assert_common_metrics(aggregator, global_tags, is_e2e=True, loader='core')

    metric_tags = global_tags + [
        'neighbor:244.12.239.177',
        'admin_status:start',
        'peer_state:established',
        'remote_as:26',
    ]

    for metric in metrics.PEER_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=metric_tags, count=2)

    for metric in metrics.PEER_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=metric_tags)

    aggregator.assert_metric('snmp.peerConnectionByState', metric_type=aggregator.GAUGE, tags=metric_tags, value=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_cisco_nexus(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update({'community_string': 'cisco-nexus'})
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)
    device_ip = instance['ip_address']

    common_tags = [
        'snmp_profile:cisco-nexus',
        'device_vendor:cisco',
        'device_namespace:default',
        "snmp_device:{}".format(device_ip),
        "device_ip:{}".format(device_ip),
        "device_id:default:{}".format(device_ip),
        'snmp_host:Nexus-eu1.companyname.managed',
        'device_hostname:Nexus-eu1.companyname.managed',
    ]

    common.assert_common_metrics(aggregator, common_tags, is_e2e=True, loader='core')

    indexes = {
        'GigabitEthernet1/0/1': '2',
        'GigabitEthernet1/0/2': '13',
        'GigabitEthernet1/0/3': '20',
        'GigabitEthernet1/0/4': '22',
        'GigabitEthernet1/0/5': '23',
        'GigabitEthernet1/0/6': '25',
        'GigabitEthernet1/0/7': '29',
        'GigabitEthernet1/0/8': '30',
    }
    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 9)]
    for metric in metrics.IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = [
            'interface:{}'.format(interface),
            'interface_alias:',
            'interface_index:{}'.format(indexes.get(interface)),
        ] + common_tags
        for metric in metrics.IF_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in metrics.IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in metrics.IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
        for metric in metrics.IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        custom_speed_tags = tags + ['speed_source:device']
        for metric in metrics.IF_CUSTOM_SPEED_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=custom_speed_tags, count=2
            )

    for metric in metrics.TCP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)

    for metric in metrics.TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)

    for metric in metrics.UDP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:celsius'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=2)

    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in metrics.FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in metrics.CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)

    for index, state in [
        (3, 'critical'),
        (6, 'not_functioning'),
        (8, 'not_functioning'),
        (11, 'not_functioning'),
        (13, 'critical'),
        (14, 'not_functioning'),
        (20, 'not_functioning'),
        (21, 'shutdown'),
        (31, 'not_present'),
    ]:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['temp_state:{}'.format(state), 'temp_index:{}'.format(index)] + common_tags,
        )

    power_supply_tags = ['power_source:unknown', 'power_status_descr:Jaded driving their their their'] + common_tags
    aggregator.assert_metric('snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=power_supply_tags)

    power_supply_tags = [
        'cisco_env_mon_supply_state:normal',
        'power_source:unknown',
        'power_status_descr:Jaded driving their their their',
    ] + common_tags
    aggregator.assert_metric('snmp.ciscoEnvMonSupplyStatus', metric_type=aggregator.GAUGE, tags=power_supply_tags)

    fan_indices = [4, 6, 7, 16, 21, 22, 25, 27]
    for index in fan_indices:
        tags = ['fan_status_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric(
        'snmp.cswStackPortOperStatus',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['interface:GigabitEthernet1/0/1'],
    )

    tag_rows = [
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name1'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name2'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name3'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name4'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name5'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name6'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name7'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_name:name8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=tag_row + common_tags)

    frus = [2, 7, 8, 21, 26, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    tag_rows = [
        ['fru:6', 'power_admin_status:power_cycle', 'power_oper_status:on_but_inline_power_fail'],
        ['fru:7', 'power_admin_status:inline_on', 'power_oper_status:off_denied'],
        ['fru:15', 'power_admin_status:inline_auto', 'power_oper_status:off_cooling'],
        ['fru:16', 'power_admin_status:off', 'power_oper_status:off_cooling'],
        ['fru:19', 'power_admin_status:on', 'power_oper_status:off_env_fan'],
        ['fru:27', 'power_admin_status:inline_on', 'power_oper_status:failed'],
        ['fru:30', 'power_admin_status:on', 'power_oper_status:off_env_fan'],
        ['fru:31', 'power_admin_status:on', 'power_oper_status:off_denied'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFRUPowerStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name1', 'switch_state:progressing'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name2', 'switch_state:ready'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name3', 'switch_state:added'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name4', 'switch_state:ver_mismatch'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name5', 'switch_state:progressing'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name6', 'switch_state:sdm_mismatch'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name7', 'switch_state:provisioned'],
        ['mac_addr:ff:ff:ff:ff:ff:ff', 'entity_physical_name:name8', 'switch_state:ver_mismatch'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cswSwitchInfo', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fru:1', 'cefc_fan_tray_oper_status:down'],
        ['fru:2', 'cefc_fan_tray_oper_status:unknown'],
        ['fru:4', 'cefc_fan_tray_oper_status:unknown'],
        ['fru:27', 'cefc_fan_tray_oper_status:unknown'],
        ['fru:30', 'cefc_fan_tray_oper_status:warning'],
        ['fru:31', 'cefc_fan_tray_oper_status:unknown'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFanTrayStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fan_status_descr:fan_1', 'fan_state:critical', 'fan_status_index:4'],
        ['fan_status_descr:fan_2', 'fan_state:not_functioning', 'fan_status_index:6'],
        ['fan_status_descr:fan_3', 'fan_state:critical', 'fan_status_index:7'],
        ['fan_status_descr:fan_4', 'fan_state:not_present', 'fan_status_index:16'],
        ['fan_status_descr:fan_8', 'fan_state:normal', 'fan_status_index:30'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    cpu_ids = [6692, 3173, 54474, 63960, 11571, 38253, 30674, 52063]
    for cpu in cpu_ids:
        aggregator.assert_metric(
            'snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + ['cpu:{}'.format(cpu)]
        )

    nexus_mem_metrics = ["memory.free", "memory.used", "memory.usage"]
    for metric in nexus_mem_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags + ['mem:1'])

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=2)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_cisco_legacy_wlc(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-5500-wlc',
        }
    )
    config['init_config']['loader'] = 'core'
    instance = config['instances'][0]

    ip_address = get_container_ip(SNMP_CONTAINER_NAME)

    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    tags = [
        'device_namespace:default',
        'snmp_profile:cisco-legacy-wlc',
        'device_vendor:cisco',
        'snmp_host:DDOGWLC',
        'device_hostname:DDOGWLC',
        'snmp_device:' + ip_address,
        "device_ip:" + ip_address,
        "device_id:default:" + ip_address,
    ]
    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')

    SYSTEM_GAUGES = ["cpu.usage", "memory.free", "memory.total", "memory.usage"]

    for metric in SYSTEM_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    if_tags = ["interface:If1", "interface_index:1"] + tags

    for metric in metrics.IF_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=if_tags)

    for metric in metrics.IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    for metric in metrics.IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    for metric in metrics.IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    for metric in metrics.IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    custom_speed_tags = if_tags + ['speed_source:device']
    for metric in metrics.IF_CUSTOM_SPEED_GAUGES:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=custom_speed_tags, count=2
        )

    TCP_COUNTS = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]

    for metric in TCP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags)

    for metric in metrics.TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    UDP_COUNTS = ['udpNoPorts', 'udpInErrors']

    for metric in UDP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags)

    ap_tags = [
        'ap_location:default location',
        'ap_name:DD-AP-1',
        'ap_ip_address:1.1.1.1',
        'ap_mac_address:  00 00 00 00 00 01',
    ] + tags

    ap_status_tags = ['ap_oper_status:associated', 'ap_admin_status:enable'] + ap_tags

    aggregator.assert_metric("snmp.accessPoint".format(), metric_type=aggregator.GAUGE, tags=ap_status_tags, value=1)

    if_ap_tags = ["ap_if_slot_id:0"] + ap_tags
    if_ap_status_tags = ['ap_if_oper_status:up', 'ap_if_admin_status:enable'] + if_ap_tags

    AP_IF_GAUGE_METRICS = [
        "bsnAPIfLoadChannelUtilization",
        "bsnAPIfLoadRxUtilization",
        "bsnAPIfLoadTxUtilization",
        "bsnAPIfPoorSNRClients",
    ]

    for metric in AP_IF_GAUGE_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_ap_tags)

    aggregator.assert_metric(
        "snmp.accessPointInterface".format(), metric_type=aggregator.GAUGE, tags=if_ap_status_tags, value=1
    )

    aggregator.assert_metric('snmp.bsnApIfNoOfUsers', metric_type=aggregator.GAUGE, tags=if_ap_tags)

    wlan_tags = ["ssid:DD-1", "wlan_index:17"] + tags

    wlan_status_tags = ['wlan_row_status:active', 'wlan_admin_status:enable'] + wlan_tags

    aggregator.assert_metric("snmp.wlan".format(), metric_type=aggregator.GAUGE, tags=wlan_status_tags, value=1)

    aggregator.assert_metric('snmp.bsnDot11EssNumberOfMobileStations', metric_type=aggregator.GAUGE, tags=wlan_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
