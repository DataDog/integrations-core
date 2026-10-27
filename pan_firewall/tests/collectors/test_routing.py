# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.routing import (
    ARE_BGP_PEER_CMD,
    ARE_LOGICAL_ROUTER_CMD,
    ARE_OSPF_NEIGHBOR_CMD,
    BGP_PEER_CMD,
    OSPF_NEIGHBOR_CMD,
    are_json,
    camel_afi_safi_tag,
    collect_bgp,
    collect_ospf,
    parse_are_bgp_peers,
    parse_are_ospf_neighbors,
    parse_bgp_peers,
    parse_ospf_neighbors,
    peer_ip,
)
from datadog_checks.pan_firewall.errors import PanosError
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_PEER, SYNTHETIC
from ..fixture_map import find_op_fixture
from ..helpers import load_op, load_xml, make_ctx, series

pytestmark = pytest.mark.unit


def load_fw_b(cmd):
    """The parsed answer of fw-b (the Advanced Routing Engine firewall) to `cmd`."""
    return load_xml(find_op_fixture(cmd, 'fw-b'))


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


FW_A_DEAD = ('peer:dead-peer', 'vr:default', 'peer_ip:10.20.1.250', 'remote_as:65099', 'peer_group:lab')
IPV4 = {'ipv4_unicast': ((1, 0, 1, 1), 10.0)}


def test_bgp_of_the_capture():
    samples = parse_bgp_peers(load_op(BGP_PEER_CMD))

    # The down peer reports zeros and its configured limit, and has no prefix family to report.
    down = peer_samples(FW_A_DEAD, status=0, duration=0, restart=0, updates=(0, 0), limit=5000)
    up = peer_samples(FW_A_PEER, status=1, duration=4856, restart=0, updates=(2, 2), limit=10, prefixes=IPV4)
    assert series(samples) == {**down, **up}


@pytest.mark.parametrize(
    'status, duration, up, restart',
    [
        pytest.param('Established', '1799', 1, 1, id='up-for-less-than-30-minutes'),
        pytest.param('Established', '1800', 1, 0, id='up-for-30-minutes'),
        # A peer that is not Established has not come up, however short its time in the state.
        pytest.param('Active', '5', 0, 0, id='not-established'),
    ],
)
def test_bgp_restart_is_an_established_peer_up_for_less_than_30_minutes(status, duration, up, restart):
    root = load_op(BGP_PEER_CMD)
    root.find("result/entry[@peer='fw-peer']/status").text = status
    root.find("result/entry[@peer='fw-peer']/status-duration").text = duration

    values = series(parse_bgp_peers(root))

    assert values['bgp.peer.status', FW_A_PEER] == (up, 'gauge')
    assert values['bgp.peer.restart', FW_A_PEER] == (restart, 'gauge')


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
        ('10.20.1.250', '10.20.1.250'),
        ('[2001:db8::1]:179', '2001:db8::1'),
        ('2001:db8::1', '2001:db8::1'),
        (None, None),
    ],
)
def test_peer_ip_strips_the_port_and_keeps_ipv6_intact(address, expected):
    assert peer_ip(address) == expected


@pytest.mark.parametrize('advanced_routing', [False, None])
def test_the_legacy_or_unknown_routing_engine_is_asked_the_legacy_ospf_command(advanced_routing):
    ctx = make_ctx(load_op(OSPF_NEIGHBOR_CMD), identity=mock.Mock(advanced_routing=advanced_routing))

    collect_ospf(ctx)

    ctx.client.op.assert_called_once_with(OSPF_NEIGHBOR_CMD)


@pytest.mark.parametrize('advanced_routing', [False, None])
def test_the_legacy_or_unknown_routing_engine_is_asked_the_legacy_bgp_command(advanced_routing):
    ctx = make_ctx(load_op(BGP_PEER_CMD), identity=mock.Mock(advanced_routing=advanced_routing))

    collect_bgp(ctx)

    ctx.client.op.assert_called_once_with(BGP_PEER_CMD)


FW_B_PEER = ('peer:fw-peer', 'vr:default', 'peer_ip:169.254.10.1', 'remote_as:65001', 'peer_group:lab')
FW_B_DEAD = ('peer:dead-peer', 'vr:default', 'peer_ip:10.60.1.250', 'remote_as:65099', 'peer_group:lab')
FW_B_SPARSE = ('peer:sparse-peer', 'vr:default', 'peer_ip:10.60.1.249', 'remote_as:65098', 'peer_group:lab')


ARE_COUNTERS = {'updates.in', 'updates.out', 'connections.established', 'connections.dropped'}


def are_peer_samples(tags, peer, ipv4):
    """The expected samples of one ARE peer: `peer` maps a metric to its value, `ipv4` the IPv4 unicast family's."""
    expected = {
        (f'bgp.peer.{name}', tags): (value, 'monotonic_count' if name in ARE_COUNTERS else 'gauge')
        for name, value in peer.items()
    }
    family_tags = (*tags, 'afi_safi:ipv4_unicast')
    expected.update({(f'bgp.peer.{name}', family_tags): (value, 'gauge') for name, value in ipv4.items()})
    return expected


def test_are_bgp_of_the_capture():
    root = load_fw_b(ARE_BGP_PEER_CMD.format(router='default'))
    samples = parse_are_bgp_peers(are_json(root), 'default')

    # ARE reports no rejected incoming or total outgoing prefixes, and the dead peer has no sent counter.
    expected = {}
    for tags, status, duration, updates, established, prefixes, advertised in (
        (FW_B_PEER, 1, 63339.0, (2, 4), 1, 1, 4),
        (FW_B_DEAD, 0, 63363.0, (0, 0), 0, 0, None),
    ):
        peer = {
            'status': status,
            'status_duration': duration,
            'restart': 0,
            'updates.in': updates[0],
            'updates.out': updates[1],
            'connections.established': established,
            'connections.dropped': 0,
        }
        ipv4 = {
            'prefix_limit': 10,
            'prefixes.incoming.total': prefixes,
            'prefix_limit.utilization': prefixes / 10 * 100,
        }
        if advertised is not None:
            ipv4['prefixes.outgoing.advertised'] = advertised
        expected.update(are_peer_samples(tags, peer, ipv4))
    assert series(samples) == expected


@pytest.mark.parametrize(
    'duration, restart',
    [pytest.param(1799.0, 1, id='up-for-less-than-30-minutes'), pytest.param(1800.0, 0, id='up-for-30-minutes')],
)
def test_are_bgp_restart_is_an_established_peer_up_for_less_than_30_minutes(duration, restart):
    data = are_json(load_fw_b(ARE_BGP_PEER_CMD.format(router='default')))
    data['fw-peer']['status-time'] = duration

    values = series(parse_are_bgp_peers(data, 'default'))

    assert values['bgp.peer.restart', FW_B_PEER] == (restart, 'gauge')


def test_are_bgp_peer_without_details_still_reports_its_status():
    samples = parse_are_bgp_peers(are_json(load_xml(SYNTHETIC / 'are_bgp_peer_sparse.xml')), 'default')

    assert series(samples) == {
        ('bgp.peer.status', FW_B_SPARSE): (0, 'gauge'),
        ('bgp.peer.status_duration', FW_B_SPARSE): (12.0, 'gauge'),
        ('bgp.peer.restart', FW_B_SPARSE): (0, 'gauge'),
    }


@pytest.mark.parametrize('limit', [0, None])
def test_are_bgp_utilization_is_not_sent_without_a_prefix_limit(limit):
    data = are_json(load_fw_b(ARE_BGP_PEER_CMD.format(router='default')))
    family = data['fw-peer']['detail']['addressFamilyInfo']['ipv4Unicast']
    if limit is None:
        del family['prefixAllowedMax']
    else:
        family['prefixAllowedMax'] = limit

    names = {s.name for s in parse_are_bgp_peers(data, 'default') if s.tags[: len(FW_B_PEER)] == FW_B_PEER}

    assert 'bgp.peer.prefix_limit.utilization' not in names
    assert 'bgp.peer.prefixes.incoming.total' in names


def test_are_bgp_same_peer_name_in_two_logical_routers():
    peers = load_fw_b(ARE_BGP_PEER_CMD.format(router='default'))
    router_list = parse_response(
        b'<response status="success"><result><json>{"default": {}, "lr2": {}}</json></result></response>'
    )
    ctx = make_ctx(
        {
            ARE_LOGICAL_ROUTER_CMD: router_list,
            ARE_BGP_PEER_CMD.format(router='default'): peers,
            ARE_BGP_PEER_CMD.format(router='lr2'): peers,
        },
        identity=mock.Mock(advanced_routing=True),
    )

    values = series(collect_bgp(ctx))

    assert values['bgp.peer.status', FW_B_PEER] == (1, 'gauge')
    assert values['bgp.peer.status', tuple(t.replace('vr:default', 'vr:lr2') for t in FW_B_PEER)] == (1, 'gauge')


def test_advanced_routing_engine_sends_the_are_calls():
    ctx = make_ctx(
        {
            ARE_LOGICAL_ROUTER_CMD: load_fw_b(ARE_LOGICAL_ROUTER_CMD),
            ARE_BGP_PEER_CMD.format(router='default'): load_fw_b(ARE_BGP_PEER_CMD.format(router='default')),
        },
        identity=mock.Mock(advanced_routing=True),
    )

    collect_bgp(ctx)

    assert [c.args[0] for c in ctx.client.op.call_args_list] == [
        ARE_LOGICAL_ROUTER_CMD,
        ARE_BGP_PEER_CMD.format(router='default'),
    ]
    ctx.log.warning.assert_not_called()


def test_advanced_routing_engine_sends_the_are_ospf_calls():
    ctx = make_ctx(
        {
            ARE_LOGICAL_ROUTER_CMD: load_fw_b(ARE_LOGICAL_ROUTER_CMD),
            ARE_OSPF_NEIGHBOR_CMD.format(router='default'): load_fw_b(ARE_OSPF_NEIGHBOR_CMD.format(router='default')),
        },
        identity=mock.Mock(advanced_routing=True),
    )

    samples = collect_ospf(ctx)

    assert [c.args[0] for c in ctx.client.op.call_args_list] == [
        ARE_LOGICAL_ROUTER_CMD,
        ARE_OSPF_NEIGHBOR_CMD.format(router='default'),
    ]
    assert {s.name for s in samples} == {'ospf.neighbor.status', 'ospf.neighbor.state_changes'}
    ctx.log.warning.assert_not_called()


def test_are_json_of_the_logical_router_capture_names_the_routers():
    assert list(are_json(load_fw_b(ARE_LOGICAL_ROUTER_CMD))) == ['default']


def test_are_json_invalid_raises():
    root = parse_response(b'<response status="success"><result><json>{not json</json></result></response>')

    with pytest.raises(PanosError):
        are_json(root)


@pytest.mark.parametrize(
    'body',
    [b'<result/>', b'<result><json></json></result>', b'<result><json>  </json></result>'],
    ids=['no-json', 'empty-json', 'blank-json'],
)
def test_are_json_missing_is_empty(body):
    assert are_json(parse_response(b'<response status="success">' + body + b'</response>')) == {}


@pytest.mark.parametrize('name, expected', [('ipv4Unicast', 'ipv4_unicast'), ('ipv6Unicast', 'ipv6_unicast')])
def test_camel_afi_safi_tag(name, expected):
    assert camel_afi_safi_tag(name) == expected


FW_A_OSPF = ('neighbor:169.254.10.2', 'router_id:10.255.0.2', 'area:0.0.0.0', 'vr:default')


@pytest.mark.parametrize('state, expected', [('full', 1), ('FULL', 1), ('2-way', 0)])
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


FW_B_OSPF = ('neighbor:169.254.10.1', 'router_id:10.255.0.1', 'area:0.0.0.0', 'vr:default')


def test_are_ospf_of_the_capture():
    data = are_json(load_fw_b(ARE_OSPF_NEIGHBOR_CMD.format(router='default')))

    assert series(parse_are_ospf_neighbors(data, 'default')) == {
        ('ospf.neighbor.status', FW_B_OSPF): (1, 'gauge'),
        ('ospf.neighbor.state_changes', FW_B_OSPF): (4, 'monotonic_count'),
    }


@pytest.mark.parametrize(
    'state, expected',
    [('Full', 1), ('Full/DR', 1), ('Full/DROther', 1), ('2-Way', 0), ('Init', 0)],
)
def test_are_ospf_neighbor_is_up_only_in_a_full_state(state, expected):
    data = are_json(load_fw_b(ARE_OSPF_NEIGHBOR_CMD.format(router='default')))
    data['neighbors']['10.255.0.1'][0]['nbrState'] = state

    values = series(parse_are_ospf_neighbors(data, 'default'))

    assert values['ospf.neighbor.status', FW_B_OSPF] == (expected, 'gauge')


def test_are_ospf_neighbor_without_a_state_is_not_reported():
    data = are_json(load_fw_b(ARE_OSPF_NEIGHBOR_CMD.format(router='default')))
    del data['neighbors']['10.255.0.1'][0]['nbrState']

    assert parse_are_ospf_neighbors(data, 'default') == []


def test_are_ospf_without_neighbors_is_empty():
    assert parse_are_ospf_neighbors({}, 'default') == []
