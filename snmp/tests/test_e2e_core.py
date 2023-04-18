# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.dev.docker import get_container_ip
from tests.common import SNMP_CONTAINER_NAME

from . import common, metrics

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
    tags = profile_tags + ["snmp_device:{}".format(instance['ip_address'])]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')
    aggregator.assert_metric(
        'datadog.snmp.submitted_metrics', metric_type=aggregator.GAUGE, tags=tags + ['loader:core'], value=31
    )

    for metric in metrics.APC_UPS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=['outlet_group_name:test_outlet'] + tags,
    )
    for metric, value in metrics.APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS:
        aggregator.assert_metric(metric, value=value, metric_type=aggregator.GAUGE, count=2, tags=tags)

    aggregator.assert_all_metrics_covered()


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
        'snmp_profile:f5-big-ip',
    ]
    tags += ['snmp_device:{}'.format(instance['ip_address'])]

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

    # raw sysName: 41ba948911b9
    aggregator.assert_metric(
        'snmp.devices_monitored',
        tags=[
            'digits:41',
            'remainder:ba948911b9',
            'letter1:4',
            'letter2:1',
            'loader:core',
            'snmp_device:' + instance['ip_address'],
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
        'device_vendor:meraki',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    common.assert_common_metrics(aggregator, tags=common_tags, is_e2e=True, loader='core')

    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = ['product:MR16-HW', 'network:L_NETWORK', 'mac_address:02:02:00:66:f5:7f'] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=2, device='Gymnasium'
        )

    if_tags = ['interface:wifi0', 'index:4', 'mac_address:02:02:00:66:f5:00'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    # IF-MIB
    if_tags = ['interface:eth0'] + common_tags
    for metric in metrics.IF_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=if_tags, count=1)

    for metric in metrics.IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=2)

    for metric in metrics.IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in metrics.IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    custom_speed_tags = if_tags + ['speed_source:device']
    for metric in metrics.IF_CUSTOM_SPEED_GAUGES:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=custom_speed_tags, count=2
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=2, tags=common_tags)
    aggregator.assert_metric(
        'snmp.interface.status',
        metric_type=aggregator.GAUGE,
        tags=if_tags + ['interface_index:11', 'status:warning', 'admin_status:down', 'oper_status:lower_layer_down'],
        value=1,
    )
    aggregator.assert_all_metrics_covered()


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
    ]

    tags = global_metric_tags + ['device_namespace:default', "snmp_device:{}".format(instance['ip_address'])]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')

    for metric in metrics.APC_UPS_METRICS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=['outlet_group_name:test_outlet'] + tags,
    )
    for metric, value in metrics.APC_UPS_UPS_BASIC_STATE_OUTPUT_STATE_METRICS:
        aggregator.assert_metric(metric, value=value, metric_type=aggregator.GAUGE, count=2, tags=tags)

    interface_tags = ['interface:mgmt', 'interface_alias:desc1'] + tags
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
