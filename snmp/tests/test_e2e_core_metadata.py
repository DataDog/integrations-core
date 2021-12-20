# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pprint

import pytest

from . import common

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def assert_network_devices_metadata(aggregator, events):
    actual_events = aggregator.get_event_platform_events("network-devices-metadata", parse_json=True)
    for event in actual_events:
        # `collect_timestamp` depend on check run time and cannot be asserted reliably,
        # we are replacing it with `0` if present
        if 'collect_timestamp' in event:
            event['collect_timestamp'] = 0
    assert events == actual_events


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
                    u'os_hostname': u'f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
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
                    u'mac_address': u'0x42010aa40033',
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
                    u'mac_address': u'0x42010aa40033',
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
                    u'mac_address': u'0x42010aa40033',
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
                    u'mac_address': u'0x42010aa40034',
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
                    u'mac_address': u'0x42010aa40034',
                    u'name': u'/Common/socks-tunnel',
                    u'oper_status': 4,
                },
            ],
            u'namespace': u'default',
            u'subnet': u'',
        },
    ]
    assert_network_devices_metadata(aggregator, events)


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

    events = aggregator.get_event_platform_events("network-devices-metadata", parse_json=True)

    # since there are >100 resources (device+interfaces), the interfaces are split into 2 events
    assert len(events) == 2
    event1 = events[0]

    # assert device (there is only one device)
    pprint.pprint(event1['devices'])
    assert len(event1['devices']) == 1
    actual_device = event1['devices'][0]
    device = {
        u'description': u'Cisco IOS Software, IOS-XE Software, Catalyst L3 Switch '
        u'Software (CAT3K_CAA-UNIVERSALK9-M), Version 03.06.06E RELEASE '
        u'SOFTWARE (fc1) Technical Support: '
        u'http://www.cisco.com/techsupport Copyright (c) 1986-2016 by '
        u'Cisco Systems, Inc. Compiled Sat 17-Dec-',
        u'id': u'default:' + device_ip,
        u'id_tags': [u'device_namespace:default', u'snmp_device:' + device_ip],
        u'ip_address': device_ip,
        u'location': u'4th floor',
        u'name': u'Cat-3850-4th-Floor.companyname.local',
        u'os_name': u'IOS',
        u'profile': u'cisco-3850',
        u'status': 1,
        u'sys_object_id': u'1.3.6.1.4.1.9.1.1745',
        u'tags': [
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
        u'mac_address': u'0x000000000000',
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

    events = aggregator.get_event_platform_events("network-devices-metadata", parse_json=True)
    assert len(events) == 1
    event1 = events[0]

    # assert device (there is only one device)
    pprint.pprint(event1['devices'])
    assert len(event1['devices']) == 1
    actual_device = event1['devices'][0]
    device = {
        u'id': u'default:' + device_ip,
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
            u'device_namespace:default',
            u'device_vendor:cisco',
            u'snmp_device:' + device_ip,
            u'snmp_host:catalyst-6000.example',
            u'snmp_profile:cisco-catalyst',
        ],
        u'vendor': u'cisco',
        u'serial_number': u'SCA044001J9',
    }
    assert device == actual_device
