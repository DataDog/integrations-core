# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

from datadog_checks.pan_firewall.collectors import FirewallState
from datadog_checks.pan_firewall.collectors.interfaces import (
    COUNTER_INTERFACE_CMD,
    parse_interface_counters,
    parse_interface_speeds,
)

from ..common import FW_A_INTERFACE_ALL, FW_A_IP, FW_A_SERIAL, FW_A_TAGS, INTERFACE_ALL_CMD, INTERFACE_NAMES, SYNTHETIC
from ..helpers import interface_state, load_op, new_check, series

COUNTER_FIELDS = {
    'ibytes': 'interface.rx.bytes',
    'obytes': 'interface.tx.bytes',
    'ipackets': 'interface.rx.packets',
    'opackets': 'interface.tx.packets',
    'ierrors': 'interface.rx.errors',
    'idrops': 'interface.rx.drops',
    'ifwderrors': 'interface.forward_errors',
    'flowstate': 'interface.flow_state',
    'land': 'interface.attack.land',
    'pod': 'interface.attack.ping_of_death',
    'teardrop': 'interface.attack.teardrop',
    'ipspoof': 'interface.attack.ip_spoof',
    'macspoof': 'interface.attack.mac_spoof',
}
ZERO = dict.fromkeys(COUNTER_FIELDS, 0)
# Values of the `ifnet/ifnet/entry` rows of the capture, in COUNTER_FIELDS order.
FW_A_ROWS = {
    **dict.fromkeys(INTERFACE_NAMES, (0,) * 13),
    'ethernet1/1': (153738451, 3120586, 119008, 30547, 0, 0, 0, 3, 0, 0, 0, 0, 0),
    'ethernet1/2': (2213914, 152466233, 25062, 110271, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'tunnel.1': (1563183, 919234, 11275, 5157, 0, 0, 0, 0, 0, 0, 0, 0, 0),
}
FW_A_TUNNELS = {'tunnel.1': (1563183, 919234, 11275, 5157), 'tunnel.2': (0, 0, 0, 0)}
# interface, interface_type, zone, vsys, vr
MAP_TAGS = {
    'ethernet1/1': ('interface:ethernet1/1', 'interface_type:ethernet', 'zone:untrust', 'vsys:vsys1', 'vr:default'),
    'ethernet1/2': ('interface:ethernet1/2', 'interface_type:ethernet', 'zone:trust', 'vsys:vsys1', 'vr:default'),
    'loopback': ('interface:loopback', 'interface_type:loopback', 'vsys:vsys1'),
    'loopback.1': ('interface:loopback.1', 'interface_type:loopback', 'zone:trust', 'vsys:vsys1', 'vr:default'),
    'tunnel': ('interface:tunnel', 'interface_type:tunnel', 'vsys:vsys1'),
    'tunnel.1': ('interface:tunnel.1', 'interface_type:tunnel', 'zone:vpn', 'vsys:vsys1', 'vr:default'),
    'tunnel.2': ('interface:tunnel.2', 'interface_type:tunnel', 'zone:vpn', 'vsys:vsys1', 'vr:default'),
}


def resource_tag(name):
    # Same shape as hpe_aruba_edgeconnect: the device id only, the `interface` tag identifies the port.
    return f'dd.internal.resource:ndm_interface:{FW_A_SERIAL}'


def expected_interfaces(rows, tags_of):
    expected = {}
    for name, values in rows.items():
        for metric, value in zip(COUNTER_FIELDS.values(), values):
            expected[metric, tags_of(name)] = (value, 'monotonic_count')
    return expected


def with_map_tags(name):
    return (*MAP_TAGS[name], resource_tag(name))


def test_interface_counters_with_the_interface_map():
    state = interface_state(FW_A_INTERFACE_ALL)
    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), state, FW_A_SERIAL, None, mock.Mock())

    interface_samples = [s for s in samples if s.name.startswith('interface.')]
    assert series(interface_samples) == expected_interfaces(FW_A_ROWS, with_map_tags)


def test_interface_counters_without_a_map_carry_the_interface_tag_only():
    # Without `show interface all` (fw-b has no capture of it, ruling R7) the state holds no interface map.
    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), FirewallState(), FW_A_SERIAL, None, mock.Mock())

    assert series(samples) == expected_interfaces(FW_A_ROWS, lambda name: (f'interface:{name}',))


def test_interface_without_an_ifnet_row_gets_the_type_and_the_resource_tag():
    state = interface_state(FW_A_INTERFACE_ALL)
    state.interface_rows = [r for r in state.interface_rows if r.findtext('name') != 'ethernet1/2']

    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), state, FW_A_SERIAL, None, mock.Mock())

    tags = {s.tags for s in samples if s.name == 'interface.rx.bytes' and 'interface:ethernet1/2' in s.tags}
    assert tags == {('interface:ethernet1/2', 'interface_type:ethernet', resource_tag('ethernet1/2'))}


def test_resource_tag_is_omitted_without_a_serial():
    state = interface_state(FW_A_INTERFACE_ALL)

    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), state, None, None, mock.Mock())

    assert not any('dd.internal.resource' in t for s in samples for t in s.tags)


def tunnel_tags(name):
    return (f'tunnel:tun-{name}', f'tunnel_interface:{name}', 'peer_ip:10.0.0.1', 'gateway:gw', 'outer_interface:e1')


def test_tunnel_rows_become_ipsec_counters_with_the_tags_vpn_stored():
    known = {name: tunnel_tags(name) for name in FW_A_TUNNELS}

    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), FirewallState(), FW_A_SERIAL, known, mock.Mock())

    ipsec = [s for s in samples if s.name.startswith('ipsec.')]
    expected = {}
    for name, values in FW_A_TUNNELS.items():
        for metric, value in zip(
            ('ipsec.tunnel.rx.bytes', 'ipsec.tunnel.tx.bytes', 'ipsec.tunnel.rx.packets', 'ipsec.tunnel.tx.packets'),
            values,
        ):
            expected[metric, tunnel_tags(name)] = (value, 'monotonic_count')
    assert series(ipsec) == expected
    # The same rows are also interfaces, tunnels included.
    assert {s.tags[0] for s in samples if s.name == 'interface.rx.bytes'} >= {
        'interface:tunnel.1',
        'interface:tunnel.2',
    }

    # A tunnel row that `vpn` does not list is not an IPsec tunnel.
    samples = parse_interface_counters(
        load_op(COUNTER_INTERFACE_CMD),
        FirewallState(),
        FW_A_SERIAL,
        {'tunnel.1': tunnel_tags('tunnel.1')},
        mock.Mock(),
    )

    assert {s.tags for s in samples if s.name == 'ipsec.tunnel.rx.bytes'} == {tunnel_tags('tunnel.1')}


def test_speeds_of_the_capture_are_not_sent():
    state = interface_state(FW_A_INTERFACE_ALL)

    assert parse_interface_speeds(state, FW_A_SERIAL, mock.Mock()) == []


def test_speed_is_megabits_converted_to_bits_and_unparseable_is_logged():
    state = interface_state(SYNTHETIC / 'interface_all_speeds.xml')
    log = mock.Mock()

    samples = parse_interface_speeds(state, FW_A_SERIAL, log)

    assert series(samples) == {
        ('interface.speed', with_map_tags('ethernet1/1')): (1e9, 'gauge'),
        ('interface.speed', with_map_tags('ethernet1/2')): (1e10, 'gauge'),
    }
    log.debug.assert_called_once()
    assert 'fast' in str(log.debug.call_args)


def test_speeds_are_sent_as_gauges_every_30_minutes_with_the_identity_not_every_3(
    dd_run_check,
    aggregator,
    fake_panos,
    monkeypatch,
    schedule_clock,
):
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, (SYNTHETIC / 'interface_all_speeds.xml').read_bytes()))
    check = new_check()

    sent = []
    for seconds in (0, 180, 1799, 1800):
        schedule_clock.now = 1000.0 + seconds
        before = len(aggregator.metrics('pan_firewall.interface.speed'))
        dd_run_check(check)
        sent.append(len(aggregator.metrics('pan_firewall.interface.speed')) - before)

    # Two interfaces report a speed: sent on the first run and on the 30-minute run only.
    assert sent == [2, 0, 0, 2]
    for name, speed in (('ethernet1/1', 1e9), ('ethernet1/2', 1e10)):
        aggregator.assert_metric(
            'pan_firewall.interface.speed',
            speed,
            tags=sorted([*FW_A_TAGS, *with_map_tags(name)]),
            metric_type=aggregator.GAUGE,
        )
