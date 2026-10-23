# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.pan_firewall.collectors.counters import GLOBAL_COUNTER_CMD, parse_global
from datadog_checks.pan_firewall.constants import DROPPED_PACKET_ASPECTS, GLOBAL_COUNTERS

from ..common import SYNTHETIC
from ..helpers import load_op, load_xml, series

pytestmark = pytest.mark.unit

# The values of the capture; a counter it doesn't list is sent as 0.
FW_A_COUNTERS = {
    **dict.fromkeys(GLOBAL_COUNTERS, 0),
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
# The `severity=drop` counters of the capture summed by aspect: `forward` is `flow_fwd_l3_noarp`, `pktproc` is
# `flow_action_close` + `ctd_dns_wait_pkt_drop` + `ctd_dns_wait_pkt_drop_response`, and `mgmt`, which is not in
# DROPPED_PACKET_ASPECTS, is `flow_host_decap_err`.
FW_A_DROPS = {**dict.fromkeys(DROPPED_PACKET_ASPECTS, 0), 'forward': 1546, 'pktproc': 118 + 8 + 8, 'mgmt': 45}


def counter_tags(counter, category, aspect):
    return (f'counter:{counter}', f'category:{category}', f'aspect:{aspect}')


def test_global_counters_of_the_capture():
    expected = {
        ('counter.global', counter_tags(name, *GLOBAL_COUNTERS[name])): (value, 'monotonic_count')
        for name, value in FW_A_COUNTERS.items()
    }
    expected |= {
        ('dropped_packets', (f'aspect:{aspect}',)): (value, 'monotonic_count') for aspect, value in FW_A_DROPS.items()
    }

    assert series(parse_global(load_op(GLOBAL_COUNTER_CMD))) == expected


def test_listed_counter_takes_category_and_aspect_from_the_response():
    samples = series(parse_global(load_xml(SYNTHETIC / 'counter_global_session_installed_pktproc.xml')))

    assert ('counter.global', counter_tags('session_installed', 'session', 'pktproc')) in samples
