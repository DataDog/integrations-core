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
    device_id = u'default:' + device_ip

    events = [
        {
            u'collect_timestamp': 0,
            u'devices': [
                {
                    u'description': u'BIG-IP Virtual Edition : Linux '
                    u'3.10.0-862.14.4.el7.ve.x86_64 : BIG-IP software '
                    u'release 15.0.1, build 0.0.11',
                    u'id': device_id,
                    u'id_tags': [
                        u'device_namespace:default',
                        u'snmp_device:' + device_ip,
                    ],
                    u'ip_address': device_ip,
                    u'location': u'Network Closet 1',
                    u'name': u'f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                    u'profile': u'f5-big-ip',
                    u'status': 1,
                    u'sys_object_id': u'1.3.6.1.4.1.3375.2.1.3.4.43',
                    u'tags': [
                        u'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                        u'device_id:' + device_id,
                        u'device_ip:' + device_ip,
                        u'device_namespace:default',
                        u'device_vendor:f5',
                        u'snmp_device:' + device_ip,
                        u'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                        u'snmp_profile:f5-big-ip',
                    ],
                    u'vendor': u'f5',
                    u'serial_number': '26ff4a4d-190e-12ac-d4257ed36ba6',
                    u'version': u'15.0.1',
                    u'product_name': u'BIG-IP',
                    u'model': u'Z100',
                    u'os_name': u'Linux',
                    u'os_version': u'3.10.0-862.14.4.el7.ve.x86_64',
                    u'device_type': u'load_balancer',
                },
            ],
            u'diagnoses': [
                {
                    u'diagnoses': None,
                    u'resource_id': device_id,
                    u'resource_type': u'device',
                },
            ],
            u'interfaces': [
                {
                    u'admin_status': 1,
                    u'alias': u'desc5',
                    u'description': u'/Common/internal',
                    u'device_id': device_id,
                    u'id_tags': [u'interface:/Common/internal'],
                    u'index': 112,
                    u'mac_address': u'42:01:0a:a4:00:33',
                    u'name': u'/Common/internal',
                    u'oper_status': 1,
                },
                {
                    u'admin_status': 1,
                    u'alias': u'desc1',
                    u'description': u'mgmt',
                    u'device_id': device_id,
                    u'id_tags': [u'interface:mgmt'],
                    u'index': 32,
                    u'mac_address': u'42:01:0a:a4:00:33',
                    u'name': u'mgmt',
                    u'oper_status': 1,
                },
                {
                    u'admin_status': 1,
                    u'alias': u'desc2',
                    u'description': u'1.0',
                    u'device_id': device_id,
                    u'id_tags': [u'interface:1.0'],
                    u'index': 48,
                    u'mac_address': u'42:01:0a:a4:00:33',
                    u'name': u'1.0',
                    u'oper_status': 1,
                },
                {
                    u'admin_status': 1,
                    u'alias': u'desc3',
                    u'description': u'/Common/http-tunnel',
                    u'device_id': device_id,
                    u'id_tags': [u'interface:/Common/http-tunnel'],
                    u'index': 80,
                    u'mac_address': u'42:01:0a:a4:00:34',
                    u'name': u'/Common/http-tunnel',
                    u'oper_status': 4,
                },
                {
                    u'admin_status': 1,
                    u'alias': u'desc4',
                    u'description': u'/Common/socks-tunnel',
                    u'device_id': device_id,
                    u'id_tags': [u'interface:/Common/socks-tunnel'],
                    u'index': 96,
                    u'mac_address': u'42:01:0a:a4:00:34',
                    u'name': u'/Common/socks-tunnel',
                    u'oper_status': 4,
                },
            ],
            "ip_addresses": [
                {"interface_id": "default:{}:32".format(device_ip), "ip_address": "10.164.0.51", "prefixlen": 32}
            ],
            u'namespace': u'default',
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
        u'description': u'Cisco IOS Software, IOS-XE Software, Catalyst L3 Switch '
        u'Software (CAT3K_CAA-UNIVERSALK9-M), Version 03.06.06E RELEASE '
        u'SOFTWARE (fc1) Technical Support: '
        u'http://www.cisco.com/techsupport Copyright (c) 1986-2016 by '
        u'Cisco Systems, Inc. Compiled Sat 17-Dec-',
        u'id': device_id,
        u'id_tags': [u'device_namespace:default', u'snmp_device:' + device_ip],
        u'ip_address': device_ip,
        u'location': u'4th floor',
        u'name': u'Cat-3850-4th-Floor.companyname.local',
        u'os_name': u'IOS',
        u'profile': u'cisco-3850',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.1745',
        u'tags': [
            u'device_hostname:Cat-3850-4th-Floor.companyname.local',
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_host:Cat-3850-4th-Floor.companyname.local',
            u'snmp_profile:cisco-3850',
        ],
        u'vendor': u'cisco',
        u'version': u'03.06.06E',
        u'serial_number': u'FOCXXXXXXXX',
        u'model': u'CAT3K_CAA-UNIVERSALK9-M',
        u'device_type': u'switch',
    }
    assert device == actual_device

    # assert one interface
    pprint.pprint(event1['interfaces'])
    assert len(event1['interfaces']) > 1
    actual_interface = event1['interfaces'][0]
    interface = {
        u'admin_status': 1,
        u'description': u'GigabitEthernet0/0',
        u'device_id': u'default:' + device_ip,
        u'id_tags': [u'interface:Gi0/0'],
        u'index': 1,
        u'mac_address': u'00:00:00:00:00:00',
        u'name': u'Gi0/0',
        u'oper_status': 2,
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
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'name': u'catalyst-6000.example',
        u'profile': u'cisco-catalyst',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.241',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_host:catalyst-6000.example',
            u'device_hostname:catalyst-6000.example',
            u'snmp_profile:cisco-catalyst',
        ],
        u'vendor': u'cisco',
        u'serial_number': u'SCA044001J9',
        u'device_type': u'switch',
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
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'iLO4',
        u'os_name': u'RHEL',
        u'os_version': u'3.10.0-862.14.4.el7.ve.x86_64',
        u'product_name': u'Integrated Lights-Out',
        u'name': u'hp-ilo4.example',
        u'profile': u'hp-ilo4',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.232.9.4.10',
        u'version': u'A04-08/12/2018',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:hp',
            u'snmp_device:' + device_ip,
            u'snmp_host:hp-ilo4.example',
            u'device_hostname:hp-ilo4.example',
            u'snmp_profile:hp-ilo4',
        ],
        u'vendor': u'hp',
        u'serial_number': u'dXPEdPBE5yKtjW9xx3',
        u'device_type': u'server',
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
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'name': u'hpe-proliant.example',
        u'profile': u'hpe-proliant',
        u'status': 1,
        u'model': u'BL35p G1',
        u'os_name': u'RHEL',
        u'os_version': u'3.10.0-862.15.4.el7.ve.x86_64',
        u'product_name': u'ProLiant',
        u'version': u'A04-08/12/2019',
        u'sys_object_id': u'1.3.6.1.4.1.232.1.2',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:hp',
            u'snmp_device:' + device_ip,
            u'snmp_host:hpe-proliant.example',
            u'device_hostname:hpe-proliant.example',
            u'snmp_profile:hpe-proliant',
        ],
        u'vendor': u'hp',
        u'serial_number': u'dLPEdPBE5yKtjW9xx3',
        u'device_type': u'other',
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
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
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
        u'device_type': u'ups',
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
        u'description': u'Juniper Networks, Inc. ex2200-24t-4g internet router, kernel '
        + u'JUNOS 10.2R1.8 #0: 2010-05-27 20:13:49 UTC',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'ex2200-24t-4g',
        u'os_name': u'JUNOS',
        u'os_version': u'10.2R1.8',
        u'product_name': u'EX2200 Ethernet Switch',
        u'profile': u'juniper-ex',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.2636.1.1.1.2.30',
        u'serial_number': u'dXPEdPBE5yKtjW9xx3',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:juniper-networks',
            u'snmp_device:' + device_ip,
            u'snmp_profile:juniper-ex',
        ],
        u'vendor': u'juniper-networks',
        u'version': u'version-1.0',
        u'device_type': u'switch',
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
        u'description': u'Juniper Networks, Inc. mx480 internet router, kernel JUNOS 11.2R1.10 '
        + u'#0: 2011-07-29 07:15:34 UTC',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'mx480',
        u'os_name': u'JUNOS',
        u'os_version': u'11.2R1.10',
        u'product_name': u'MX480 Router',
        u'profile': u'juniper-mx',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.2636.1.1.1.2.25',
        u'serial_number': u'dXPEdPBE5yKtjW9xx4',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:juniper-networks',
            u'snmp_device:' + device_ip,
            u'snmp_profile:juniper-mx',
        ],
        u'vendor': u'juniper-networks',
        u'version': u'version-1.1',
        u'device_type': u'router',
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
        u'description': u'Juniper Networks, Inc. srx3400 internet router, kernel JUNOS '
        + u'10.4R3.4 #0: 2011-03-19 22:06:23 UTC',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'srx3400',
        u'os_name': u'JUNOS',
        u'os_version': u'10.4R3.4',
        u'product_name': u'SRX 3400 Router',
        u'profile': u'juniper-srx',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.2636.1.1.1.2.35',
        u'serial_number': u'dXPEdPBE5yKtjW9xx5',
        u'tags': [
            u'device_id:' + device_id,
            u'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:juniper-networks',
            u'snmp_device:' + device_ip,
            u'snmp_profile:juniper-srx',
        ],
        u'vendor': u'juniper-networks',
        u'version': u'version-1.2',
        u'device_type': u'firewall',
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
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            'device_namespace:default',
            'snmp_device:' + device_ip,
            'snmp_profile:palo-alto',
        ],
        'vendor': 'paloaltonetworks',
        'version': '9.0.5',
        'device_type': 'other',
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
        'device_type': 'other',
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
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'profile': u'idrac',
        u'status': 1,
        u'model': u'customFooVersion',
        u'os_name': u'Ubuntu',
        u'os_version': u'18.04.3 LTS (Bionic Beaver)',
        u'product_name': u'PowerEdge',
        u'version': u'2.5.4',
        u'sys_object_id': u'1.3.6.1.4.1.674.10892.2',
        u'tags': [
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:dell',
            u'snmp_device:' + device_ip,
            u'snmp_profile:idrac',
        ],
        u'vendor': u'dell',
        u'serial_number': u'acted quaintly driving',
        u'device_type': u'server',
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
    device_id = u'default:' + device_ip

    # CHANGE
    topology_link1 = {
        'id': device_id + ':1.216',
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
        u'description': u'Cisco IOS Software [Bengaluru], ASR1000 Software '
        '(X86_64_LINUX_IOSD-UNIVERSALK9-M), Version 17.6.4, RELEASE '
        'SOFTWARE (fc1)',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'X86_64_LINUX_IOSD-UNIVERSALK9-M',
        u'os_name': u'IOS',
        u'profile': u'cisco-asr',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.1861',
        u'tags': [
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_profile:cisco-asr',
        ],
        u'vendor': u'cisco',
        u'version': u'17.6.4',
        u'device_type': u'router',
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
        u'description': u'Cisco IOS XR Software (Cisco ASR9K Series),  Version ' '6.4.2[Default]',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': 'Cisco ASR9K Series',
        u'os_name': u'IOSXR',
        u'profile': u'cisco-asr',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.1639',
        u'tags': [
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_profile:cisco-asr',
        ],
        u'vendor': u'cisco',
        u'version': u'6.4.2',
        u'device_type': u'router',
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
        u'description': u'Cisco IOS XR Software (ASR9K), Version 7.1.3  Copyright (c) '
        '2013-2020 by Cisco Systems, Inc.',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'model': u'ASR9K',
        u'os_name': u'IOSXR',
        u'profile': u'cisco-asr',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.2658',
        u'tags': [
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_profile:cisco-asr',
        ],
        u'vendor': u'cisco',
        u'version': u'7.1.3',
        u'device_type': u'router',
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
    device_id = u'default:' + device_ip

    topology_link1 = {
        'id': device_id + ':1.5',
        'source_type': 'cdp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':1', 'id': ''},
        },
        "remote": {
            "device": {
                "id": "K10-ITV.tine.no",
                "ip_address": "10.10.0.134",
                u"description": u'Cisco IOS Software, C2960C Software (C2960c405-UNIVERSALK9-M), Version 15.0(2)SE8, '
                'RELEASE SOFTWARE (fc1)\nTechnical Support: http://www.cisco.com/techsupport\r',
            },
            "interface": {"id": "GE0/1", "id_type": "interface_name"},
        },
    }
    topology_link2 = {
        'id': device_id + ':2.3',
        'source_type': 'cdp',
        "local": {
            "device": {'dd_id': device_id},
            'interface': {'dd_id': device_id + ':2', "id": ''},
        },
        "remote": {
            "device": {
                "id": "K06-ITV.tine.no",
                "ip_address": "10.10.0.132",
                u"description": u'Cisco IOS Software, C2960C Software (C2960c405-UNIVERSALK9-M), Version 15.0(2)SE8, '
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
    device_id = u'default:' + device_ip

    topology_link = {
        'id': device_id + ':7.1',
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
        u'description': u'Cisco Controller',
        u'id': device_id,
        u'id_tags': [
            u'device_namespace:default',
            u'snmp_device:' + device_ip,
        ],
        u'ip_address': device_ip,
        u'location': 'Datadog Paris',
        u'name': 'DDOGWLC',
        u'profile': u'cisco-legacy-wlc',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.1069',
        u'tags': [
            'device_id:' + device_id,
            'device_ip:' + device_ip,
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_host:DDOGWLC',
            'device_hostname:DDOGWLC',
            u'snmp_profile:cisco-legacy-wlc',
        ],
        u'vendor': u'cisco',
        u'device_type': u'wlc',
    }
    assert_device_metadata(aggregator, device)
