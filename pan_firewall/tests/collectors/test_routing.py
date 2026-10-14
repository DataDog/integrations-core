# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.routing import (
    BGP_PEER_CMD,
    OSPF_NEIGHBOR_CMD,
    collect_bgp,
    collect_ospf,
    parse_bgp_peers,
    parse_ospf_neighbors,
    peer_ip,
)

from ..common import FW_A_PEER, SYNTHETIC
from ..helpers import load_op, load_xml, make_ctx, series


def peer_samples(tags, *, status, duration, restart, updates, limit, prefixes=None):
    """The expected samples of one peer; `updates` is (in, out); `prefixes` maps a family tag to its four counters
    and utilization."""
    expected = {
        ('bgp.peer.status', tags): (status, 'gauge'),
        ('bgp.peer.status_duration', tags): (duration, 'gauge'),
        ('bgp.peer.restart', tags): (restart, 'gauge'),
        ('bgp.peer.updates.in', tags): (updates[0], 'monotonic_count'),
        ('bgp.peer.updates.out', tags): (updates[1], 'monotonic_count'),
        ('bgp.peer.prefix_limit', tags): (limit, 'gauge'),
    }
    names = ('incoming.total', 'incoming.rejected', 'outgoing.total', 'outgoing.advertised')
    for family, (counters, utilization) in (prefixes or {}).items():
        family_tags = (*tags, f'afi_safi:{family}')
        for name, value in zip(names, counters):
            expected[f'bgp.peer.prefixes.{name}', family_tags] = (value, 'gauge')
        expected['bgp.peer.prefix_limit.utilization', family_tags] = (utilization, 'gauge')
    return expected


FW_A_DEAD = ('peer:dead-peer', 'vr:default', 'peer_ip:10.60.1.250', 'remote_as:65099', 'peer_group:lab')
IPV4 = {'ipv4_unicast': ((1, 0, 1, 1), 10.0)}


def test_bgp_of_the_capture():
    samples = parse_bgp_peers(load_op(BGP_PEER_CMD))

    # The down peer reports zeros and its configured limit, and has no prefix family to report.
    down = peer_samples(FW_A_DEAD, status=0, duration=0, restart=0, updates=(0, 0), limit=5000)
    up = peer_samples(FW_A_PEER, status=1, duration=4856, restart=0, updates=(2, 2), limit=10, prefixes=IPV4)
    assert series(samples) == {**down, **up}


def test_bgp_established_peer_is_a_restart_within_30_minutes():
    root = load_op(BGP_PEER_CMD)
    for duration, restart in (('1799', 1), ('1800', 0)):
        root.find("result/entry[@peer='fw-peer']/status-duration").text = duration
        values = series(parse_bgp_peers(root))
        assert values['bgp.peer.restart', FW_A_PEER] == (restart, 'gauge')
    # A peer that is not Established has not come up, however short its time in the state.
    root.find("result/entry[@peer='fw-peer']/status").text = 'Active'
    root.find("result/entry[@peer='fw-peer']/status-duration").text = '5'
    values = series(parse_bgp_peers(root))
    assert values['bgp.peer.status', FW_A_PEER] == (0, 'gauge')
    assert values['bgp.peer.restart', FW_A_PEER] == (0, 'gauge')


def test_bgp_dual_stack_peer_reports_each_family_with_its_own_utilization():
    root = load_xml(SYNTHETIC / 'bgp_peer_dual_stack.xml')
    # Different in and out counts, so a swap shows.
    root.find("result/entry[@peer='fw-peer']/msg-update-out").text = '7'
    samples = parse_bgp_peers(root)

    tags = ('peer:fw-peer', 'vr:default', 'peer_ip:2001:db8::1', 'remote_as:65002', 'peer_group:lab')
    assert series(samples) == peer_samples(
        tags,
        status=1,
        duration=4856,
        restart=0,
        updates=(2, 7),
        limit=4,
        prefixes={'ipv4_unicast': ((1, 0, 1, 1), 25.0), 'ipv6_unicast': ((3, 1, 5, 4), 75.0)},
    )


@pytest.mark.parametrize('limit', ['0', None])
def test_bgp_utilization_is_not_sent_without_a_prefix_limit(limit):
    root = load_op(BGP_PEER_CMD)
    element = root.find("result/entry[@peer='fw-peer']/prefix-limit")
    if limit is None:
        root.find("result/entry[@peer='fw-peer']").remove(element)
    else:
        element.text = limit

    names = {s.name for s in parse_bgp_peers(root)}

    assert 'bgp.peer.prefix_limit.utilization' not in names
    assert 'bgp.peer.prefixes.incoming.total' in names


@pytest.mark.parametrize(
    'address, expected',
    [
        ('169.254.10.2:179', '169.254.10.2'),
        ('10.60.1.250', '10.60.1.250'),
        ('[2001:db8::1]:179', '2001:db8::1'),
        ('2001:db8::1', '2001:db8::1'),
        (None, None),
    ],
)
def test_peer_ip_strips_the_port_and_keeps_ipv6_intact(address, expected):
    assert peer_ip(address) == expected


def make_context(advanced_routing, state=None):
    return make_ctx(state=state, identity=mock.Mock(advanced_routing=advanced_routing))


COLLECTORS = [
    pytest.param(collect_bgp, BGP_PEER_CMD, id='bgp'),
    pytest.param(collect_ospf, OSPF_NEIGHBOR_CMD, id='ospf'),
]


@pytest.mark.parametrize('collect, _cmd', COLLECTORS)
def test_advanced_routing_engine_sends_no_call_and_warns_about_the_legacy_engine(collect, _cmd):
    ctx = make_context(True)

    assert collect(ctx) == []

    ctx.client.op.assert_not_called()
    ctx.log.warning.assert_called_once()
    assert 'legacy routing engine' in ctx.log.warning.call_args.args[0]


@pytest.mark.parametrize('collect, cmd', COLLECTORS)
@pytest.mark.parametrize('advanced_routing', [False, None])
def test_legacy_or_unknown_routing_engine_sends_the_legacy_call(collect, cmd, advanced_routing):
    ctx = make_context(advanced_routing)
    ctx.client.op.return_value = load_op(cmd)

    assert collect(ctx)
    ctx.client.op.assert_called_once_with(cmd)
    ctx.log.warning.assert_not_called()


FW_A_OSPF = ('neighbor:169.254.10.2', 'router_id:10.255.0.2', 'area:0.0.0.0', 'vr:default')


@pytest.mark.parametrize(
    'state, expected',
    [('full', 1), ('FULL', 1), ('2-way', 0)],
)
def test_ospf_neighbor_is_up_only_in_the_full_state(state, expected):
    root = load_op(OSPF_NEIGHBOR_CMD)
    root.find('result/entry/status').text = state

    # The state is the value; tagging it would split the series each time the neighbor changes state.
    assert series(parse_ospf_neighbors(root)) == {('ospf.neighbor.status', FW_A_OSPF): (expected, 'gauge')}


def test_ospf_neighbor_without_a_status_is_not_reported():
    root = load_op(OSPF_NEIGHBOR_CMD)
    entry = root.find('result/entry')
    entry.remove(entry.find('status'))

    assert parse_ospf_neighbors(root) == []
