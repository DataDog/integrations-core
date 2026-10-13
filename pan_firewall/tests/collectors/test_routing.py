# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.routing import BGP_PEER_CMD, collect_bgp, parse_bgp_peers, peer_ip
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..fixture_map import op_fixture
from ..test_check import FW_A_TAGS, new_check

SYNTHETIC = FIXTURES / 'synthetic'


def load(path):
    return parse_response(path.read_bytes())


def series(samples):
    """Samples keyed by (name, tags) to (value, kind); fails on a duplicate (two values for one series)."""
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def peer_samples(tags, *, status, duration, restart, updates, limit, prefixes=None):
    """The expected samples of one peer; `prefixes` maps a family tag to its four counters and utilization."""
    expected = {
        ('bgp.peer.status', tags): (status, 'gauge'),
        ('bgp.peer.status_duration', tags): (duration, 'gauge'),
        ('bgp.peer.restart', tags): (restart, 'gauge'),
        ('bgp.peer.updates.in', tags): (updates, 'monotonic_count'),
        ('bgp.peer.updates.out', tags): (updates, 'monotonic_count'),
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
FW_A_PEER = ('peer:fw-peer', 'vr:default', 'peer_ip:169.254.10.2', 'remote_as:65002', 'peer_group:lab')
FW_B_DEAD = FW_A_DEAD
FW_B_PEER = ('peer:fw-peer', 'vr:default', 'peer_ip:169.254.10.1', 'remote_as:65001', 'peer_group:lab')
IPV4 = {'ipv4_unicast': ((1, 0, 1, 1), 10.0)}


@pytest.mark.parametrize(
    'firewall, peer, dead',
    [('fw-a', FW_A_PEER, FW_A_DEAD), ('fw-b', FW_B_PEER, FW_B_DEAD)],
)
def test_bgp_of_the_captures(firewall, peer, dead):
    samples = parse_bgp_peers(load(op_fixture(BGP_PEER_CMD, firewall)))

    # The down peer reports zeros and its configured limit, and has no prefix family to report.
    down = peer_samples(dead, status=0, duration=0, restart=0, updates=0, limit=5000)
    up = peer_samples(
        peer,
        status=1,
        duration=4856 if firewall == 'fw-a' else 4878,
        restart=0,
        updates=2,
        limit=10,
        prefixes=IPV4,
    )
    assert series(samples) == {**down, **up}


def test_bgp_established_peer_is_a_restart_within_30_minutes():
    root = load(op_fixture(BGP_PEER_CMD))
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
    samples = parse_bgp_peers(load(SYNTHETIC / 'bgp_peer_dual_stack.xml'))

    tags = ('peer:fw-peer', 'vr:default', 'peer_ip:2001:db8::1', 'remote_as:65002', 'peer_group:lab')
    assert series(samples) == peer_samples(
        tags,
        status=1,
        duration=4856,
        restart=0,
        updates=2,
        limit=4,
        prefixes={'ipv4_unicast': ((1, 0, 1, 1), 25.0), 'ipv6_unicast': ((3, 1, 5, 4), 75.0)},
    )


@pytest.mark.parametrize('limit', ['0', None])
def test_bgp_utilization_is_not_sent_without_a_prefix_limit(limit):
    root = load(op_fixture(BGP_PEER_CMD))
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
        ('169.254.10.1:41785', '169.254.10.1'),
        ('10.60.1.250', '10.60.1.250'),
        ('[2001:db8::1]:179', '2001:db8::1'),
        ('2001:db8::1', '2001:db8::1'),
        ('', None),
        (None, None),
    ],
)
def test_peer_ip_strips_the_port_and_keeps_ipv6_intact(address, expected):
    assert peer_ip(address) == expected


def make_context(advanced_routing, state=None):
    return CollectContext(
        client=mock.Mock(),
        identity=mock.Mock(advanced_routing=advanced_routing),
        state=state or FirewallState(),
        config=mock.Mock(),
        log=mock.Mock(),
    )


def test_advanced_routing_engine_sends_no_call_and_warns_once_per_firewall():
    state = FirewallState()
    first, second = make_context(True, state), make_context(True, state)

    assert collect_bgp(first) == []
    assert collect_bgp(second) == []

    first.client.op.assert_not_called()
    second.client.op.assert_not_called()
    first.log.warning.assert_called_once()
    assert 'legacy routing engine' in first.log.warning.call_args.args[0]
    second.log.warning.assert_not_called()
    # Another firewall has its own state, so it warns on its own.
    other = make_context(True)
    collect_bgp(other)
    other.log.warning.assert_called_once()


@pytest.mark.parametrize('advanced_routing', [False, None])
def test_legacy_or_unknown_routing_engine_sends_the_legacy_call(advanced_routing):
    ctx = make_context(advanced_routing)
    ctx.client.op.return_value = load(op_fixture(BGP_PEER_CMD))

    assert collect_bgp(ctx)
    ctx.client.op.assert_called_once_with(BGP_PEER_CMD)
    ctx.log.warning.assert_not_called()


def test_bgp_is_registered_and_submits_through_the_check(real_collectors, dd_run_check, aggregator):
    assert 'bgp' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    def expect(name, value, tags, metric_type):
        aggregator.assert_metric(
            f'pan_firewall.{name}', value, tags=sorted([*FW_A_TAGS, *tags]), metric_type=metric_type
        )

    gauge, monotonic = aggregator.GAUGE, aggregator.MONOTONIC_COUNT
    expect('bgp.peer.status', 1, FW_A_PEER, gauge)
    expect('bgp.peer.status', 0, FW_A_DEAD, gauge)
    expect('bgp.peer.status_duration', 4856, FW_A_PEER, gauge)
    expect('bgp.peer.restart', 0, FW_A_PEER, gauge)
    expect('bgp.peer.updates.in', 2, FW_A_PEER, monotonic)
    expect('bgp.peer.updates.out', 2, FW_A_PEER, monotonic)
    expect('bgp.peer.prefix_limit', 10, FW_A_PEER, gauge)
    expect('bgp.peer.prefixes.incoming.total', 1, [*FW_A_PEER, 'afi_safi:ipv4_unicast'], gauge)
    expect('bgp.peer.prefix_limit.utilization', 10.0, [*FW_A_PEER, 'afi_safi:ipv4_unicast'], gauge)
    assert len(aggregator.metrics('pan_firewall.bgp.peer.status')) == 2
