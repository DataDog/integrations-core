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

from datadog_checks.cisco_catalyst_center.check import CiscoCatalystCenterCheck
from datadog_checks.cisco_catalyst_center.ndm_models import (
    STATUS_REACHABLE,
    STATUS_UNREACHABLE,
    batch_payloads,
    create_device_metadata,
    create_interface_metadata,
)

from .common import load_captured, load_wireless_synthetic


def _device_record():
    return load_captured('data_network_devices')['response'][0]


def test_device_metadata_id_is_the_catalyst_center_instance_uuid():
    # Per the product brief's Device Metadata table: NDM `id` <- `id` (instanceUuid). Unlike
    # managementIpAddress, the UUID is present on every record and survives renumbering.
    record = _device_record()

    assert create_device_metadata(record, namespace='default').id == record['id']


def test_device_metadata_carries_the_snmp_compatible_device_id_tag():
    # The UUID identifies the record; this tag is what lines it up with the SNMP check, which
    # identifies the same switch as {namespace}:{ip}.
    device = create_device_metadata(_device_record(), namespace='default')

    assert 'device_id:default:10.10.20.175' in device.id_tags


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


def test_device_metadata_maps_reachability_to_a_status_code():
    # The data API reports `reachabilityHealthStatus`, not the `reachabilityStatus` the brief
    # names, and it uses upper case where the legacy endpoint uses title case.
    record = dict(_device_record(), reachabilityHealthStatus='REACHABLE')

    assert create_device_metadata(record, namespace='default').status == STATUS_REACHABLE


def test_device_metadata_given_unreachable_device_reports_unreachable():
    record = dict(_device_record(), reachabilityHealthStatus='UNREACHABLE')

    assert create_device_metadata(record, namespace='default').status == STATUS_UNREACHABLE


def test_device_metadata_maps_switch_family_to_a_supported_device_type():
    device = create_device_metadata(_device_record(), namespace='default')

    assert device.device_type == 'switch'


def test_device_metadata_maps_access_point_family_to_a_supported_device_type():
    ap = load_wireless_synthetic('data_network_devices_wireless')['response'][0]

    assert create_device_metadata(ap, namespace='default').device_type == 'access_point'


def test_device_metadata_maps_wireless_controller_family_to_wlc():
    wlc = load_wireless_synthetic('data_network_devices_wireless')['response'][1]

    assert create_device_metadata(wlc, namespace='default').device_type == 'wlc'


def test_device_metadata_takes_name_and_os_from_the_data_api_field_names():
    # The brief maps these from `hostname` and `softwareType`, which the data API does not have.
    device = create_device_metadata(_device_record(), namespace='default')

    assert device.name == 'sw1'
    assert device.os_name == 'IOS-XE'


def test_interface_metadata_device_id_is_the_parent_device_uuid():
    # Per the brief: interface `device_id` <- parent device instanceUuid. The interface record
    # already carries it as `networkDeviceId`, so no join through the IP is needed.
    record = load_captured('data_interfaces_configuration')['response'][0]

    interface = create_interface_metadata(record, namespace='default')

    assert interface.device_id == record['networkDeviceId']


def test_interface_device_ids_resolve_to_the_collected_devices():
    # The interface's device_id must be one of the device ids, or interfaces attach to nothing.
    devices = load_captured('data_network_devices')['response']
    device_ids = {create_device_metadata(d, namespace='default').id for d in devices}

    interfaces = load_captured('data_interfaces_configuration')['response']
    interface_parents = {create_interface_metadata(i, namespace='default').device_id for i in interfaces}

    assert interface_parents <= device_ids


def test_interface_metadata_uses_the_interface_uuid_as_raw_id():
    # The brief specifies raw_id_type as the constant "interface_uuid".
    record = load_captured('data_interfaces_configuration')['response'][0]

    interface = create_interface_metadata(record, namespace='default')

    assert interface.raw_id_type == 'interface_uuid'
    assert interface.raw_id == record['id']


def test_interface_metadata_converts_speed_from_kbps_to_bps():
    record = load_captured('data_interfaces_configuration')['response'][0]

    assert create_interface_metadata(record, namespace='default').speed == 1_000_000_000


def test_batch_payloads_splits_at_one_hundred_items():
    devices = [create_device_metadata(_device_record(), namespace='default') for _ in range(250)]

    batches = list(batch_payloads('default', devices))

    assert [batch.size for batch in batches] == [100, 100, 50]


def test_batch_payloads_given_nothing_yields_nothing():
    assert list(batch_payloads('default', [])) == []


def test_check_given_ndm_disabled_sends_no_metadata_event(dd_run_check, aggregator, instance):
    from .conftest import ScriptedHttp

    instance['send_ndm_metadata'] = False
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    check.client.http = ScriptedHttp([load_captured('data_network_devices')])

    dd_run_check(check)

    assert aggregator.events == []


def test_check_given_ndm_enabled_sends_devices_in_the_metadata_event(dd_run_check, aggregator, instance):
    from .conftest import ViewRoutedHttp

    instance['send_ndm_metadata'] = True
    instance['collect_stacks'] = False
    instance['collect_site_health'] = False
    check = CiscoCatalystCenterCheck('cisco_catalyst_center', {}, [instance])
    check.client.http = ViewRoutedHttp(
        {
            None: load_captured('data_network_devices'),
            'configuration': load_captured('data_interfaces_configuration'),
            'statistics': load_captured('data_interfaces_statistics'),
        }
    )

    dd_run_check(check)

    payloads = [
        json.loads(p) for p in aggregator.get_event_platform_events('network-devices-metadata', parse_json=False)
    ]
    devices = [d for payload in payloads for d in payload.get('devices', [])]
    expected = {record['id'] for record in load_captured('data_network_devices')['response']}
    assert {d['id'] for d in devices} == expected
