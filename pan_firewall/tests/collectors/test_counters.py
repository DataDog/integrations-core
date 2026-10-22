# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors.counters import GLOBAL_COUNTER_CMD, parse_global
from datadog_checks.pan_firewall.constants import DROPPED_PACKET_ASPECTS, GLOBAL_COUNTERS

from ..common import SYNTHETIC
from ..helpers import load_op, load_xml

pytestmark = pytest.mark.unit

# The 26 counters, with the values of the capture (0 for a counter the capture doesn't list) and the category and
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
# Sum of the `severity=drop` counters of the capture, by aspect. `mgmt` is `flow_host_decap_err`; `pktproc` is
# `flow_action_close` + `ctd_dns_wait_pkt_drop` + `ctd_dns_wait_pkt_drop_response`; `forward` is `flow_fwd_l3_noarp`.
FW_A_DROPS = {'forward': 1546, 'pktproc': 118 + 8 + 8, 'mgmt': 45}


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


def test_global_counters_of_the_capture():
    samples = parse_global(load_op(GLOBAL_COUNTER_CMD))

    series = global_series(samples)

    # A counter the capture doesn't list is sent as 0 with the table's category and aspect.
    assert series == {counter_tags(counter, *GLOBAL_COUNTERS[counter]): value for counter, value in FW_A_VALUES.items()}
    assert {s.name for s in samples} == {'counter.global', 'dropped_packets'}
    # `dropped_packets` sums the severity=drop counters by aspect.
    assert dropped(samples) == {**dict.fromkeys(DROPPED_PACKET_ASPECTS, 0), **FW_A_DROPS}


def test_listed_counter_takes_category_and_aspect_from_the_response():
    series = global_series(parse_global(load_xml(SYNTHETIC / 'counter_global_session_installed_pktproc.xml')))

    assert series[counter_tags('session_installed', 'session', 'pktproc')] == 2269
    assert len(series) == 26
