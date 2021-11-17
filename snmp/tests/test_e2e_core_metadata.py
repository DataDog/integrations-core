# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from copy import deepcopy

import pytest

from . import common

pytestmark = [pytest.mark.e2e, common.snmp_integration_only]


def assert_network_devices_metadata(aggregator, events):
    actual_events = aggregator.get_event_platform_events("network-devices-metadata", parse_json=True)
    for event in actual_events:
        # `collect_timestamp` depend on check run time and cannot be asserted reliably,
        # we are replacing it with `0` if present
        if 'collect_timestamp' in event:
            event['collect_timestamp'] = 0
    assert events == actual_events


def test_e2e_core_metadata(dd_agent_check):
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
                    'name': 'f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                    'profile': 'f5-big-ip',
                    'status': 1,
                    'subnet': '',
                    'sys_object_id': '1.3.6.1.4.1.3375.2.1.3.4.43',
                    'tags': [
                        'device_namespace:default',
                        'device_vendor:f5',
                        'snmp_device:' + device_ip,
                        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
                        'snmp_profile:f5-big-ip',
                    ],
                    'vendor': 'f5',
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
                    'mac_address': '0x42010aa40033',
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
                    'mac_address': '0x42010aa40033',
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
                    'mac_address': '0x42010aa40033',
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
                    'mac_address': '0x42010aa40034',
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
                    'mac_address': '0x42010aa40034',
                    'name': '/Common/socks-tunnel',
                    'oper_status': 4,
                },
            ],
            'namespace': 'default',
            'subnet': '',
        },
    ]
    assert_network_devices_metadata(aggregator, events)

