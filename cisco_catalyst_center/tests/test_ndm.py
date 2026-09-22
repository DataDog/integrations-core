# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""NDM metadata payloads.

The device id is the load-bearing field: it must be `{namespace}:{management_ip}`, identical to
what the SNMP check computes for the same device. If the two disagree, Catalyst Center and SNMP
resolve to different NDM devices and the pairing the product brief is built on silently
delivers half its value.
"""

from __future__ import annotations

import json

import pytest

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.ndm_models import (
    OPER_STATUS_UNKNOWN,
    STATUS_DOWN,
    STATUS_REACHABLE,
    STATUS_UNREACHABLE,
    STATUS_UP,
    batch_payloads,
    create_device_metadata,
    create_interface_metadata,
)

from .common import load_captured, load_wireless_synthetic
from .conftest import ScriptedHttp, ViewRoutedHttp


def _device_record():
    return load_captured('data_network_devices')['response'][0]


def test_device_metadata_given_a_captured_switch_returns_the_expected_payload():
    """The whole NDM device payload for one recorded sandbox switch.

    Asserting the payload as a unit rather than field by field is what catches a field that
    quietly stops being populated. Two of them carry most of the weight. `id` is the instanceUuid
    rather than the management IP, because the UUID is present on every record and survives
    renumbering. The `device_id` tag is `{namespace}:{ip}`, byte-identical to what the SNMP check
    computes for the same switch -- if the two disagree, Catalyst Center and SNMP resolve to
    different NDM devices and the pairing the product brief is built on delivers half its value.
    """
    device = create_device_metadata(_device_record(), namespace='default')

    assert device.model_dump() == {
        'integration': 'cisco_catalyst_center',
        'id': 'aa754801-8895-41e8-8ca5-27ee415c9c42',
        'id_tags': ['device_namespace:default', 'device_ip:10.10.20.175', 'device_id:default:10.10.20.175'],
        'tags': [
            'device_namespace:default',
            'device_ip:10.10.20.175',
            'device_id:default:10.10.20.175',
            'device_uuid:aa754801-8895-41e8-8ca5-27ee415c9c42',
            'device_hostname:sw1',
            'device_family:Switches and Hubs',
            'device_role:ACCESS',
            'device_series:Cisco Catalyst 9000 Series Virtual Switches',
            'device_vendor:cisco',
        ],
        'ip_address': '10.10.20.175',
        'status': STATUS_REACHABLE,
        # The brief maps name and os_name from `hostname` and `softwareType`, which the data API
        # does not have; they come from `name` and `osType` instead.
        'name': 'sw1',
        'vendor': 'cisco',
        'serial_number': 'CML12345UAD',
        'location': 'Global',
        'version': '17.12.1prd9',
        'product_name': 'C9KV-UADP-8P',
        'os_name': 'IOS-XE',
        'device_type': 'switch',
        'site_id': '00f6df3f-c067-4d55-8ff3-059d35bbaa0c',
        'site_name': 'Global',
        'namespace': 'default',
    }


def test_device_metadata_honours_a_custom_namespace():
    # The namespace must match the SNMP check's, so it has to flow through rather than be fixed.
    device = create_device_metadata(_device_record(), namespace='campus-east')

    assert 'device_namespace:campus-east' in device.id_tags
    assert 'device_id:campus-east:10.10.20.175' in device.id_tags


def test_device_metadata_given_no_management_ip_still_has_a_unique_id():
    # An access point reporting through a controller may carry no management IP. Under an
    # IP-derived id every such device would collide on one record; the UUID cannot.
    record = dict(_device_record(), managementIpAddress=None)

    device = create_device_metadata(record, namespace='default')

    assert device.id == record['id']
    assert device.ip_address == ''


@pytest.mark.parametrize(
    ('reachability', 'expected_status'),
    [
        ('REACHABLE', STATUS_REACHABLE),
        ('UNREACHABLE', STATUS_UNREACHABLE),
    ],
)
def test_device_metadata_maps_reachability_to_a_status_code(reachability, expected_status):
    # The data API reports `reachabilityHealthStatus`, not the `reachabilityStatus` the brief
    # names, and it uses upper case where the legacy endpoint uses title case.
    record = dict(_device_record(), reachabilityHealthStatus=reachability)

    assert create_device_metadata(record, namespace='default').status == expected_status


@pytest.mark.parametrize(
    ('record_index', 'expected_type'),
    [
        (0, 'access_point'),  # Unified AP
        (1, 'wlc'),  # Wireless Controller
    ],
)
def test_device_metadata_maps_a_wireless_family_to_a_supported_device_type(record_index, expected_type):
    # NDM drops a device_type it does not recognise, so an unmapped family collects nothing. The
    # switch family is covered by the payload assertion above; these are the two synthetic ones.
    record = load_wireless_synthetic('data_network_devices_wireless')['response'][record_index]

    assert create_device_metadata(record, namespace='default').device_type == expected_type


def test_interface_metadata_given_a_captured_interface_returns_the_expected_payload():
    """The whole NDM interface payload for one recorded sandbox port.

    `device_id` is the parent device's instanceUuid, taken straight from `networkDeviceId`, so an
    interface attaches to its device without a join through the management IP. `speed` is the
    other field worth naming: the API documents it in Kbps and returns it as a string, while NDM
    expects bits per second, so a 1 GbE port reporting "1000000" has to land as 1_000_000_000.
    """
    record = load_captured('data_interfaces_configuration')['response'][0]

    interface = create_interface_metadata(record, namespace='default')

    assert interface.model_dump() == {
        'integration': 'cisco_catalyst_center',
        'device_id': '5a105585-b595-4b87-a01d-fd057a54abd4',
        'raw_id': '1faa42f2-c41c-4f6c-83db-e25bfd9c81f8',
        'raw_id_type': 'interface_uuid',
        'id_tags': ['interface:GigabitEthernet0/0'],
        'name': 'GigabitEthernet0/0',
        # The data API returns both of these as null on every interface. The intent API sweep in
        # collect_interfaces fills them in; this test calls create_interface_metadata directly on
        # the raw data-API record, bypassing that sweep.
        'description': '',
        'mac_address': '',
        'admin_status': STATUS_UP,
        'oper_status': STATUS_UP,
        'speed': 1_000_000_000,
        'vlan': None,
        'port_role': 'routed',
    }


@pytest.mark.parametrize(
    ('reported_status', 'expected_admin', 'expected_oper'),
    [
        ('UP', STATUS_UP, STATUS_UP),
        ('DOWN', STATUS_DOWN, STATUS_DOWN),
        # A status Catalyst Center never reported must not read the same as one it reported
        # down, or an interface the appliance is simply silent about looks like an outage.
        (None, None, OPER_STATUS_UNKNOWN),
    ],
)
def test_interface_metadata_maps_the_reported_status(reported_status, expected_admin, expected_oper):
    record = dict(
        load_captured('data_interfaces_configuration')['response'][0],
        adminStatus=reported_status,
        operStatus=reported_status,
    )

    interface = create_interface_metadata(record, namespace='default')

    assert interface.admin_status == expected_admin
    assert interface.oper_status == expected_oper


def test_interface_metadata_port_role_prefers_uplink_when_iswan_is_set():
    # The brief derives port_role from interfaceType, portMode and description; an interface the
    # appliance has identified as a WAN link is an uplink regardless of its port mode.
    record = dict(load_captured('data_interfaces_configuration')['response'][0], isWan=True)

    assert create_interface_metadata(record, namespace='default').port_role == 'uplink'


@pytest.mark.parametrize(('device_count', 'expected_sizes'), [(0, []), (250, [100, 100, 50])])
def test_batch_payloads_splits_into_batches_of_at_most_one_hundred(device_count, expected_sizes):
    # The intake rejects an oversized payload outright, so a sweep of a large estate has to be
    # split. Nothing in, nothing out: an empty cycle must not send an empty payload either.
    devices = [create_device_metadata(_device_record(), namespace='default') for _ in range(device_count)]

    batches = list(batch_payloads('default', devices))

    assert [batch.size for batch in batches] == expected_sizes


def test_check_given_ndm_disabled_sends_no_metadata_event(dd_run_check, aggregator, instance):
    instance['send_ndm_metadata'] = False
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    check.client.http = ScriptedHttp([load_captured('data_network_devices')])

    dd_run_check(check)

    assert aggregator.get_event_platform_events('network-devices-metadata', parse_json=False) == []


def test_check_given_ndm_enabled_sends_devices_in_the_metadata_event(dd_run_check, aggregator, instance):
    instance['send_ndm_metadata'] = True
    instance['collect_stacks'] = False
    instance['collect_site_health'] = False
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    check.client.http = ViewRoutedHttp(
        {
            None: load_captured('data_network_devices'),
            'configuration': load_captured('data_interfaces_configuration'),
            'statistics': load_captured('data_interfaces_statistics'),
        },
        # The interface collector always sweeps the intent API; without a route for it the
        # viewless request would be served the device payload above.
        by_path={'/dna/intent/api/v1/interface': {'response': []}},
    )

    dd_run_check(check)

    payloads = [
        json.loads(p) for p in aggregator.get_event_platform_events('network-devices-metadata', parse_json=False)
    ]
    devices = [d for payload in payloads for d in payload.get('devices', [])]
    expected = {record['id'] for record in load_captured('data_network_devices')['response']}
    assert {d['id'] for d in devices} == expected
