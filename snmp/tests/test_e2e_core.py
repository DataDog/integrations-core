# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from tests.common import SNMP_CONTAINER_NAME

from datadog_checks.dev.docker import get_container_ip

from . import common

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
    aggregator = dd_agent_check(config, rate=True)

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

    metrics = [
        'upsAdvBatteryNumOfBadBattPacks',
        'upsAdvBatteryReplaceIndicator',
        'upsAdvBatteryRunTimeRemaining',
        'upsAdvBatteryTemperature',
        'upsAdvBatteryCapacity',
        'upsHighPrecInputFrequency',
        'upsHighPrecInputLineVoltage',
        'upsHighPrecOutputCurrent',
        'upsAdvInputLineFailCause',
        'upsAdvOutputLoad',
        'upsBasicBatteryTimeOnBattery',
        'upsAdvTestDiagnosticsResults',
    ]

    common.assert_common_metrics(aggregator, tags, is_e2e=True, loader='core')

    for metric in metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=['outlet_group_name:test_outlet'] + tags,
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.AVRTrimActive', 1, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.BatteriesDischarged', 1, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.LowBatteryOnBattery', 1, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.NoBatteriesAttached', 1, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.OnLine', 0, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric(
        'snmp.upsBasicStateOutputState.ReplaceBattery', 1, metric_type=aggregator.GAUGE, tags=tags, count=2
    )
    aggregator.assert_metric('snmp.upsBasicStateOutputState.On', 1, metric_type=aggregator.GAUGE, tags=tags, count=2)

    aggregator.assert_all_metrics_covered()


def test_e2e_core_discovery(dd_agent_check):
    config = common.generate_container_profile_config_with_ad('apc_ups')
    config['init_config']['loader'] = 'core'
    aggregator = dd_agent_check(config, rate=False, times=5)

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
        'snmp.devices_monitored', metric_type=aggregator.GAUGE, tags=tags_with_loader, at_least=4, value=1
    )
    aggregator.assert_metric('snmp.upsAdvBatteryTemperature', metric_type=aggregator.GAUGE, tags=tags, at_least=4)


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
    aggregator = dd_agent_check(config, rate=True)
    config['init_config']['loader'] = 'core'
    aggregator = dd_agent_check(config, rate=True)

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
