# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict
from copy import deepcopy

import pytest

from datadog_checks.base.stubs.common import MetricStub, ServiceCheckStub

from . import common

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]

SUPPORTED_METRIC_TYPES = [
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.7.1.0", 'name': "IAmACounter32"}},  # Counter32
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.4.31.1.1.6.1", 'name': "IAmACounter64"}},  # Counter64
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.4.24.6.0", 'name': "IAmAGauge32"}},  # Gauge32
    {'MIB': 'ABC', 'symbol': {'OID': "1.3.6.1.2.1.88.1.1.1.0", 'name': "IAmAnInteger"}},  # Integer
]

ASSERT_VALUE_METRICS = [
    'snmp.devices_monitored',
]

# Profiles may contain symbols declared twice with different names and the same OID
# Python check does handle one single metric name per OID symbol
SKIPPED_CORE_ONLY_METRICS = [
    'snmp.memory.total',
    'snmp.memory.used',
    'snmp.memory.free',
    'snmp.memory.usage',
    'snmp.cpu.usage',
    'snmp.device.reachable',
    'snmp.device.unreachable',
    'snmp.interface.status',
    'snmp.ifInSpeed',
    'snmp.ifOutSpeed',
    'snmp.peerConnectionByState',  # BGP4 constant metric, not handled by python check
    'snmp.ltmVsStatus',  # F5-BIG-IP constant metric
    'snmp.ltmNodeAddr',  # F5-BIG-IP constant metric
    'snmp.ltmPoolMember',  # F5-BIG-IP constant metric
    'snmp.ospfNbr',  # OSPF constant metrics, not handled by python check
    'snmp.ospfVirtNbr',
    'snmp.ospfIf',
    'snmp.ospfVirtIf',
    'snmp.wlsxSysExtFan',  # Aruba constant metric
    'snmp.upsOutletGroupStatus',  # APC UPS constant metric
    'snmp.cpiEas',  # Chatsworth constant metric
    'snmp.ciscoEnvMonSupplyStatus',  # Cisco constant metric
    'snmp.ciscoEnvMonFanStatus',  # Cisco constant metric
    'snmp.cefcFanTrayStatus',  # Cisco constant metric
    'snmp.cefcFRUPowerStatus',  # Cisco constant metric
    'snmp.cswSwitchInfo',  # Cisco constant metric
    'snmp.cswSwitchState',  # Cisco constant metric
    'snmp.cpqHeFltTolPowerSupply',  # HP constant metric
    'snmp.fanSpeedSensor',  # Checkpoint constant metric
    'snmp.meraki.dev',  # Meraki constant metric
    'snmp.enclosurePowerSupply',  # iDRAC constant metric
    'snmp.fgVirtualDomain',  # Fortinet-Fortigate constant metric
    'snmp.systemState',  # Dell-Poweredge constant metric
    'snmp.dell.systemState',  # iDRAC constant metric
    'snmp.dell.physicalDisk',  # iDRAC constant metric
    'snmp.dell.controller',  # Dell constant metric
    'snmp.dell.pCIDevice',  # Dell constant metric
    'snmp.dell.systemSlot',  # Dell constant metric
    'snmp.dell.battery',  # Dell constant metric
    'snmp.dell.networkDevice',  # Dell constant metric
    'snmp.dell.systemBIOS',  # Dell constant metric
    'snmp.dell.amperageProbe',  # Dell constant metric
    'snmp.dell.voltageProbe',  # Dell constant metric
    'snmp.dell.memoryDevice',  # Dell constant metric
]

DEFAULT_TAGS_TO_SKIP = ['loader', 'device_id', 'device_ip']

CORE_ONLY_TAGS = ['device_namespace:default']


def test_e2e_metric_types(dd_agent_check):
    instance = common.generate_container_instance_config(SUPPORTED_METRIC_TYPES)
    assert_python_vs_core(dd_agent_check, instance, expected_total_count=10 + 5)


def test_e2e_v3_version_autodetection(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogSHADES',
            'authKey': 'doggiepass',
            'authProtocol': 'sha',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'des',
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=SKIPPED_CORE_ONLY_METRICS,
    )


def test_e2e_v3_explicit_version(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogSHADES',
            'authKey': 'doggiepass',
            'authProtocol': 'SHA',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'DES',
            'snmp_version': 3,
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=SKIPPED_CORE_ONLY_METRICS,
    )


def test_e2e_v3_md5_aes(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogMD5AES',
            'authKey': 'doggiepass',
            'authProtocol': 'MD5',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'AES',
            'snmp_version': 3,
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
    )


def test_e2e_v3_md5_aes256_blumenthal(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogMD5AES256BLMT',
            'authKey': 'doggiepass',
            'authProtocol': 'MD5',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'AES256',  # `AES256` correspond to Blumenthal implementation for pysnmp and gosnmp
            'snmp_version': 3,
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
    )


def test_e2e_v3_md5_aes256_reeder(dd_agent_check):
    # About Reeder implementation:
    # "Many vendors, including Cisco, use the 3DES key extension algorithm to extend the privacy keys that are
    # too short when using AES,AES192 and AES256."
    # source: https://github.com/gosnmp/gosnmp/blob/f6fb3f74afc3fb0e5b44b3f60751b988bc960019/v3_usm.go#L458-L461
    config = common.generate_container_instance_config([])
    config['instances'][0].update(
        {
            'user': 'datadogMD5AES256',
            'authKey': 'doggiepass',
            'authProtocol': 'MD5',
            'privKey': 'doggiePRIVkey',
            'privProtocol': 'AES256C',  # `AES256C` correspond to Reeder implementation for pysnmp and gosnmp
            'snmp_version': 3,
            'context_name': 'f5-big-ip',
            'community_string': '',
        }
    )
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
    )


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
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_scalar_oid_retry(dd_agent_check):
    scalar_objects_with_tags = [
        {'OID': "1.3.6.1.2.1.7.1", 'name': "udpDatagrams"},
    ]
    instance = common.generate_container_instance_config(scalar_objects_with_tags)
    assert_python_vs_core(dd_agent_check, instance)


def test_e2e_symbol_metric_tags(dd_agent_check):
    scalar_objects_with_tags = [
        {'OID': "1.3.6.1.2.1.7.1.0", 'name': "udpDatagrams", 'metric_tags': ['udpdgrams', 'UDP']},
        {'OID': "1.3.6.1.2.1.6.10.0", 'name': "tcpInSegs", 'metric_tags': ['tcpinsegs', 'TCP']},
    ]
    instance = common.generate_container_instance_config(scalar_objects_with_tags)
    assert_python_vs_core(dd_agent_check, instance)


def test_e2e_inline_profile_def(dd_agent_check):
    config = common.generate_container_instance_config([])
    config['init_config'] = {'profiles': {'profile1': {'definition': {'metrics': common.SUPPORTED_METRIC_TYPES}}}}
    config['instances'][0]['profile'] = 'profile1'
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_custom_metrics_cases(dd_agent_check):
    metrics = [
        # extract value using regex
        {
            "MIB": "DUMMY-MIB",
            'symbol': {
                'OID': "1.3.6.1.4.1.123456789.4.0",
                'name': "aTemperatureValueInferred",
                'extract_value': '(\\d+)C',
            },
        },
        # string float value
        {
            "MIB": "DUMMY-MIB",
            'symbol': {
                'OID': "1.3.6.1.4.1.123456789.5.0",
                'name': "aStringFloatValue",
            },
        },
    ]
    config = common.generate_container_instance_config(metrics)
    instance = config['instances'][0]
    instance["community_string"] = "dummy"
    assert_python_vs_core(
        dd_agent_check, config, assert_value_metrics=ASSERT_VALUE_METRICS + ['snmp.aStringFloatValue']
    )


# Profile tests
# expected_total_count: Test with some expected_total_count to be sure that both python and corecheck impl
# are collecting some metrics.


def test_e2e_profile_apc_ups(dd_agent_check):
    config = common.generate_container_profile_config('apc_ups')
    assert_python_vs_core(
        dd_agent_check, config, expected_total_count=64 + 5, tags_to_skip=["ups_outlet_group_status_group_state"]
    )


def test_e2e_profile_apc_ups_user(dd_agent_check):
    config = common.generate_container_profile_config('apc_ups_user')
    assert_python_vs_core(
        dd_agent_check, config, expected_total_count=66 + 5, tags_to_skip=["ups_outlet_group_status_group_state"]
    )


def test_e2e_profile_arista(dd_agent_check):
    config = common.generate_container_profile_config('arista')
    assert_python_vs_core(dd_agent_check, config, expected_total_count=16 + 5)


def test_e2e_profile_aruba(dd_agent_check):
    config = common.generate_container_profile_config("aruba")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        expected_total_count=67 + 5,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=['neighbor_state', 'if_state'],  # Ignore tags that have a mapping
    )


def test_e2e_profile_chatsworth_pdu(dd_agent_check):
    config = common.generate_container_profile_config('chatsworth_pdu')
    assert_python_vs_core(
        dd_agent_check, config, expected_total_count=256, tags_to_skip=['eas_status', 'lock_status', 'door_status']
    )


def test_e2e_profile_checkpoint(dd_agent_check):
    config = common.generate_container_profile_config("checkpoint")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        expected_total_count=311,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=['fan_speed_sensor_status'],
    )


def test_e2e_profile_checkpoint_firewall(dd_agent_check):
    config = common.generate_container_profile_config(community_string="checkpoint", profile="checkpoint-firewall")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        expected_total_count=311,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=['fan_speed_sensor_status'],
    )


def test_e2e_profile_cisco_3850(dd_agent_check):
    config = common.generate_container_profile_config("cisco-3850")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        expected_total_count=5109,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=[
            'neighbor_state',
            'if_state',
            'cisco_env_mon_supply_state',
            'fan_state',
            'cefc_fan_tray_oper_status',
            'cefc_fan_tray_direction',
            'power_admin_status',
            'power_oper_status',
            'switch_state',
            'mac_addr',
            'temp_state',
            'power_source',
            'connection_type',
        ],  # Ignore tags that have mappings
    )


def test_e2e_profile_cisco_asa(dd_agent_check):
    config = common.generate_container_profile_config("cisco-asa")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=[
            'cisco_env_mon_supply_state',
            'fan_state',
            'cefc_fan_tray_oper_status',
            'cefc_fan_tray_direction',
            'power_admin_status',
            'power_oper_status',
            'switch_state',
            'mac_addr',
            'rtt_state',
            'rtt_type',
            'temp_state',
            'power_source',
            'connection_type',
        ],  # Ignore tags that have mappings
    )


def test_e2e_profile_cisco_asa_5525(dd_agent_check):
    config = common.generate_container_profile_config("cisco-asa-5525")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=[
            'cisco_env_mon_supply_state',
            'fan_state',
            'cefc_fan_tray_oper_status',
            'cefc_fan_tray_direction',
            'power_admin_status',
            'power_oper_status',
            'switch_state',
            'mac_addr',
            'rtt_state',
            'rtt_type',
            'temp_state',
            'power_source',
            'connection_type',
        ],  # Ignore tags that have mappings
    )


def test_e2e_profile_cisco_catalyst(dd_agent_check):
    config = common.generate_container_profile_config('cisco-catalyst')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_csr1000v(dd_agent_check):
    config = common.generate_container_profile_config('cisco-csr1000v')
    assert_python_vs_core(
        dd_agent_check, config, tags_to_skip=['peer_state', 'admin_status']
    )  # Ignore tags that have a mapping


def test_e2e_profile_cisco_nexus(dd_agent_check):
    config = common.generate_container_profile_config("cisco-nexus")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
        tags_to_skip=[
            'cisco_env_mon_supply_state',
            'fan_state',
            'cefc_fan_tray_oper_status',
            'cefc_fan_tray_direction',
            'power_admin_status',
            'power_oper_status',
            'switch_state',
            'mac_addr',
            'temp_state',
            'power_source',
            'connection_type',
            'sensor_type',
        ],  # Ignore tags that have mappings
    )


def test_e2e_profile_cisco_icm(dd_agent_check):
    config = common.generate_container_profile_config('cisco_icm')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_dell_poweredge(dd_agent_check):
    config = common.generate_container_profile_config('dell-poweredge')

    # TODO: Fix python implementation for duplicate declarations
    metric_to_skip = [
        # Following metrics are declared multiple times in profiles.
        # Example: snmp.networkDeviceStatus and snmp.memoryDeviceStatus are declared twice
        # in dell-poweredge.yaml and _dell-rac.yaml
        # This is causing python impl to not behave correctly. Some `snmp.networkDeviceStatus` doesn't include
        # either `ip_address` or `chassis_index/mac_addr/device_fqdd` tags.
        # See II-153
        'snmp.networkDeviceStatus',
        'snmp.memoryDeviceStatus',
        'datadog.snmp.submitted_metrics',  # count won't match because of the reason explained above
    ]
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metric_to_skip,
        tags_to_skip=[
            'disk_state',
            'controller_roll_up_status',
            'device_status',
            'slot_status',
            'battery_state',
            'system_state_chassis_status',
            'system_state_power_unit_status_redundancy',
            'system_state_power_supply_status_combined',
            'system_state_amperage_status_combined',
            'system_state_cooling_unit_status_redundancy',
            'system_state_cooling_device_status_combined',
            'system_state_temperature_status_combined',
            'system_state_memory_device_status_combined',
            'system_state_chassis_intrusion_status_combined',
            'system_state_power_unit_status_combined',
            'system_state_cooling_unit_status_combined',
            'system_state_processor_device_status_combined',
            'system_state_temperature_statistics_status_combined',
            'network_device_status',
            'system_bios_status',
            'amperage_probe_status',
            'voltage_probe_status',
            'memory_device_status',
            'probe_type',
            'cooling_device_type',
            'temperature_probe_type',
        ],  # Skipping tags with mappings
    )


def test_e2e_core_vs_python_profile_f5_big_ip(dd_agent_check):
    config = common.generate_container_profile_config("f5-big-ip")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(
        dd_agent_check,
        config,
        metrics_to_skip=metrics_to_skip,
    )


def test_e2e_profile_fortinet_fortigate(dd_agent_check):
    config = common.generate_container_profile_config("fortinet-fortigate")
    metrics_to_skip = SKIPPED_CORE_ONLY_METRICS
    assert_python_vs_core(dd_agent_check, config, metrics_to_skip=metrics_to_skip, tags_to_skip=['fgVdEntHaState'])


def test_e2e_profile_generic_device(dd_agent_check):
    config = common.generate_container_profile_config('generic-device')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_hp_ilo4(dd_agent_check):
    config = common.generate_container_profile_config('hp-ilo4')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_hpe_proliant(dd_agent_check):
    config = common.generate_container_profile_config('hpe-proliant')
    assert_python_vs_core(
        dd_agent_check,
        config,
        tags_to_skip=['power_supply_status'],  # Skipping tag with a mapping
    )


def test_e2e_profile_idrac(dd_agent_check):
    config = common.generate_container_profile_config('idrac')
    assert_python_vs_core(
        dd_agent_check,
        config,
        tags_to_skip=[
            'enclosure_power_supply_state',
            'disk_state',
            'controller_roll_up_status',
            'device_status',
            'slot_status',
            'battery_state',
            'system_state_chassis_status',
            'system_state_power_unit_status_redundancy',
            'system_state_power_supply_status_combined',
            'system_state_amperage_status_combined',
            'system_state_cooling_unit_status_redundancy',
            'system_state_cooling_device_status_combined',
            'system_state_temperature_status_combined',
            'system_state_memory_device_status_combined',
            'system_state_chassis_intrusion_status_combined',
            'system_state_power_unit_status_combined',
            'system_state_cooling_unit_status_combined',
            'system_state_processor_device_status_combined',
            'system_state_temperature_statistics_status_combined',
            'network_device_status',
            'system_bios_status',
            'amperage_probe_status',
            'voltage_probe_status',
            'memory_device_status',
            'probe_type',
            'cooling_device_type',
            'temperature_probe_type',
        ],  # Skipping tags with mappings
    )


def test_e2e_profile_isilon(dd_agent_check):
    config = common.generate_container_profile_config('isilon')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_meraki_cloud_controller(dd_agent_check):
    config = common.generate_container_profile_config('meraki-cloud-controller')
    assert_python_vs_core(dd_agent_check, config, tags_to_skip=['mac_address', 'status'])


def test_e2e_profile_netapp(dd_agent_check):
    config = common.generate_container_profile_config('netapp')
    assert_python_vs_core(dd_agent_check, config)


def test_e2e_profile_cisco_asr_1001x(dd_agent_check):
    config = common.generate_container_profile_config('cisco-asr-1001x')
    assert_python_vs_core(dd_agent_check, config, tags_to_skip=['cisco_env_mon_supply_state'])


def test_e2e_profile_cisco_asr_9001(dd_agent_check):
    config = common.generate_container_profile_config('cisco-asr-9001')
    assert_python_vs_core(dd_agent_check, config, tags_to_skip=['cisco_env_mon_supply_state'])


def test_e2e_profile_cisco_asr_9901(dd_agent_check):
    config = common.generate_container_profile_config('cisco-asr-9901')
    assert_python_vs_core(dd_agent_check, config, tags_to_skip=['cisco_env_mon_supply_state'])


def test_e2e_discovery(dd_agent_check):
    config = common.generate_container_profile_config_with_ad('apc_ups')
    # skip telemetry metrics since they are implemented different for python and corecheck
    # python integration autodiscovery submit telemetry metrics once for all devices
    # core integration autodiscovery submit telemetry metrics once for each device
    skip_metrics = [
        'datadog.snmp.check_interval',
        'datadog.snmp.submitted_metrics',
        'datadog.snmp.check_duration',
    ]
    # we don't assert count, since the count might be off by 1 due to devices not being discovered at first check run
    assert_python_vs_core(
        dd_agent_check,
        config,
        rate=False,
        pause=300,
        times=3,
        metrics_to_skip=skip_metrics,
        assert_count=False,
        tags_to_skip=['ups_outlet_group_status_group_state'],  # Skipping tag with a mapping
    )


def assert_python_vs_core(
    dd_agent_check,
    config,
    expected_total_count=None,
    metrics_to_skip=None,
    tags_to_skip=None,
    assert_count=True,
    assert_value_metrics=ASSERT_VALUE_METRICS,
    rate=True,
    pause=0,
    times=1,
):
    python_config = deepcopy(config)
    python_config['init_config']['loader'] = 'python'
    core_config = deepcopy(config)
    core_config['init_config']['loader'] = 'core'
    core_config['init_config']['collect_device_metadata'] = 'false'
    metrics_to_skip = (metrics_to_skip or []) + SKIPPED_CORE_ONLY_METRICS
    tags_to_skip = tags_to_skip or []
    tags_to_skip += DEFAULT_TAGS_TO_SKIP

    # building expected metrics (python)
    aggregator = dd_agent_check(python_config, rate=rate, pause=pause, times=times)
    python_metrics = defaultdict(list)
    for _, metrics in aggregator._metrics.items():
        for stub in metrics:
            if stub.name in metrics_to_skip:
                continue
            stub = normalize_stub_metric(stub, tags_to_skip)
            python_metrics[(stub.name, stub.type, tuple(sorted(list(stub.tags) + CORE_ONLY_TAGS)))].append(stub)

    python_service_checks = defaultdict(list)
    for _, service_checks in aggregator._service_checks.items():
        for stub in service_checks:
            python_service_checks[
                (stub.name, stub.status, tuple(sorted(list(stub.tags) + CORE_ONLY_TAGS)), stub.message)
            ].append(stub)

    total_count_python = sum(len(stubs) for stubs in python_metrics.values())

    # building core metrics (core)
    aggregator.reset()
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, core_config, rate=rate, pause=pause, times=times)
    aggregator_metrics = aggregator._metrics
    aggregator._metrics = defaultdict(list)
    for metric_name in aggregator_metrics:
        for stub in aggregator_metrics[metric_name]:
            if stub.name in metrics_to_skip:
                continue
            aggregator._metrics[metric_name].append(normalize_stub_metric(stub, tags_to_skip))

    core_metrics = defaultdict(list)
    for _, metrics in aggregator._metrics.items():
        for metric in metrics:
            core_metrics[(metric.name, metric.type, tuple(sorted(metric.tags)))].append(metric)

    print("Python metrics not found in Corecheck metrics:")
    for key in sorted(python_metrics):
        if key not in core_metrics:
            print("\t{}".format(key))

    print("Corecheck metrics not found in Python metrics:")
    for key in sorted(core_metrics):
        if key not in python_metrics:
            print("\t{}".format(key))

    for (name, mtype, tags), stubs in python_metrics.items():
        count = len(stubs) if assert_count else None
        if name in assert_value_metrics:
            for stub in stubs:
                aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=count, value=stub.value)
        else:
            aggregator.assert_metric(name, metric_type=mtype, tags=tags, count=count)

    aggregator.assert_all_metrics_covered()

    # Removed skipped tags from core aggregator
    aggregator_servicechecks = aggregator._service_checks
    aggregator._service_checks = defaultdict(list)
    for servicecheck_name in aggregator_servicechecks:
        for stub in aggregator_servicechecks[servicecheck_name]:
            if stub.name in metrics_to_skip:
                continue
            aggregator._service_checks[servicecheck_name].append(normalize_stub_servicecheck(stub, tags_to_skip))

    for (name, status, tags, message), stubs in python_service_checks.items():
        count = len(stubs) if assert_count else None
        aggregator.assert_service_check(name, status, tags, count=count, message=message)

    # assert count
    if assert_count:
        total_count_corecheck = sum(len(metrics) for key, metrics in aggregator._metrics.items())
        assert total_count_python == total_count_corecheck
        if expected_total_count is not None:
            assert expected_total_count == total_count_corecheck


def normalize_stub_metric(stub, tags_to_skip):
    tags = [t for t in stub.tags if not is_skipped_tag(t, tags_to_skip)]  # Remove skipped tag
    return MetricStub(
        stub.name,
        stub.type,
        stub.value,
        tags,
        stub.hostname,
        stub.device,
    )


def normalize_stub_servicecheck(stub, tags_to_skip):
    tags = [t for t in stub.tags if not is_skipped_tag(t, tags_to_skip)]  # Remove skipped tag
    return ServiceCheckStub(
        stub.check_id,
        stub.name,
        stub.status,
        tags,
        stub.hostname,
        stub.message,
    )


def is_skipped_tag(tag, tags_to_skip):
    for skipped_tag in tags_to_skip:
        if tag.startswith('{}:'.format(skipped_tag)):
            return True
    return False
