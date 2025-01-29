# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.cisco_aci.models import DeviceMetadataList, InterfaceMetadata, NetworkDevicesMetadata

DEVICE_METADATA = [
    {
        'id': 'default:10.0.200.0',
        'id_tags': [
            'device_ip:10.0.200.0',
            'device_namespace:default',
            'device_hostname:leaf101',
            'device_id:default:10.0.200.0',
        ],
        'integration': 'cisco-aci',
        'device_type': 'switch',
        'tags': [
            'device_vendor:cisco',
            'source:cisco-aci',
            'switch_role:leaf',
            'apic_role:leaf',
            'node_id:101',
            'fabric_state:active',
            'fabric_pod_id:1',
            'device_ip:10.0.200.0',
            'device_namespace:default',
            'device_hostname:leaf101',
            'device_id:default:10.0.200.0',
        ],
        'ip_address': '10.0.200.0',
        'model': 'N9K-C93180YC-FX',
        'name': 'leaf101',
        'serial_number': 'FDO20440TS1',
        'status': 1,
        'vendor': 'cisco',
        'version': '',
    },
    {
        'id': 'default:10.0.200.1',
        'id_tags': [
            'device_ip:10.0.200.1',
            'device_namespace:default',
            'device_hostname:leaf102',
            'device_id:default:10.0.200.1',
        ],
        'integration': 'cisco-aci',
        'device_type': 'switch',
        'tags': [
            'device_vendor:cisco',
            'source:cisco-aci',
            'switch_role:leaf',
            'apic_role:leaf',
            'node_id:102',
            'fabric_state:active',
            'fabric_pod_id:1',
            'device_ip:10.0.200.1',
            'device_namespace:default',
            'device_hostname:leaf102',
            'device_id:default:10.0.200.1',
        ],
        'ip_address': '10.0.200.1',
        'model': 'N9K-C93180YC-FX',
        'name': 'leaf102',
        'serial_number': 'FDO20510HCA',
        'status': 1,
        'vendor': 'cisco',
        'version': '',
    },
    {
        'id': 'default:10.0.200.4',
        'id_tags': [
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
        ],
        'integration': 'cisco-aci',
        'device_type': 'other',
        'tags': [
            'device_vendor:cisco',
            'source:cisco-aci',
            'apic_role:controller',
            'node_id:1',
            'fabric_state:unknown',
            'fabric_pod_id:1',
            'device_ip:10.0.200.4',
            'device_namespace:default',
            'device_hostname:apic1',
            'device_id:default:10.0.200.4',
        ],
        'ip_address': '10.0.200.4',
        'model': 'APIC-SERVER-M1',
        'name': 'apic1',
        'serial_number': 'FCH1928V0SL',
        'status': 1,
        'vendor': 'cisco',
        'version': 'A',
    },
    {
        'id': 'default:10.0.200.5',
        'id_tags': [
            'device_ip:10.0.200.5',
            'device_namespace:default',
            'device_hostname:spine201',
            'device_id:default:10.0.200.5',
        ],
        'integration': 'cisco-aci',
        'device_type': 'switch',
        'tags': [
            'device_vendor:cisco',
            'source:cisco-aci',
            'switch_role:spine',
            'apic_role:spine',
            'node_id:201',
            'fabric_state:active',
            'fabric_pod_id:1',
            'device_ip:10.0.200.5',
            'device_namespace:default',
            'device_hostname:spine201',
            'device_id:default:10.0.200.5',
        ],
        'ip_address': '10.0.200.5',
        'model': 'N9K-C9336PQ',
        'name': 'spine201',
        'serial_number': 'SAL2014N5U4',
        'status': 1,
        'vendor': 'cisco',
        'version': '',
    },
]

INTERFACE_METADATA = [
    {
        'admin_status': 1,
        'alias': 'eth1/1',
        'raw_id': 'eth1/1',
        'device_id': 'default:10.0.200.0',
        'id_tags': [
            'interface:eth1/1',
        ],
        'index': 1,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/1',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth1/2',
        'raw_id': 'eth1/2',
        'device_id': 'default:10.0.200.0',
        'id_tags': [
            'interface:eth1/2',
        ],
        'index': 2,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/2',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth1/3',
        'raw_id': 'eth1/3',
        'device_id': 'default:10.0.200.0',
        'id_tags': [
            'interface:eth1/3',
        ],
        'index': 3,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/3',
        'oper_status': 2,
        'status': 'down',
    },
    {
        'admin_status': 1,
        'alias': 'eth1/1',
        'raw_id': 'eth1/1',
        'device_id': 'default:10.0.200.1',
        'id_tags': [
            'interface:eth1/1',
        ],
        'index': 1,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/1',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth1/2',
        'raw_id': 'eth1/2',
        'device_id': 'default:10.0.200.1',
        'id_tags': [
            'interface:eth1/2',
        ],
        'index': 2,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/2',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth1/3',
        'raw_id': 'eth1/3',
        'device_id': 'default:10.0.200.1',
        'id_tags': [
            'interface:eth1/3',
        ],
        'index': 3,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth1/3',
        'oper_status': 2,
        'status': 'down',
    },
    {
        'admin_status': 1,
        'alias': 'eth5/1',
        'raw_id': 'eth5/1',
        'device_id': 'default:10.0.200.5',
        'id_tags': [
            'interface:eth5/1',
        ],
        'index': 1,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth5/1',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth5/2',
        'raw_id': 'eth5/2',
        'device_id': 'default:10.0.200.5',
        'id_tags': [
            'interface:eth5/2',
        ],
        'index': 2,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth5/2',
        'oper_status': 1,
        'status': 'up',
    },
    {
        'admin_status': 1,
        'alias': 'eth7/1',
        'raw_id': 'eth7/1',
        'device_id': 'default:10.0.200.5',
        'id_tags': [
            'interface:eth7/1',
        ],
        'index': 1,
        'integration': 'cisco-aci',
        'mac_address': 'not-applicable',
        'name': 'eth7/1',
        'oper_status': 2,
        'status': 'down',
    },
]

TOPOLOGY_LINK_METADATA = [
    {
        'id': 'default:10.0.200.0:cisco-aci-eth1/49.cisco-aci-eth5/1',
        'local': {
            'device': {
                'dd_id': 'default:10.0.200.0',
            },
            'interface': {
                'dd_id': 'default:10.0.200.0:cisco-aci-eth1/49',
                'id': 'eth1/49',
                'id_type': 'interface_name',
            },
        },
        'remote': {
            'device': {
                'dd_id': 'default:10.0.200.5',
                'description': 'topology/pod-1/node-201',
                'id': '6a:00:21:1f:55:2a',
                'id_type': 'mac',
                'ip_address': '10.0.200.5',
                'name': 'SP201',
            },
            'interface': {
                'dd_id': 'default:10.0.200.5:cisco-aci-eth5/1',
                'description': 'topology/pod-1/paths-201/pathep-[eth5/1]',
                'id': '6a:00:21:1f:55:2a',
                'id_type': 'mac_address',
            },
        },
        'source_type': 'lldp',
    },
    {
        'id': 'default:10.0.200.1:cisco-aci-eth1/49.cisco-aci-eth5/2',
        'local': {
            'device': {
                'dd_id': 'default:10.0.200.1',
            },
            'interface': {
                'dd_id': 'default:10.0.200.1:cisco-aci-eth1/49',
                'id': 'eth1/49',
                'id_type': 'interface_name',
            },
        },
        'remote': {
            'device': {
                'dd_id': 'default:10.0.200.5',
                'description': 'topology/pod-1/node-201',
                'id': '6a:00:21:1f:55:2b',
                'id_type': 'mac',
                'ip_address': '10.0.200.5',
                'name': 'SP201',
            },
            'interface': {
                'dd_id': 'default:10.0.200.5:cisco-aci-eth5/2',
                'description': 'topology/pod-1/paths-201/pathep-[eth5/2]',
                'id': '6a:00:21:1f:55:2b',
                'id_type': 'mac_address',
            },
        },
        'source_type': 'lldp',
    },
]

EXPECTED_DEVICE_METADATA_RESULT = DeviceMetadataList(device_metadata=DEVICE_METADATA)

# "2012-01-14 03:21:34" in seconds
MOCK_TIME_EPOCH = 1326511294

EXPECTED_INTERFACE_METADATA = [InterfaceMetadata(**im) for im in INTERFACE_METADATA]

EXPECTED_METADATA_EVENTS = [
    NetworkDevicesMetadata(
        namespace='default',
        devices=DEVICE_METADATA,
        interfaces=INTERFACE_METADATA,
        links=TOPOLOGY_LINK_METADATA,
        collect_timestamp=MOCK_TIME_EPOCH,
    )
]
