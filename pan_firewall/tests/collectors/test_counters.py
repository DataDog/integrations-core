# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.counters import GLOBAL_COUNTER_CMD, collect_global_counters, parse_global
from datadog_checks.pan_firewall.constants import DROPPED_PACKET_ASPECTS, GLOBAL_COUNTERS
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_TAGS, SYNTHETIC
from ..fixture_map import op_fixture
from ..helpers import make_instance, new_check

# The 26 counters, with the values of each capture (0 for a counter the capture doesn't list) and the category and
# aspect they are tagged with when the capture lists them (otherwise the table's).
ZERO = dict.fromkeys(GLOBAL_COUNTERS, 0)
FW_A_VALUES = {
    **ZERO,
    'appid_unknown_fini_empty': 520,
    'flow_arp_pkt_rcv': 225,
    'flow_arp_pkt_xmt': 307,
    'flow_arp_resolve_xmt': 307,
    'flow_fwd_l3_noarp': 1546,
    'flow_host_service_allow': 2841,
    'pkt_recv': 140542,
    'pkt_sent': 140806,
    'session_freed': 2236,
    'session_installed': 2269,
    'ssl_hsm_up_down_event_rcv': 1,
}
FW_B_VALUES = {
    **ZERO,
    'appid_unknown_fini_empty': 506,
    'flow_arp_pkt_rcv': 225,
    'flow_arp_pkt_xmt': 299,
    'flow_arp_resolve_xmt': 299,
    'flow_fwd_l3_noarp': 1524,
    'flow_host_service_allow': 2833,
    'pkt_recv': 145294,
    'pkt_sent': 145540,
    'session_freed': 2219,
    'session_installed': 2247,
    'ssl_hsm_up_down_event_rcv': 1,
}
# Sum of the `severity=drop` counters of each capture, by aspect. `mgmt` is `flow_host_decap_err`; `pktproc` is
# `flow_action_close` + `ctd_dns_wait_pkt_drop` + `ctd_dns_wait_pkt_drop_response`; `forward` is `flow_fwd_l3_noarp`.
FW_A_DROPS = {'forward': 1546, 'pktproc': 118 + 8 + 8, 'mgmt': 45}
FW_B_DROPS = {'forward': 1524, 'pktproc': 122 + 6 + 6, 'mgmt': 46}


def load(path):
    return parse_response(path.read_bytes())


def global_series(samples):
    result = {}
    for s in samples:
        if s.name == 'counter.global':
            assert s.kind == 'monotonic_count'
            result[s.tags] = s.value
    return result


def counter_tags(counter, category, aspect):
    return (f'counter:{counter}', f'category:{category}', f'aspect:{aspect}')


def dropped(samples):
    result = {}
    for s in samples:
        if s.name == 'dropped_packets':
            assert s.kind == 'monotonic_count'
            (tag,) = s.tags
            assert tag.startswith('aspect:')
            result[tag.removeprefix('aspect:')] = s.value
    return result


@pytest.mark.parametrize('firewall, values', [('fw-a', FW_A_VALUES), ('fw-b', FW_B_VALUES)], ids=['fw-a', 'fw-b'])
def test_global_counters_of_the_captures(firewall, values):
    samples = parse_global(load(op_fixture(GLOBAL_COUNTER_CMD, firewall)))

    series = global_series(samples)

    assert len(series) == 26
    assert series == {counter_tags(counter, *GLOBAL_COUNTERS[counter]): value for counter, value in values.items()}
    assert {s.name for s in samples} == {'counter.global', 'dropped_packets'}


def test_listed_counter_takes_category_and_aspect_from_the_response():
    series = global_series(parse_global(load(SYNTHETIC / 'counter_global_session_installed_pktproc.xml')))

    assert series[counter_tags('session_installed', 'session', 'pktproc')] == 2269
    assert counter_tags('session_installed', 'session', 'resource') not in series
    assert len(series) == 26


def test_unlisted_counter_takes_category_and_aspect_from_the_table():
    series = global_series(parse_global(load(op_fixture(GLOBAL_COUNTER_CMD, 'fw-a'))))

    # Not in the capture: sent as 0, tagged with the table's values.
    assert series[counter_tags('flow_arp_rcv_err', 'flow', 'arp')] == 0
    assert series[counter_tags('pkt_recv_zero', 'packet', 'pktproc')] == 0


@pytest.mark.parametrize('firewall, drops', [('fw-a', FW_A_DROPS), ('fw-b', FW_B_DROPS)], ids=['fw-a', 'fw-b'])
def test_dropped_packets_sum_the_drop_severity_counters_by_aspect(firewall, drops):
    result = dropped(parse_global(load(op_fixture(GLOBAL_COUNTER_CMD, firewall))))

    assert result == {**dict.fromkeys(DROPPED_PACKET_ASPECTS, 0), **drops}
    assert len(DROPPED_PACKET_ASPECTS) == 13


def test_global_counters_sends_one_unfiltered_call(real_collectors):
    client = mock.Mock()
    client.op.return_value = load(op_fixture(GLOBAL_COUNTER_CMD, 'fw-a'))
    ctx = CollectContext(client, mock.Mock(), FirewallState(), mock.Mock(), mock.Mock())

    samples = collect_global_counters(ctx)

    client.op.assert_called_once_with('<show><counter><global/></counter></show>')
    assert len(global_series(samples)) == 26


def test_global_counters_submit_through_the_check(real_collectors, fake_panos, dd_run_check, aggregator):
    assert 'global_counters' in COLLECT_FUNCTIONS

    dd_run_check(new_check(make_instance(collect_global_counters=True)))

    for counter, (category, aspect) in GLOBAL_COUNTERS.items():
        aggregator.assert_metric(
            'pan_firewall.counter.global',
            value=FW_A_VALUES[counter],
            tags=sorted([*FW_A_TAGS, *counter_tags(counter, category, aspect)]),
            metric_type=aggregator.MONOTONIC_COUNT,
        )
    aggregator.assert_metric(
        'pan_firewall.dropped_packets',
        value=1546,
        tags=sorted([*FW_A_TAGS, 'aspect:forward']),
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_metric(
        'pan_firewall.dropped_packets',
        value=0,
        tags=sorted([*FW_A_TAGS, 'aspect:arp']),
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    aggregator.assert_metric(
        'pan_firewall.counter.global',
        value=1,
        tags=sorted([*FW_A_TAGS, 'counter:ssl_hsm_up_down_event_rcv', 'category:ssl', 'aspect:pktproc']),
        metric_type=aggregator.MONOTONIC_COUNT,
    )
    assert len(aggregator.metrics('pan_firewall.counter.global')) == 26
    assert len(aggregator.metrics('pan_firewall.dropped_packets')) == 14
    assert [c.cmd for c in fake_panos.calls if c.cmd == GLOBAL_COUNTER_CMD] == [GLOBAL_COUNTER_CMD]


def test_global_counters_off_makes_no_call(real_collectors, fake_panos, dd_run_check, aggregator):
    dd_run_check(new_check(make_instance(collect_global_counters=False)))

    assert not [c for c in fake_panos.calls if c.cmd == GLOBAL_COUNTER_CMD]
    assert not aggregator.metrics('pan_firewall.counter.global')
