# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.interfaces import COUNTER_INTERFACE_CMD, collect_interfaces
from datadog_checks.pan_firewall.collectors.vpn import VPN_FLOW_CMD, VPN_GATEWAY_CMD, collect_vpn, parse_vpn
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..fixture_map import op_fixture
from ..test_check import FW_A_TAGS, new_check


def load(firewall, cmd):
    return parse_response(op_fixture(cmd, firewall).read_bytes())


def series(samples):
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


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


@pytest.mark.parametrize('firewall, peer_ip', [('fw-a', '10.60.1.11'), ('fw-b', '10.60.1.10')])
def test_vpn_of_the_captures(firewall, peer_ip):
    snapshot = parse_vpn(load(firewall, VPN_FLOW_CMD), load(firewall, VPN_GATEWAY_CMD), mock.Mock())

    assert series(snapshot.samples) == expected(peer_ip)
    assert snapshot.tunnel_states == {'tunnel.1': 'active', 'tunnel.2': 'init'}
    assert snapshot.tunnel_tags == {
        'tunnel.1': tunnel_tags('tun-peer', 'tunnel.1', peer_ip, 'gw-peer'),
        'tunnel.2': tunnel_tags('tun-dead', 'tunnel.2', '198.51.100.10', 'gw-dead'),
    }


def test_unknown_state_is_skipped_and_logged_but_still_counts_in_the_total():
    flow = load('fw-a', VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-peer']/state").text = 'weird'
    log = mock.Mock()

    snapshot = parse_vpn(flow, load('fw-a', VPN_GATEWAY_CMD), log)

    assert series(snapshot.samples) == expected('10.60.1.11', active=0, states={'tun-dead': 2})
    log.warning.assert_called_once()
    assert 'weird' in str(log.warning.call_args)


def test_inactive_state_is_zero():
    flow = load('fw-a', VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-dead']/state").text = 'inactive'

    snapshot = parse_vpn(flow, load('fw-a', VPN_GATEWAY_CMD), mock.Mock())

    assert series(snapshot.samples) == expected('10.60.1.11', init=0, inactive=1, states={'tun-peer': 1, 'tun-dead': 0})


def test_gateway_tag_is_omitted_when_gwid_matches_no_gateway():
    flow = load('fw-a', VPN_FLOW_CMD)
    flow.find("result/IPSec/entry[name='tun-peer']/gwid").text = '99'

    snapshot = parse_vpn(flow, load('fw-a', VPN_GATEWAY_CMD), mock.Mock())

    assert snapshot.tunnel_tags['tunnel.1'] == (
        'tunnel:tun-peer',
        'tunnel_interface:tunnel.1',
        'peer_ip:10.60.1.11',
        'outer_interface:ethernet1/1',
    )


def test_unknown_shape_warns_and_sends_nothing():
    log = mock.Mock()
    empty = parse_response(b'<response status="success"/>')

    snapshot = parse_vpn(empty, load('fw-a', VPN_GATEWAY_CMD), log)

    assert snapshot.samples == []
    log.warning.assert_called_once()


def make_context(state, responses):
    ctx = CollectContext(
        client=mock.Mock(),
        identity=mock.Mock(serial='007955000930601'),
        state=state,
        config=mock.Mock(),
        log=mock.Mock(),
    )
    ctx.client.op.side_effect = lambda cmd: responses[cmd]
    return ctx


def test_collector_stores_tunnel_tags_and_states_and_interfaces_uses_them_on_the_next_run():
    state = FirewallState()
    responses = {
        VPN_FLOW_CMD: load('fw-a', VPN_FLOW_CMD),
        VPN_GATEWAY_CMD: load('fw-a', VPN_GATEWAY_CMD),
        COUNTER_INTERFACE_CMD: load('fw-a', COUNTER_INTERFACE_CMD),
    }
    ctx = make_context(state, responses)

    collect_vpn(ctx)
    samples = collect_interfaces(ctx)

    assert [c.args[0] for c in ctx.client.op.call_args_list] == [VPN_FLOW_CMD, VPN_GATEWAY_CMD, COUNTER_INTERFACE_CMD]
    assert state.tunnel_states == {'tunnel.1': 'active', 'tunnel.2': 'init'}
    rx = {s.tags: s.value for s in samples if s.name == 'ipsec.tunnel.rx.bytes'}
    assert rx == {
        tunnel_tags('tun-peer', 'tunnel.1', '10.60.1.11', 'gw-peer'): 1563183,
        tunnel_tags('tun-dead', 'tunnel.2', '198.51.100.10', 'gw-dead'): 0,
    }


def test_failed_vpn_call_keeps_the_stored_tunnels():
    state = FirewallState(tunnel_states={'tunnel.1': 'active'})
    ctx = make_context(state, {})

    with pytest.raises(KeyError):
        collect_vpn(ctx)

    assert state.tunnel_states == {'tunnel.1': 'active'}


def test_vpn_is_registered_and_submits_through_the_check(real_collectors, dd_run_check, aggregator, fake_panos):
    assert 'vpn' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    gauge, monotonic = aggregator.GAUGE, aggregator.MONOTONIC_COUNT
    for name, value in (('total', 2), ('active', 1), ('inactive', 0), ('init', 1)):
        aggregator.assert_metric(f'pan_firewall.ipsec.tunnels.{name}', value, tags=FW_A_TAGS, metric_type=gauge)
    aggregator.assert_metric('pan_firewall.ipsec.gateways.total', 2, tags=FW_A_TAGS, metric_type=gauge)
    aggregator.assert_metric(
        'pan_firewall.ipsec.tunnel.state',
        1,
        tags=sorted([*FW_A_TAGS, *tunnel_tags('tun-peer', 'tunnel.1', '10.60.1.11', 'gw-peer')]),
        metric_type=gauge,
    )
    # `interfaces` and `vpn` run in parallel, so the first run may carry the tunnel interface tag only.
    rx = aggregator.metrics('pan_firewall.ipsec.tunnel.rx.bytes')
    assert sorted(m.value for m in rx) == [0, 1563183]
    assert all(m.type == monotonic for m in rx)
    assert sum('tunnel_interface:tunnel.1' in m.tags for m in rx) == 1
    # One `counter interface all` call serves the interfaces and the tunnels.
    assert [c.cmd for c in fake_panos.calls if c.cmd == COUNTER_INTERFACE_CMD] == [COUNTER_INTERFACE_CMD]
