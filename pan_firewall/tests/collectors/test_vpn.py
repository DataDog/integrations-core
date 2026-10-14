# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import threading
from unittest import mock

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, FirewallState
from datadog_checks.pan_firewall.collectors.vpn import VPN_FLOW_CMD, VPN_GATEWAY_CMD, collect_vpn, parse_vpn
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_TAGS, FW_A_TUNNEL
from ..helpers import load_op, make_ctx, new_check, series


def tunnel_tags(tunnel, interface, peer, gateway):
    return (
        f'tunnel:{tunnel}',
        f'tunnel_interface:{interface}',
        f'peer_ip:{peer}',
        f'gateway:{gateway}',
        'outer_interface:ethernet1/1',
    )


def expected(peer_ip, *, total=2, active=1, inactive=0, init=1, states=None):
    states = states or {'tun-peer': 1, 'tun-dead': 2}
    tags = {
        'tun-peer': tunnel_tags('tun-peer', 'tunnel.1', peer_ip, 'gw-peer'),
        'tun-dead': tunnel_tags('tun-dead', 'tunnel.2', '198.51.100.10', 'gw-dead'),
    }
    result = {
        ('ipsec.tunnels.total', ()): (total, 'gauge'),
        ('ipsec.tunnels.active', ()): (active, 'gauge'),
        ('ipsec.tunnels.inactive', ()): (inactive, 'gauge'),
        ('ipsec.tunnels.init', ()): (init, 'gauge'),
        ('ipsec.gateways.total', ()): (2, 'gauge'),
    }
    for name, value in states.items():
        result['ipsec.tunnel.state', tags[name]] = (value, 'gauge')
    return result


def test_vpn_of_the_capture():
    peer_ip = '10.60.1.11'
    snapshot = parse_vpn(load_op(VPN_FLOW_CMD), load_op(VPN_GATEWAY_CMD), mock.Mock())

    assert series(snapshot.samples) == expected(peer_ip)
    assert snapshot.tunnel_states == {'tunnel.1': 'active', 'tunnel.2': 'init'}
    assert snapshot.tunnel_tags == {
        'tunnel.1': tunnel_tags('tun-peer', 'tunnel.1', peer_ip, 'gw-peer'),
        'tunnel.2': tunnel_tags('tun-dead', 'tunnel.2', '198.51.100.10', 'gw-dead'),
    }


def test_unknown_state_is_skipped_and_logged_but_still_counts_in_the_total():
    flow = load_op(VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-peer']/state").text = 'weird'
    log = mock.Mock()

    snapshot = parse_vpn(flow, load_op(VPN_GATEWAY_CMD), log)

    assert series(snapshot.samples) == expected('10.60.1.11', active=0, states={'tun-dead': 2})
    log.warning.assert_called_once()
    assert 'weird' in str(log.warning.call_args)


def test_gateway_tag_is_omitted_when_gwid_matches_no_gateway():
    flow = load_op(VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-peer']/gwid").text = '99'

    snapshot = parse_vpn(flow, load_op(VPN_GATEWAY_CMD), mock.Mock())

    assert snapshot.tunnel_tags['tunnel.1'] == (
        'tunnel:tun-peer',
        'tunnel_interface:tunnel.1',
        'peer_ip:10.60.1.11',
        'outer_interface:ethernet1/1',
    )


def test_gateway_total_counts_gateways_without_an_id_or_a_name():
    gateway = load_op(VPN_GATEWAY_CMD)
    entries = gateway.findall('./result/entries/entry')
    entries[0].remove(entries[0].find('id'))
    entries[1].remove(entries[1].find('name'))

    snapshot = parse_vpn(load_op(VPN_FLOW_CMD), gateway, mock.Mock())

    assert series(snapshot.samples)[('ipsec.gateways.total', ())] == (len(entries), 'gauge')


def test_vpn_answer_without_result_keeps_the_stored_tunnels():
    tags = {'tunnel.1': ('tunnel:tun-peer', 'tunnel_interface:tunnel.1')}
    state = FirewallState(tunnel_tags=dict(tags), tunnel_states={'tunnel.1': 'active'})
    ctx = make_ctx(parse_response(b'<response status="success"/>'), state=state)

    assert collect_vpn(ctx) == []

    assert (state.tunnel_tags, state.tunnel_states) == (tags, {'tunnel.1': 'active'})


def test_tunnel_counters_wait_for_the_run_after_vpn_first_answers_whatever_the_collector_order(
    real_collectors,
    dd_run_check,
    aggregator,
    monkeypatch,
    schedule_clock,
):
    vpn_done = threading.Event()
    real_vpn, real_interfaces = COLLECT_FUNCTIONS['vpn'], COLLECT_FUNCTIONS['interfaces']

    def vpn_then_signal(ctx):
        try:
            return real_vpn(ctx)
        finally:
            vpn_done.set()

    def interfaces_after_vpn(ctx):
        assert vpn_done.wait(10)
        return real_interfaces(ctx)

    monkeypatch.setitem(COLLECT_FUNCTIONS, 'vpn', vpn_then_signal)
    monkeypatch.setitem(COLLECT_FUNCTIONS, 'interfaces', interfaces_after_vpn)
    check = new_check()

    dd_run_check(check)
    assert aggregator.metrics('pan_firewall.ipsec.tunnel.rx.bytes') == []

    schedule_clock.now += 180
    dd_run_check(check)
    full_tags = sorted([*FW_A_TAGS, *FW_A_TUNNEL])
    aggregator.assert_metric(
        'pan_firewall.ipsec.tunnel.rx.bytes', 1563183, tags=full_tags, metric_type=aggregator.MONOTONIC_COUNT
    )
