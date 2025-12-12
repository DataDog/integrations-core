# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import pprint

import pytest

from . import common

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def get_events(aggregator):
    events = aggregator.get_event_platform_events("network-devices-metadata", parse_json=True)
    for event in events:
        # `collect_timestamp` depend on check run time and cannot be asserted reliably,
        # we are replacing it with `0` if present
        if 'collect_timestamp' in event:
            event['collect_timestamp'] = 0
        for device in event.get('devices', []):
            device['tags'] = common.remove_tags(device['tags'], common.EXCLUDED_E2E_TAG_KEYS)
    return events


def assert_metadata_events(aggregator, events):
    actual_events = get_events(aggregator)
    assert events == actual_events, "ACTUAL EVENTS: " + json.dumps(actual_events, indent=4)


def assert_device_metadata(aggregator, expected_device):
    events = get_events(aggregator)

    assert len(events) >= 1
    event1 = events[0]

    pprint.pprint(event1['devices'])
    assert len(event1['devices']) == 1

    actual_device = event1['devices'][0]
    for device in [actual_device, expected_device]:
        device.get('tags', []).sort()

    assert actual_device == expected_device


def test_e2e_core_metadata_f5(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'f5-big-ip',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    events = [
        {
            'collect_timestamp': 0,
            'integration': 'snmp',
            'devices': [
                {
                    'description': 'BIG-IP Virtual Edition : Linux '
                    '3.10.0-862.14.4.el7.ve.x86_64 : BIG-IP software '
                    'release 15.0.1, build 0.0.11',
                    'id': device_id,
                    'id_tags': [
                        'device_namespace:default',
                        'snmp_device:' + device_ip,
                    ],
                    'ip_address': device_ip,
                    'location': 'Network Closet 1',
                    'name': 'f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                    'profile': 'f5-big-ip',
                    'status': 1,
                    'sys_object_id': '1.3.6.1.4.1.3375.2.1.3.4.43',
                    'tags': [
                        'agent_host:' + common.get_agent_hostname(),
                        'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                        'device_id:' + device_id,
                        'device_ip:' + device_ip,
                        'device_namespace:default',
                        'device_vendor:f5',
                        'snmp_device:' + device_ip,
                        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                        'snmp_profile:f5-big-ip',
                    ],
                    'vendor': 'f5',
                    'serial_number': '26ff4a4d-190e-12ac-d4257ed36ba6',
                    'version': '15.0.1',
                    'product_name': 'BIG-IP',
                    'model': 'Z100',
                    'os_name': 'Linux',
                    'os_version': '3.10.0-862.14.4.el7.ve.x86_64',
                    'device_type': 'load_balancer',
                    'integration': 'snmp',
                },
            ],
            'diagnoses': [
                {
                    'diagnoses': None,
                    'resource_id': device_id,
                    'resource_type': 'device',
                },
            ],
            'interfaces': [
                {
                    'admin_status': 1,
                    'alias': 'desc5',
                    'description': '/Common/internal',
                    'device_id': device_id,
                    'id_tags': ['interface:/Common/internal'],
                    'index': 112,
                    'mac_address': '42:01:0a:a4:00:33',
                    'name': '/Common/internal',
                    'oper_status': 1,
                },
                {
                    'admin_status': 1,
                    'alias': 'desc1',
                    'description': 'mgmt',
                    'device_id': device_id,
                    'id_tags': ['interface:mgmt'],
                    'index': 32,
                    'mac_address': '42:01:0a:a4:00:33',
                    'name': 'mgmt',
                    'oper_status': 1,
                },
                {
                    'admin_status': 1,
                    'alias': 'desc2',
                    'description': '1.0',
                    'device_id': device_id,
                    'id_tags': ['interface:1.0'],
                    'index': 48,
                    'mac_address': '42:01:0a:a4:00:33',
                    'name': '1.0',
                    'oper_status': 1,
                },
                {
                    'admin_status': 1,
                    'alias': 'desc3',
                    'description': '/Common/http-tunnel',
                    'device_id': device_id,
                    'id_tags': ['interface:/Common/http-tunnel'],
                    'index': 80,
                    'mac_address': '42:01:0a:a4:00:34',
                    'name': '/Common/http-tunnel',
                    'oper_status': 4,
                },
                {
                    'admin_status': 1,
                    'alias': 'desc4',
                    'description': '/Common/socks-tunnel',
                    'device_id': device_id,
                    'id_tags': ['interface:/Common/socks-tunnel'],
                    'index': 96,
                    'mac_address': '42:01:0a:a4:00:34',
                    'name': '/Common/socks-tunnel',
                    'oper_status': 4,
                },
            ],
            "ip_addresses": [
                {"interface_id": "default:{}:32".format(device_ip), "ip_address": "10.164.0.51", "prefixlen": 32}
            ],
            'namespace': 'default',
        },
    ]
    assert_metadata_events(aggregator, events)


def test_e2e_core_metadata_cisco_3850(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-3850',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']

    events = get_events(aggregator)

    # since there are >100 resources (device+interfaces+links), the metadata is split into 3 events
    assert len(events) == 3
    event1 = events[0]

    # assert device (there is only one device)
    pprint.pprint(event1['devices'])
    assert len(event1['devices']) == 1
    actual_device = event1['devices'][0]

    device_id = 'default:' + device_ip

    device = {
        'description': 'Cisco IOS Software, IOS-XE Software, Catalyst L3 Switch '
        'Software (CAT3K_CAA-UNIVERSALK9-M), Version 03.06.06E RELEASE '
        'SOFTWARE (fc1) Technical Support: '
        'http://www.cisco.com/techsupport Copyright (c) 1986-2016 by '
        'Cisco Systems, Inc. Compiled Sat 17-Dec-',
        'id': device_id,
        'id_tags': ['device_namespace:default', 'snmp_device:' + device_ip],
        'ip_address': device_ip,
        'location': '4th floor',
        'name': 'Cat-3850-4th-Floor.companyname.local',
        'os_name': 'IOS',
        'profile': 'cisco-3850',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1745',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_hostname:Cat-3850-4th-Floor.companyname.local',
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_host:Cat-3850-4th-Floor.companyname.local',
            'snmp_profile:cisco-3850',
        ],
        'vendor': 'cisco',
        'version': '03.06.06E',
        'serial_number': 'FOCXXXXXXXX',
        'model': 'CAT3K_CAA-UNIVERSALK9-M',
        'device_type': 'switch',
        'integration': 'snmp',
    }
    assert device == actual_device

    # assert one interface
    pprint.pprint(event1['interfaces'])
    assert len(event1['interfaces']) > 1
    actual_interface = event1['interfaces'][0]
    interface = {
        'admin_status': 1,
        'description': 'GigabitEthernet0/0',
        'device_id': 'default:' + device_ip,
        'id_tags': ['interface:Gi0/0'],
        'index': 1,
        'mac_address': '00:00:00:00:00:00',
        'name': 'Gi0/0',
        'oper_status': 2,
    }
    assert interface == actual_interface


def test_e2e_core_metadata_cisco_catalyst(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-catalyst',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'name': 'catalyst-6000.example',
        'profile': 'cisco-catalyst',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.241',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_host:catalyst-6000.example',
            'device_hostname:catalyst-6000.example',
            'snmp_profile:cisco-catalyst',
        ],
        'vendor': 'cisco',
        'serial_number': 'SCA044001J9',
        'device_type': 'switch',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_hp_ilo4(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'hp-ilo4',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'iLO4',
        'os_name': 'RHEL',
        'os_version': '3.10.0-862.14.4.el7.ve.x86_64',
        'product_name': 'Integrated Lights-Out',
        'name': 'hp-ilo4.example',
        'profile': 'hp-ilo4',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.232.9.4.10',
        'version': 'A04-08/12/2018',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:hp',
            'snmp_device:' + device_ip,
            'snmp_host:hp-ilo4.example',
            'device_hostname:hp-ilo4.example',
            'snmp_profile:hp-ilo4',
        ],
        'vendor': 'hp',
        'serial_number': 'dXPEdPBE5yKtjW9xx3',
        'device_type': 'server',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_hpe_proliant(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'hpe-proliant',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'name': 'hpe-proliant.example',
        'profile': 'hpe-proliant',
        'status': 1,
        'model': 'BL35p G1',
        'os_name': 'RHEL',
        'os_version': '3.10.0-862.15.4.el7.ve.x86_64',
        'product_name': 'ProLiant',
        'version': 'A04-08/12/2019',
        'sys_object_id': '1.3.6.1.4.1.232.1.2',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:hp',
            'snmp_device:' + device_ip,
            'snmp_host:hpe-proliant.example',
            'device_hostname:hpe-proliant.example',
            'snmp_profile:hpe-proliant',
        ],
        'vendor': 'hp',
        'serial_number': 'dLPEdPBE5yKtjW9xx3',
        'device_type': 'other',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_apc_ups(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'apc_ups',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'APC Web/SNMP Management Card (MB:v3.9.2 PF:v3.9.2 '
        'PN:apc_hw02_aos_392.bin AF1:v3.7.2 AN1:apc_hw02_sumx_372.bin '
        'MN:AP9619 HR:A10 SN: 5A1827E00000 MD:12/04/2007) (Embedded '
        'PowerNet SNMP Agent SW v2.2 compatible)',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'AP9619',
        'os_name': 'AOS',
        'os_version': 'v3.9.2',
        'product_name': 'APC Smart-UPS 600',
        'profile': 'apc_ups',
        'serial_number': '5A1827E00000',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.318.1.1.1',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:apc',
            'firmware_version:2.0.3-test',
            'model:APC Smart-UPS 600',
            'serial_num:test_serial',
            'snmp_device:' + device_ip,
            'snmp_profile:apc_ups',
            'ups_name:testIdentName',
        ],
        'vendor': 'apc',
        'version': '2.0.3-test',
        'device_type': 'ups',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_juniper_ex(dd_agent_check):
    """Test Juniper EX metadata collection"""
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'juniper-ex',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    expected_device = {
        'description': 'Juniper Networks, Inc. ex2200-24t-4g internet router, kernel '
        + 'JUNOS 10.2R1.8 #0: 2010-05-27 20:13:49 UTC',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'ex2200-24t-4g',
        'os_name': 'JUNOS',
        'os_version': '10.2R1.8',
        'product_name': 'EX2200 Ethernet Switch',
        'profile': 'juniper-ex',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2636.1.1.1.2.30',
        'serial_number': 'dXPEdPBE5yKtjW9xx3',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:juniper-networks',
            'snmp_device:' + device_ip,
            'snmp_profile:juniper-ex',
        ],
        'vendor': 'juniper-networks',
        'version': 'version-1.0',
        'device_type': 'switch',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, expected_device)


def test_e2e_core_metadata_juniper_mx(dd_agent_check):
    """Test Juniper MX metadata collection"""
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'juniper-mx',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    expected_device = {
        'description': 'Juniper Networks, Inc. mx480 internet router, kernel JUNOS 11.2R1.10 '
        + '#0: 2011-07-29 07:15:34 UTC',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'mx480',
        'os_name': 'JUNOS',
        'os_version': '11.2R1.10',
        'product_name': 'MX480 Router',
        'profile': 'juniper-mx',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2636.1.1.1.2.25',
        'serial_number': 'dXPEdPBE5yKtjW9xx4',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:juniper-networks',
            'snmp_device:' + device_ip,
            'snmp_profile:juniper-mx',
        ],
        'vendor': 'juniper-networks',
        'version': 'version-1.1',
        'device_type': 'router',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, expected_device)


def test_e2e_core_metadata_juniper_srx(dd_agent_check):
    """Test Juniper SRX metadata collection"""
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'juniper-srx',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    expected_device = {
        'description': 'Juniper Networks, Inc. srx3400 internet router, kernel JUNOS '
        + '10.4R3.4 #0: 2011-03-19 22:06:23 UTC',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'srx3400',
        'os_name': 'JUNOS',
        'os_version': '10.4R3.4',
        'product_name': 'SRX 3400 Router',
        'profile': 'juniper-srx',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2636.1.1.1.2.35',
        'serial_number': 'dXPEdPBE5yKtjW9xx5',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:juniper-networks',
            'snmp_device:' + device_ip,
            'snmp_profile:juniper-srx',
        ],
        'vendor': 'juniper-networks',
        'version': 'version-1.2',
        'device_type': 'firewall',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, expected_device)


def test_e2e_core_metadata_aruba_switch(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'aruba-switch',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'ArubaOS (MODEL: Aruba7210), Version 8.6.0.4 (74969)',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'A7210',
        'name': 'aruba-switch.device.name',
        'os_name': 'ArubaOS',
        'os_version': '8.6.0.4',
        'product_name': 'Aruba7210',
        'profile': 'aruba-switch',
        'serial_number': 'CV0009200',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14823.1.1.36',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:aruba',
            'snmp_device:' + device_ip,
            'snmp_host:aruba-switch.device.name',
            'device_hostname:aruba-switch.device.name',
            'snmp_profile:aruba-switch',
        ],
        'vendor': 'aruba',
        'version': '8.6.0.4',
        'device_type': 'switch',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_aruba_access_point(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'aruba-access-point',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'ArubaOS (MODEL: 335), Version 6.5.4.3-6.5.4.3',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': '335',
        'os_name': 'ArubaOS',
        'os_version': '6.5.4.3',
        'name': 'aruba-335-name',
        'profile': 'aruba-access-point',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14823.1.2.80',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:aruba',
            'snmp_device:' + device_ip,
            'snmp_host:aruba-335-name',
            'device_hostname:aruba-335-name',
            'snmp_profile:aruba-access-point',
        ],
        'vendor': 'aruba',
        'version': '6.5.4.3-6.5.4.3',
        'device_type': 'access_point',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_arista(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'arista',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Arista Networks EOS version 4.20.11.1M running on an Arista Networks DCS-7504',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'DCS-7504',
        'name': 'DCS-7504-name',
        'os_name': 'EOS',
        'os_version': '4.20.11.1M',
        'product_name': 'DCS-7504 Chassis',
        'profile': 'arista',
        'serial_number': 'HSH16195058',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.30065.1.3011.7504',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:arista',
            'snmp_device:' + device_ip,
            'snmp_host:DCS-7504-name',
            'device_hostname:DCS-7504-name',
            'snmp_profile:arista',
        ],
        'vendor': 'arista',
        'version': '12.00',
        'device_type': 'other',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_palo_alto(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'palo-alto',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Palo Alto Networks PA-3000 series firewall',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
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
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'snmp_device:' + device_ip,
            'snmp_profile:palo-alto',
        ],
        'vendor': 'paloaltonetworks',
        'version': '9.0.5',
        'device_type': 'other',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_netapp(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'netapp',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'NetApp Release 9.3P7: Wed Jul 25 10:11:10 UTC 2018',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'location': 'France',
        'model': 'example-model',
        'name': 'example-datacenter.company',
        'os_name': 'ONTAP',
        'os_version': '9.3',
        'profile': 'netapp',
        'serial_number': '1-23-456789',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.789.2.5',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:netapp',
            'snmp_device:' + device_ip,
            'snmp_host:example-datacenter.company',
            'device_hostname:example-datacenter.company',
            'snmp_profile:netapp',
        ],
        'vendor': 'netapp',
        'version': '9.3P7:',
        'device_type': 'storage',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_checkpoint(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'checkpoint',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Linux host1 3.10.0-957.21.3cpx86_64 #1 SMP Tue Jan 28 17:26:12 IST 2020 x86_64',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'Check Point 3200',
        'name': 'checkpoint.device.name',
        'os_name': 'Gaia',
        'os_version': '3.10.0',
        'product_name': 'SVN Foundation',
        'profile': 'checkpoint',
        'serial_number': '1711BA4008',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2620.1.1',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:checkpoint',
            'snmp_device:' + device_ip,
            'snmp_host:checkpoint.device.name',
            'device_hostname:checkpoint.device.name',
            'snmp_profile:checkpoint',
        ],
        'vendor': 'checkpoint',
        'version': 'R80.10',
        'device_type': 'firewall',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_checkpoint_firewall(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'checkpoint',
            'loader': 'core',
            'profile': 'checkpoint-firewall',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Linux host1 3.10.0-957.21.3cpx86_64 #1 SMP Tue Jan 28 17:26:12 IST 2020 x86_64',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'Check Point 3200',
        'name': 'checkpoint.device.name',
        'os_name': 'Gaia',
        'os_version': '3.10.0',
        'product_name': 'SVN Foundation',
        'profile': 'checkpoint-firewall',
        'serial_number': '1711BA4008',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2620.1.1',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:checkpoint',
            'snmp_device:' + device_ip,
            'snmp_host:checkpoint.device.name',
            'device_hostname:checkpoint.device.name',
            'snmp_profile:checkpoint-firewall',
        ],
        'vendor': 'checkpoint',
        'version': 'R80.10',
        'device_type': 'firewall',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_fortinet_fortigate(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'fortinet-fortigate',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'FGT_501E',
        'name': 'fortinet-fortigate.device.name',
        'os_name': 'FortiOS',
        'os_version': '5.6.4',
        'product_name': 'FortiGate-501E',
        'profile': 'fortinet-fortigate',
        'serial_number': 'FG5H1E5110000000',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12356.101.1.1',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:fortinet',
            'snmp_device:' + device_ip,
            'snmp_host:fortinet-fortigate.device.name',
            'device_hostname:fortinet-fortigate.device.name',
            'snmp_profile:fortinet-fortigate',
        ],
        'vendor': 'fortinet',
        'version': 'v5.6.4,build1575b1575,180425 (GA)',
        'device_type': 'other',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_dell_idrac(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'idrac',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'profile': 'idrac',
        'status': 1,
        'model': 'customFooVersion',
        'os_name': 'Ubuntu',
        'os_version': '18.04.3 LTS (Bionic Beaver)',
        'product_name': 'PowerEdge',
        'version': '2.5.4',
        'sys_object_id': '1.3.6.1.4.1.674.10892.2',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:dell',
            'snmp_device:' + device_ip,
            'snmp_profile:idrac',
        ],
        'vendor': 'dell',
        'serial_number': 'acted quaintly driving',
        'device_type': 'server',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_isilon(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'isilon',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'device-name-3 263829375 Isilon OneFS v8.2.0.0',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'X410-4U-Dual-64GB-2x1GE-2x10GE SFP+-34TB-800GB SSD',
        'os_name': 'OneFS',
        'os_version': '8.2.0.0',
        'product_name': 'Isilon OneFS',
        'profile': 'isilon',
        'serial_number': 'SX410-251604-0122',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12325.1.1.2.1.1',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'cluster_name:testcluster1',
            'device_namespace:default',
            'device_vendor:dell',
            'node_name:node1',
            'node_type:1',
            'snmp_device:' + device_ip,
            'snmp_profile:isilon',
        ],
        'vendor': 'dell',
        'version': '8.2.0.0',
        'device_type': 'storage',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_aos_lldp(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'aos-lldp',
            'loader': 'core',
            'collect_topology': True,
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    # CHANGE
    topology_link1 = {
        'id': device_id + ':1.216',
        'integration': 'snmp',
        'source_type': 'lldp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':1', 'id': 'e1'},
        },
        "remote": {
            "device": {"id": "00:80:9f:85:78:8e", "id_type": "mac_address"},
            "interface": {"id": "00:80:9f:85:78:8e", "id_type": "mac_address"},
        },
    }
    topology_link2 = {
        'id': device_id + ':11.217',
        'integration': 'snmp',
        'source_type': 'lldp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':11', 'id': 'e11'},
        },
        "remote": {
            "device": {"id": "00:80:9f:86:0d:d8", "id_type": "mac_address"},
            "interface": {"id": "00:80:9f:86:0d:d8", "id_type": "mac_address"},
        },
    }
    events = get_events(aggregator)

    print("TOPOLOGY LINKS: " + json.dumps(events[0]['links'], indent=4))

    assert events[0]['links'][0] == topology_link1
    assert events[0]['links'][1] == topology_link2
    assert len(events[0]['links']) == 13


def test_e2e_core_metadata_cisco_asr_1001x(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-asr-1001x',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Cisco IOS Software [Bengaluru], ASR1000 Software '
        '(X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 17.6.4, RELEASE '
        'SOFTWARE (fc1)',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'X86_64_LINUX_IOSD-UNIVERSALK9-M',
        'os_name': 'IOS',
        'profile': 'cisco-asr',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1861',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_profile:cisco-asr',
        ],
        'vendor': 'cisco',
        'version': '17.6.4',
        'device_type': 'router',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_cisco_asr_9001(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-asr-9001',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Cisco IOS XR Software (Cisco ASR9K Series),  Version 6.4.2[Default]',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'Cisco ASR9K Series',
        'os_name': 'IOSXR',
        'profile': 'cisco-asr',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1639',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_profile:cisco-asr',
        ],
        'vendor': 'cisco',
        'version': '6.4.2',
        'device_type': 'router',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_cisco_asr_9901(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-asr-9901',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Cisco IOS XR Software (ASR9K), Version 7.1.3  Copyright (c) 2013-2020 by Cisco Systems, Inc.',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'model': 'ASR9K',
        'os_name': 'IOSXR',
        'profile': 'cisco-asr',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.2658',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_profile:cisco-asr',
        ],
        'vendor': 'cisco',
        'version': '7.1.3',
        'device_type': 'router',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)


def test_e2e_core_metadata_cisco_cdp(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-cdp',
            'loader': 'core',
            'collect_topology': True,
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    topology_link1 = {
        'id': device_id + ':1.5',
        'integration': 'snmp',
        'source_type': 'cdp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':1', 'id': ''},
        },
        "remote": {
            "device": {
                "id": "K10-ITV.tine.no",
                "ip_address": "10.10.0.134",
                "description": 'Cisco IOS Software, C2960C Software (C2960c405-UNIVERSALK9-M), Version 15.0(2)SE8, '
                'RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\r',
            },
            "interface": {"id": "GE0/1", "id_type": "interface_name"},
        },
    }
    topology_link2 = {
        'id': device_id + ':2.3',
        'integration': 'snmp',
        'source_type': 'cdp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':2', "id": ''},
        },
        "remote": {
            "device": {
                "id": "K06-ITV.tine.no",
                "ip_address": "10.10.0.132",
                "description": 'Cisco IOS Software, C2960C Software (C2960c405-UNIVERSALK9-M), Version 15.0(2)SE8, '
                'RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\r',
            },
            "interface": {"id": "GE0/2", "id_type": "interface_name"},
        },
    }
    events = get_events(aggregator)

    print("TOPOLOGY LINKS: " + json.dumps(events[0]['links'], indent=4))

    assert events[0]['links'][0] == topology_link1
    assert events[0]['links'][2] == topology_link2
    assert len(events[0]['links']) == 10


#  test that we're only using lldp even when we have both cdp and lldp
def test_e2e_core_metadata_cisco_cdp_lldp(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-cdp-lldp',
            'loader': 'core',
            'collect_topology': True,
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    topology_link = {
        'id': device_id + ':7.1',
        'integration': 'snmp',
        'source_type': 'lldp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':7', 'id': 'te1/0/7'},
        },
        "remote": {
            "device": {
                "id": "82:8a:8c:2f:f8:36",
                "id_type": "mac_address",
                "ip_address": "10.25.0.19",
                "name": "K05-ITV",
            },
            "interface": {"id": "gi9", "id_type": "interface_name"},
        },
    }
    events = get_events(aggregator)

    print("TOPOLOGY LINKS: " + json.dumps(events[0]['links'], indent=4))

    assert events[0]['links'][0] == topology_link
    assert len(events[0]['links']) == 1


def test_e2e_core_metadata_cisco_wlc(dd_agent_check):
    config = common.generate_container_instance_config([])
    instance = config['instances'][0]
    instance.update(
        {
            'community_string': 'cisco-5500-wlc',
            'loader': 'core',
        }
    )

    aggregator = dd_agent_check(config, rate=False)

    device_ip = instance['ip_address']
    device_id = 'default:' + device_ip

    device = {
        'description': 'Cisco Controller',
        'id': device_id,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + device_ip,
        ],
        'ip_address': device_ip,
        'location': 'Datadog Paris',
        'name': 'DDOGWLC',
        'profile': 'cisco-legacy-wlc',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1069',
        'tags': [
            'agent_host:' + common.get_agent_hostname(),
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'device_vendor:cisco',
            'snmp_device:' + device_ip,
            'snmp_host:DDOGWLC',
            'device_hostname:DDOGWLC',
            'snmp_profile:cisco-legacy-wlc',
        ],
        'vendor': 'cisco',
        'device_type': 'wlc',
        'integration': 'snmp',
    }
    assert_device_metadata(aggregator, device)
