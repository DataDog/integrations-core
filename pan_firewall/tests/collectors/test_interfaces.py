# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.interfaces import (
    COUNTER_INTERFACE_CMD,
    INTERFACE_METRICS,
    TUNNEL_METRICS,
    interface_tags,
    parse_interface_counters,
    parse_interface_speeds,
)

from ..common import (
    FW_A_INTERFACE_ALL,
    FW_A_IP,
    FW_A_SERIAL,
    FW_A_TAGS,
    FW_A_TUNNEL,
    INTERFACE_ALL_CMD,
    INTERFACE_NAMES,
    SYNTHETIC,
)
from ..helpers import interface_state, load_op, new_check, series

pytestmark = pytest.mark.unit

SPEEDS = SYNTHETIC / 'interface_all_speeds.xml'
# The device id only: the `interface` tag identifies the port (same shape as hpe_aruba_edgeconnect).
RESOURCE_TAG = f'dd.internal.resource:ndm_interface:{FW_A_SERIAL}'
# Values of the `ifnet/ifnet/entry` rows of the capture, in INTERFACE_METRICS order.
FW_A_ROWS = {
    **dict.fromkeys(INTERFACE_NAMES, (0,) * 13),
    'ethernet1/1': (153738451, 3120586, 119008, 30547, 0, 0, 0, 3, 0, 0, 0, 0, 0),
    'ethernet1/2': (2213914, 152466233, 25062, 110271, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    'tunnel.1': (1563183, 919234, 11275, 5157, 0, 0, 0, 0, 0, 0, 0, 0, 0),
}
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


def with_map_tags(name):
    return (*MAP_TAGS[name], RESOURCE_TAG)


def test_interface_counters_of_the_capture():
    state = interface_state(FW_A_INTERFACE_ALL)

    samples = parse_interface_counters(load_op(COUNTER_INTERFACE_CMD), state, FW_A_SERIAL, None, mock.Mock())

    assert series(samples) == {
        (metric, with_map_tags(name)): (value, 'monotonic_count')
        for name, values in FW_A_ROWS.items()
        for metric, value in zip(INTERFACE_METRICS.values(), values)
    }


@pytest.mark.parametrize(
    'state, serial, tags',
    [
        pytest.param(FirewallState(), FW_A_SERIAL, ('interface:ethernet1/1',), id='without-show-interface-all'),
        pytest.param(
            FirewallState(interface_map={}),
            FW_A_SERIAL,
            ('interface:ethernet1/1', 'interface_type:ethernet', RESOURCE_TAG),
            id='without-an-ifnet-row',
        ),
        pytest.param(interface_state(FW_A_INTERFACE_ALL), None, MAP_TAGS['ethernet1/1'], id='without-a-serial'),
    ],
)
def test_interface_tags(state, serial, tags):
    assert interface_tags('ethernet1/1', state, serial) == tags


def test_tunnel_rows_vpn_listed_are_ipsec_counters():
    # `tunnel.2` is a tunnel row too, but `vpn` did not list it.
    tunnel_tags = {'tunnel.1': FW_A_TUNNEL}

    samples = parse_interface_counters(
        load_op(COUNTER_INTERFACE_CMD), FirewallState(), FW_A_SERIAL, tunnel_tags, mock.Mock()
    )

    assert series([s for s in samples if s.name.startswith('ipsec.')]) == {
        (metric, FW_A_TUNNEL): (value, 'monotonic_count')
        for metric, value in zip(TUNNEL_METRICS.values(), FW_A_ROWS['tunnel.1'])
    }


@pytest.mark.parametrize(
    'path, speeds',
    [
        pytest.param(FW_A_INTERFACE_ALL, {}, id='unknown-and-not-applicable'),
        pytest.param(SPEEDS, {'ethernet1/1': 1e9, 'ethernet1/2': 1e10}, id='megabits-and-unparseable'),
    ],
)
def test_interface_speeds(path, speeds):
    samples = parse_interface_speeds(interface_state(path), FW_A_SERIAL, mock.Mock())

    assert series(samples) == {('interface.speed', with_map_tags(n)): (s, 'gauge') for n, s in speeds.items()}


def test_speeds_are_sent_with_the_identity_every_30_minutes(dd_run_check, aggregator, fake_panos, schedule_clock):
    fake_panos.answer_op(FW_A_IP, INTERFACE_ALL_CMD, (200, SPEEDS.read_bytes()))
    check = new_check()
    start = schedule_clock.now

    sent = []
    for seconds in (0, 1799, 1800):
        schedule_clock.now = start + seconds
        before = len(aggregator.metrics('pan_firewall.interface.speed'))
        dd_run_check(check)
        sent.append(len(aggregator.metrics('pan_firewall.interface.speed')) - before)

    # Two interfaces have a speed; the interfaces collector runs in between and does not send them.
    assert sent == [2, 0, 2]
    aggregator.assert_metric(
        'pan_firewall.interface.speed', 1e9, tags=sorted([*FW_A_TAGS, *with_map_tags('ethernet1/1')])
    )
