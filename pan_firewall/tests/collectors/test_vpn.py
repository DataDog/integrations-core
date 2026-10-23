# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
from unittest import mock
from xml.etree.ElementTree import Element

import pytest

from datadog_checks.pan_firewall.collectors import COLLECTORS
from datadog_checks.pan_firewall.collectors.base import FirewallState
from datadog_checks.pan_firewall.collectors.vpn import VPN_FLOW_CMD, VPN_GATEWAY_CMD, collect_vpn, parse_vpn
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_TAGS, FW_A_TUNNEL
from ..helpers import load_op, make_ctx, new_check, series

pytestmark = pytest.mark.unit

FW_A_DEAD_TUNNEL = (
    'tunnel:tun-dead',
    'tunnel_interface:tunnel.2',
    'peer_ip:198.51.100.10',
    'gateway:gw-dead',
    'outer_interface:ethernet1/1',
)
FW_A_VPN = {
    ('ipsec.tunnels.total', ()): (2, 'gauge'),
    ('ipsec.tunnels.active', ()): (1, 'gauge'),
    ('ipsec.tunnels.inactive', ()): (0, 'gauge'),
    ('ipsec.tunnels.init', ()): (1, 'gauge'),
    ('ipsec.gateways.total', ()): (2, 'gauge'),
    ('ipsec.tunnel.state', FW_A_TUNNEL): (1, 'gauge'),
    ('ipsec.tunnel.state', FW_A_DEAD_TUNNEL): (2, 'gauge'),
}


def test_vpn_of_the_capture():
    snapshot = parse_vpn(load_op(VPN_FLOW_CMD), load_op(VPN_GATEWAY_CMD), mock.Mock())

    assert series(snapshot.samples) == FW_A_VPN
    assert snapshot.tunnel_states == {'tunnel.1': 'active', 'tunnel.2': 'init'}
    assert snapshot.tunnel_tags == {'tunnel.1': FW_A_TUNNEL, 'tunnel.2': FW_A_DEAD_TUNNEL}


def _flow(*tunnels: tuple[str, str, str, str]) -> Element:
    entries = ''.join(
        f'<entry><name>{name}</name><gwid>1</gwid><inner-if>{inner}</inner-if><outer-if>{outer}</outer-if>'
        f'<peerip>10.20.1.{i}</peerip><state>{state}</state></entry>'
        for i, (name, inner, outer, state) in enumerate(tunnels, 1)
    )
    return parse_response(f'<response status="success"><result><IPSec>{entries}</IPSec></result></response>'.encode())


@pytest.mark.parametrize(
    'tunnels, expected_tags, expected_states',
    [
        pytest.param(
            (
                ('tun-a', 'tunnel.1', 'ethernet1/1', 'init'),
                ('tun-b', 'tunnel.1', 'ethernet1/1', 'active'),
                ('tun-c', 'tunnel.2', 'ethernet1/2', 'inactive'),
            ),
            {
                'tunnel.1': ('tunnel_interface:tunnel.1', 'outer_interface:ethernet1/1'),
                'tunnel.2': (
                    'tunnel:tun-c',
                    'tunnel_interface:tunnel.2',
                    'peer_ip:10.20.1.3',
                    'gateway:gw-peer',
                    'outer_interface:ethernet1/2',
                ),
            },
            {'tunnel.1': 'active', 'tunnel.2': 'inactive'},
            id='shared-interface-is-up-if-any-tunnel-is-active',
        ),
        pytest.param(
            (
                ('tun-a', 'tunnel.1', 'ethernet1/1', 'inactive'),
                ('tun-b', 'tunnel.1', 'ethernet1/2', 'init'),
            ),
            {'tunnel.1': ('tunnel_interface:tunnel.1',)},
            {'tunnel.1': 'init'},
            id='shared-interface-with-different-outer-interfaces-has-no-outer-tag',
        ),
        pytest.param(
            (
                ('tun-a', 'tunnel.1', 'ethernet1/1', 'weird'),
                ('tun-b', 'tunnel.1', 'ethernet1/1', 'inactive'),
            ),
            {'tunnel.1': ('tunnel_interface:tunnel.1', 'outer_interface:ethernet1/1')},
            {'tunnel.1': 'inactive'},
            id='unknown-state-ranks-below-the-known-ones',
        ),
    ],
)
def test_tunnels_sharing_an_interface_are_tagged_and_stated_per_interface(tunnels, expected_tags, expected_states):
    snapshot = parse_vpn(_flow(*tunnels), load_op(VPN_GATEWAY_CMD), mock.Mock())

    assert snapshot.tunnel_tags == expected_tags
    assert snapshot.tunnel_states == expected_states
    # Each flow entry still reports its own state.
    assert sum(1 for name, _ in series(snapshot.samples) if name == 'ipsec.tunnel.state') == len(
        {n for n in tunnels if n[3] != 'weird'}
    )


def test_unknown_state_is_skipped_but_still_counts_in_the_total():
    flow = load_op(VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-peer']/state").text = 'weird'

    snapshot = parse_vpn(flow, load_op(VPN_GATEWAY_CMD), mock.Mock())

    expected = {**FW_A_VPN, ('ipsec.tunnels.active', ()): (0, 'gauge')}
    del expected['ipsec.tunnel.state', FW_A_TUNNEL]
    assert series(snapshot.samples) == expected


def test_gateway_without_an_id_counts_in_the_total_but_tags_no_tunnel():
    gateway = load_op(VPN_GATEWAY_CMD)
    entry = gateway.find("result/entries/entry[name='gw-peer']")
    entry.remove(entry.find('id'))

    snapshot = parse_vpn(load_op(VPN_FLOW_CMD), gateway, mock.Mock())

    assert series(snapshot.samples)['ipsec.gateways.total', ()] == (2, 'gauge')
    assert snapshot.tunnel_tags['tunnel.1'] == tuple(t for t in FW_A_TUNNEL if not t.startswith('gateway:'))


def test_vpn_answer_without_result_keeps_the_stored_tunnels():
    state = FirewallState(tunnel_tags={'tunnel.1': FW_A_TUNNEL}, tunnel_states={'tunnel.1': 'active'})
    ctx = make_ctx(parse_response(b'<response status="success"/>'), state=state)

    assert collect_vpn(ctx) == []

    assert (state.tunnel_tags, state.tunnel_states) == ({'tunnel.1': FW_A_TUNNEL}, {'tunnel.1': 'active'})


def test_tunnel_counters_wait_for_the_run_after_vpn_first_answers_whatever_the_collector_order(
    dd_run_check, aggregator, monkeypatch, schedule_clock
):
    # Force the worst order: `interfaces` reads the tunnel tags only after `vpn` has stored them in this run.
    vpn_done = threading.Event()
    real_vpn, real_interfaces = COLLECTORS['vpn'], COLLECTORS['interfaces']

    def vpn_then_signal(ctx):
        try:
            return real_vpn(ctx)
        finally:
            vpn_done.set()

    def interfaces_after_vpn(ctx):
        assert vpn_done.wait(10)
        return real_interfaces(ctx)

    monkeypatch.setitem(COLLECTORS, 'vpn', vpn_then_signal)
    monkeypatch.setitem(COLLECTORS, 'interfaces', interfaces_after_vpn)
    check = new_check()

    dd_run_check(check)
    assert aggregator.metrics('pan_firewall.ipsec.tunnel.rx.bytes') == []

    schedule_clock.now += 180
    dd_run_check(check)
    aggregator.assert_metric('pan_firewall.ipsec.tunnel.rx.bytes', 1563183, tags=sorted([*FW_A_TAGS, *FW_A_TUNNEL]))
