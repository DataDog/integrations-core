# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.pan_firewall.auth import Credentials
from datadog_checks.pan_firewall.collectors.ha import HA_CMD, HA_INTERFACE_CMD
from datadog_checks.pan_firewall.firewalls import FirewallTarget
from datadog_checks.pan_firewall.identity import global_tags, parse_system_info
from datadog_checks.pan_firewall.interface_config import parse_interface_config
from datadog_checks.pan_firewall.metadata import build_device, build_interfaces
from datadog_checks.pan_firewall.xml_utils import parse_response

from .common import (
    FIXTURES,
    FW_A_INTERFACE_ALL,
    FW_A_IP,
    FW_A_SERIAL,
    INTERFACE_ALL_CMD,
    INTERFACE_CONFIG_CMD,
    INTERFACE_NAMES,
    SYNTHETIC,
    SYSTEM_INFO_CMD,
)
from .fake_panos import FIREWALL_SETS
from .fixture_map import NO_CAPTURE
from .helpers import interface_state, load_xml, make_instance, new_check

pytestmark = pytest.mark.unit

EVENT_TYPE = 'network-devices-metadata'
FW_A_STATIC_IP = '198.51.100.7'
FW_A_INTERFACE_CONFIG = FIXTURES / 'fw-a-probe' / 'config_running_interface.xml'
SYNTHETIC_INTERFACES = SYNTHETIC / 'interface_all_subinterfaces.xml'
SYNTHETIC_CONFIG = SYNTHETIC / 'config_running_interface_set.xml'
SYSTEM_INFO = parse_system_info(parse_response((FIXTURES / 'fw-a' / 'system_info.xml').read_bytes()))
NAMESPACE = 'default'


def interfaces_by_name(path, tunnel_states=None, config_path=None) -> dict:
    state = interface_state(path)
    state.tunnel_states = tunnel_states or {}
    if config_path is not None:
        state.interface_config = parse_interface_config(load_xml(config_path))
    return {i.name: i.model_dump(exclude_none=True) for i in build_interfaces(FW_A_SERIAL, state)}


def events(aggregator) -> list[dict]:
    return aggregator.get_event_platform_events(EVENT_TYPE)


def test_device_metadata_of_the_static_fw_a():
    target = FirewallTarget(ip=FW_A_STATIC_IP, credentials=Credentials(username='u', password='p', api_key=None))
    tags = global_tags(SYSTEM_INFO, target, NAMESPACE, ['team:test'])

    device = build_device(SYSTEM_INFO, FW_A_STATIC_IP, NAMESPACE, tags, can_connect=1, ha_state=None)

    assert device.model_dump(exclude_none=True) == {
        'integration': 'pan_firewall',
        'id': '007900000000001',
        'id_tags': ['device_namespace:default', 'device_id:007900000000001'],
        'tags': tags,
        'ip_address': FW_A_STATIC_IP,
        'status': 1,
        'name': 'fw-a',
        'model': 'PA-VM',
        'serial_number': '007900000000001',
        'version': '11.1.13-h12',
        'vendor': 'Palo Alto Networks',
        'os_name': 'PAN-OS',
        'device_type': 'firewall',
        'namespace': 'default',
    }


def test_interfaces_of_fw_a_capture():
    # The capture lists tunnel.1 (active) and tunnel.2 (init) once `vpn` has stored their state.
    by_name = interfaces_by_name(FW_A_INTERFACE_ALL, {'tunnel.1': 'active', 'tunnel.2': 'init'})

    assert by_name['ethernet1/1'] == {
        'integration': 'pan_firewall',
        'device_id': FW_A_SERIAL,
        'raw_id': 'ethernet1/1',
        'raw_id_type': 'name',
        'id_tags': ['interface:ethernet1/1'],
        'name': 'ethernet1/1',
        'index': 16,
        'mac_address': '02:00:00:00:01:01',
        'oper_status': 1,
    }
    # Only physical ports have a MAC.
    assert {n: (i['index'], i['oper_status'], i.get('mac_address')) for n, i in by_name.items()} == {
        'ethernet1/1': (16, 1, '02:00:00:00:01:01'),
        'ethernet1/2': (17, 1, '02:00:00:00:01:02'),
        'loopback': (3, 4, None),
        'loopback.1': (258, 4, None),
        'tunnel': (4, 1, None),
        'tunnel.1': (256, 1, None),
        'tunnel.2': (257, 2, None),
    }


def test_subinterfaces_inherit_the_parent_state_and_tunnels_use_the_vpn_state():
    by_name = interfaces_by_name(SYNTHETIC / 'interface_all_subinterfaces.xml', {'tunnel.3': 'inactive'})

    assert {n: i['oper_status'] for n, i in by_name.items()} == {
        'ethernet1/1': 1,
        'ethernet1/1.10': 1,
        'ethernet1/2.20': 2,
        'loopback.1': 4,
        'tunnel.3': 2,
        # No hw row and no parent: the state is unknown.
        'ae1': 4,
    }
    assert by_name['ethernet1/1.10']['index'] == 259
    assert 'mac_address' not in by_name['ethernet1/1.10']
    # A tunnel without a VPN entry is unknown.
    assert interfaces_by_name(SYNTHETIC / 'interface_all_subinterfaces.xml')['tunnel.3']['oper_status'] == 4


def test_admin_status_and_description_of_the_synthetic_set():
    by_name = interfaces_by_name(SYNTHETIC_INTERFACES, config_path=SYNTHETIC_CONFIG)

    assert {n: (i['admin_status'], i.get('description')) for n, i in by_name.items()} == {
        # link-state up is still enabled.
        'ethernet1/1': (1, 'Uplink & <ISP> — São Paulo'),
        'ethernet1/1.10': (1, 'Guest VLAN'),
        # The parent ethernet1/2 is link-state down.
        'ethernet1/2.20': (2, None),
        'loopback.1': (1, 'router-id'),
        'tunnel.3': (1, 'to DC2'),
        # An aggregate has no link-state.
        'ae1': (1, 'LACP to core'),
    }


def test_interfaces_of_fw_a_capture_with_its_config():
    by_name = interfaces_by_name(FW_A_INTERFACE_ALL, config_path=FW_A_INTERFACE_CONFIG)

    assert {n: i['admin_status'] for n, i in by_name.items()} == dict.fromkeys(INTERFACE_NAMES, 1)
    assert not any('description' in i for i in by_name.values())


def test_no_config_read_omits_admin_status_and_description():
    by_name = interfaces_by_name(FW_A_INTERFACE_ALL)

    assert not any({'admin_status', 'description'} & i.keys() for i in by_name.values())


# End to end, through the check.


def test_first_run_sends_the_device_and_its_interfaces(dd_run_check, aggregator, monkeypatch):
    monkeypatch.setitem(FIREWALL_SETS, FW_A_STATIC_IP, 'fw-a')

    dd_run_check(new_check(make_instance(ip=FW_A_STATIC_IP)))

    (event,) = events(aggregator)
    assert event['namespace'] == 'default'
    assert event['collect_timestamp'] > 0
    (device,) = event['devices']
    assert (device['id'], device['ip_address'], device['name'], device['status']) == (
        FW_A_SERIAL,
        FW_A_STATIC_IP,
        'fw-a',
        1,
    )
    assert len(event['interfaces']) == 7


HA_PAIR_ANSWERS = {
    HA_CMD: 'ha_all.xml',
    HA_INTERFACE_CMD.format(link='ha1'): 'ha_interface_ha1.xml',
    HA_INTERFACE_CMD.format(link='ha2'): 'ha_interface_ha2.xml',
}


def test_device_event_carries_the_ha_state_of_an_ha_firewall(dd_run_check, aggregator, fake_panos):
    for cmd, name in HA_PAIR_ANSWERS.items():
        fake_panos.answer_op(FW_A_IP, cmd, (200, (FIXTURES / 'fw-c' / name).read_bytes()))

    dd_run_check(new_check())

    (device,) = [device for event in events(aggregator) for device in event.get('devices', [])]
    assert 'ha_state:active' in device['tags']


def test_250_interfaces_are_sent_in_three_events(dd_run_check, aggregator, fake_panos):
    root = ET.fromstring(FW_A_INTERFACE_ALL.read_text())
    ifnet, template = root.find('./result/ifnet'), root.find('./result/ifnet/entry')
    for entry in list(ifnet):
        ifnet.remove(entry)
    for index in range(250):
        entry = copy.deepcopy(template)
        entry.find('name').text = f'ethernet1/{index}'
        ifnet.append(entry)
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, ET.tostring(root)))

    dd_run_check(new_check())

    sent = events(aggregator)
    assert len(sent) == 3
    assert all(len(e.get('devices', [])) + len(e.get('interfaces', [])) <= 100 for e in sent)
    assert sum(len(e.get('interfaces', [])) for e in sent) == 250
    assert all(e['namespace'] == 'default' and e['collect_timestamp'] for e in sent)


def test_metadata_is_sent_every_30_minutes(dd_run_check, aggregator, schedule_clock):
    check = new_check()
    dd_run_check(check)
    assert len(events(aggregator)) == 1

    schedule_clock.now += 1794
    dd_run_check(check)
    assert len(events(aggregator)) == 1

    schedule_clock.now += 1
    dd_run_check(check)
    assert len(events(aggregator)) == 2


def test_metadata_is_sent_at_once_when_the_firewall_comes_back(dd_run_check, aggregator, fake_panos, schedule_clock):
    check = new_check()
    dd_run_check(check)
    fake_panos.fail(FW_A_IP, 'refused')
    schedule_clock.now += 120
    dd_run_check(check)
    fake_panos.recover(FW_A_IP)
    schedule_clock.now += 120

    dd_run_check(check)

    assert [e['devices'][0]['status'] for e in events(aggregator)] == [1, 2, 1]


def test_disabled_metadata_sends_no_event_but_still_reads_the_identity(dd_run_check, aggregator, fake_panos):
    dd_run_check(new_check(make_instance(send_ndm_metadata=False)))

    assert events(aggregator) == []
    cmds = {c.cmd for c in fake_panos.calls}
    assert {SYSTEM_INFO_CMD, INTERFACE_ALL_CMD} <= cmds
    # The interface config only feeds the metadata, so it is not read without it.
    assert INTERFACE_CONFIG_CMD not in cmds


def test_static_firewall_never_reached_sends_no_metadata(dd_run_check, aggregator, fake_panos):
    fake_panos.fail(FW_A_IP, 'refused')
    check = new_check()

    dd_run_check(check)
    dd_run_check(check)

    assert events(aggregator) == []


def test_refused_interface_config_sends_interfaces_without_admin_status(dd_run_check, aggregator, fake_panos):
    # What fw-a answers a role without the permission, with the same HTTP 403.
    fake_panos.answer_op(
        FW_A_IP, INTERFACE_CONFIG_CMD, (403, (FIXTURES / 'fw-a-probe' / 'config_refused.xml').read_bytes())
    )

    dd_run_check(new_check())

    (event,) = events(aggregator)
    assert len(event['interfaces']) == 7
    assert all('admin_status' not in i and i['oper_status'] for i in event['interfaces'])
    # The refusal is not a rejected key: no renewal, and the authentication status stays OK.
    assert [c.type for c in fake_panos.calls].count('keygen') == 1
    (auth,) = aggregator.metrics('pan_firewall.api.authentication.status')
    assert auth.value == 0


def test_failed_interface_config_read_keeps_the_last_one(dd_run_check, aggregator, fake_panos, schedule_clock):
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, SYNTHETIC_INTERFACES.read_bytes()))
    fake_panos.answer_op(FW_A_IP, INTERFACE_CONFIG_CMD, (200, SYNTHETIC_CONFIG.read_bytes()))
    check = new_check()
    dd_run_check(check)
    fake_panos.answer_op(FW_A_IP, INTERFACE_CONFIG_CMD, (200, NO_CAPTURE))

    schedule_clock.now += 1800
    dd_run_check(check)

    assert len(events(aggregator)) == 2
    last = {i['name']: i for i in events(aggregator)[-1]['interfaces']}
    assert last['ethernet1/2.20']['admin_status'] == 2
