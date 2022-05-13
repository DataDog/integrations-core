# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import array
import logging
import os
import platform
import socket
from collections import namedtuple

import mock
import pytest
from six import PY3, iteritems

from datadog_checks.base import ConfigurationError
from datadog_checks.dev import EnvVars

from . import common

if PY3:
    long = int

FIXTURE_DIR = os.path.join(common.HERE, 'fixtures')

CX_STATE_GAUGES_VALUES = {
    'system.net.udp4.connections': 2,
    'system.net.udp6.connections': 3,
    'system.net.tcp4.established': 1,
    'system.net.tcp4.opening': 2,
    'system.net.tcp4.closing': 2,
    'system.net.tcp4.listening': 2,
    'system.net.tcp4.time_wait': 2,
    'system.net.tcp6.established': 1,
    'system.net.tcp6.opening': 0,
    'system.net.tcp6.closing': 1,
    'system.net.tcp6.listening': 1,
    'system.net.tcp6.time_wait': 1,
}

CONNTRACK_STATS = {
    'system.net.conntrack.found': (27644, 21960),
    'system.net.conntrack.invalid': (19060, 17288),
    'system.net.conntrack.ignore': (485633411, 475938848),
    'system.net.conntrack.insert': (0, 0),
    'system.net.conntrack.insert_failed': (1, 1),
    'system.net.conntrack.drop': (1, 1),
    'system.net.conntrack.early_drop': (0, 0),
    'system.net.conntrack.error': (0, 0),
    'system.net.conntrack.search_restart': (39936711, 36983181),
}

LINUX_SYS_NET_STATS = {
    'system.net.iface.mtu': (65536, 9001),
    'system.net.iface.tx_queue_len': (1000, 1000),
    'system.net.iface.num_rx_queues': (1, 2),
    'system.net.iface.num_tx_queues': (1, 3),
}

ENA_ETHTOOL_VALUES = {
    'queue:0': {
        'ena.queue.rx_bad_csum': 0,
        'ena.queue.rx_bad_desc_num': 0,
        'ena.queue.rx_bad_req_id': 0,
        'ena.queue.rx_bytes': 24423973,
        'ena.queue.rx_cnt': 18967,
        'ena.queue.rx_csum_good': 0,
        'ena.queue.rx_csum_unchecked': 0,
        'ena.queue.rx_dma_mapping_err': 0,
        'ena.queue.rx_empty_rx_ring': 0,
        'ena.queue.rx_page_alloc_fail': 0,
        'ena.queue.rx_refil_partial': 0,
        'ena.queue.rx_rx_copybreak_pkt': 2394,
        'ena.queue.rx_skb_alloc_fail': 0,
        'ena.queue.tx_bad_req_id': 0,
        'ena.queue.tx_bytes': 1566697,
        'ena.queue.tx_cnt': 17841,
        'ena.queue.tx_dma_mapping_err': 0,
        'ena.queue.tx_doorbells': 17766,
        'ena.queue.tx_linearize': 0,
        'ena.queue.tx_linearize_failed': 0,
        'ena.queue.tx_llq_buffer_copy': 0,
        'ena.queue.tx_missed_tx': 0,
        'ena.queue.tx_napi_comp': 21232,
        'ena.queue.tx_prepare_ctx_err': 0,
        'ena.queue.tx_queue_stop': 0,
        'ena.queue.tx_queue_wakeup': 0,
        'ena.queue.tx_tx_poll': 21232,
        'ena.queue.tx_unmask_interrupt': 21232,
    },
    'queue:1': {
        'ena.queue.rx_bad_csum': 0,
        'ena.queue.rx_bad_desc_num': 0,
        'ena.queue.rx_bad_req_id': 0,
        'ena.queue.rx_bytes': 429894172,
        'ena.queue.rx_cnt': 300129,
        'ena.queue.rx_csum_good': 0,
        'ena.queue.rx_csum_unchecked': 0,
        'ena.queue.rx_dma_mapping_err': 0,
        'ena.queue.rx_empty_rx_ring': 0,
        'ena.queue.rx_page_alloc_fail': 0,
        'ena.queue.rx_refil_partial': 0,
        'ena.queue.rx_rx_copybreak_pkt': 7146,
        'ena.queue.rx_skb_alloc_fail': 0,
        'ena.queue.tx_bad_req_id': 0,
        'ena.queue.tx_bytes': 1618542,
        'ena.queue.tx_cnt': 26865,
        'ena.queue.tx_dma_mapping_err': 0,
        'ena.queue.tx_doorbells': 26863,
        'ena.queue.tx_linearize': 0,
        'ena.queue.tx_linearize_failed': 0,
        'ena.queue.tx_llq_buffer_copy': 0,
        'ena.queue.tx_missed_tx': 0,
        'ena.queue.tx_napi_comp': 87481,
        'ena.queue.tx_prepare_ctx_err': 0,
        'ena.queue.tx_queue_stop': 0,
        'ena.queue.tx_queue_wakeup': 0,
        'ena.queue.tx_tx_poll': 87509,
        'ena.queue.tx_unmask_interrupt': 87481,
    },
    'global': {'ena.resume': 0, 'ena.suspend': 0, 'ena.tx_timeout': 0, 'ena.wd_expired': 0},
}


VIRTIO_ETHTOOL_VALUES = {
    'queue:0': {
        'virtio_net.queue.rx_bytes': 3330581189214,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 49443,
        'virtio_net.queue.rx_packets': 3240253467,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 729525539711,
        'virtio_net.queue.tx_kicks': 17882,
        'virtio_net.queue.tx_packets': 1171912402,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:1': {
        'virtio_net.queue.rx_bytes': 2943312275097,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 44975,
        'virtio_net.queue.rx_packets': 2947437406,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 711942138149,
        'virtio_net.queue.tx_kicks': 17055,
        'virtio_net.queue.tx_packets': 1117705342,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:2': {
        'virtio_net.queue.rx_bytes': 3114136399578,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 46080,
        'virtio_net.queue.rx_packets': 3019742569,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 715095442379,
        'virtio_net.queue.tx_kicks': 17149,
        'virtio_net.queue.tx_packets': 1123816782,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:3': {
        'virtio_net.queue.rx_bytes': 3017036703051,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 46688,
        'virtio_net.queue.rx_packets': 3059719508,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 714098071307,
        'virtio_net.queue.tx_kicks': 16939,
        'virtio_net.queue.tx_packets': 1110067614,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:4': {
        'virtio_net.queue.rx_bytes': 3859364388980,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 55049,
        'virtio_net.queue.rx_packets': 3607658361,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 723288378426,
        'virtio_net.queue.tx_kicks': 17745,
        'virtio_net.queue.tx_packets': 1162873931,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:5': {
        'virtio_net.queue.rx_bytes': 3638485117143,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 52996,
        'virtio_net.queue.rx_packets': 3473131946,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 717434286730,
        'virtio_net.queue.tx_kicks': 17543,
        'virtio_net.queue.tx_packets': 1149663211,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:6': {
        'virtio_net.queue.rx_bytes': 3344829702018,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 49510,
        'virtio_net.queue.rx_packets': 3244657039,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 712950253668,
        'virtio_net.queue.tx_kicks': 17528,
        'virtio_net.queue.tx_packets': 1148696179,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
    'queue:7': {
        'virtio_net.queue.rx_bytes': 3528035076384,
        'virtio_net.queue.rx_drops': 0,
        'virtio_net.queue.rx_kicks': 52167,
        'virtio_net.queue.rx_packets': 3418771828,
        'virtio_net.queue.rx_xdp_drops': 0,
        'virtio_net.queue.rx_xdp_packets': 0,
        'virtio_net.queue.rx_xdp_redirects': 0,
        'virtio_net.queue.rx_xdp_tx': 0,
        'virtio_net.queue.tx_bytes': 712418609150,
        'virtio_net.queue.tx_kicks': 17508,
        'virtio_net.queue.tx_packets': 1147383428,
        'virtio_net.queue.tx_xdp_tx': 0,
        'virtio_net.queue.tx_xdp_tx_drops': 0,
    },
}

HV_NETVSC_ETHTOOL_VALUES = {
    'queue:0': {
        'hv_netvsc.queue.rx_bytes': 69753132,
        'hv_netvsc.queue.rx_packets': 174128,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 673523,
        'hv_netvsc.queue.tx_packets': 367,
    },
    'queue:1': {
        'hv_netvsc.queue.rx_bytes': 80536029,
        'hv_netvsc.queue.rx_packets': 186321,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 20418,
        'hv_netvsc.queue.tx_packets': 40,
    },
    'queue:2': {
        'hv_netvsc.queue.rx_bytes': 97417257,
        'hv_netvsc.queue.rx_packets': 190115,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 194574,
        'hv_netvsc.queue.tx_packets': 96,
    },
    'queue:3': {
        'hv_netvsc.queue.rx_bytes': 57902633,
        'hv_netvsc.queue.rx_packets': 161989,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 43830,
        'hv_netvsc.queue.tx_packets': 36,
    },
    'queue:4': {
        'hv_netvsc.queue.rx_bytes': 57235863,
        'hv_netvsc.queue.rx_packets': 161812,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 9700,
        'hv_netvsc.queue.tx_packets': 17,
    },
    'queue:5': {
        'hv_netvsc.queue.rx_bytes': 57347838,
        'hv_netvsc.queue.rx_packets': 167028,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 47915,
        'hv_netvsc.queue.tx_packets': 52,
    },
    'queue:6': {
        'hv_netvsc.queue.rx_bytes': 56878203,
        'hv_netvsc.queue.rx_packets': 166400,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 16863,
        'hv_netvsc.queue.tx_packets': 13,
    },
    'queue:7': {
        'hv_netvsc.queue.rx_bytes': 59770311,
        'hv_netvsc.queue.rx_packets': 163608,
        'hv_netvsc.queue.rx_xdp_drop': 0,
        'hv_netvsc.queue.tx_bytes': 27259,
        'hv_netvsc.queue.tx_packets': 57,
    },
    'cpu:0': {
        'hv_netvsc.cpu.rx_bytes': 192205947,
        'hv_netvsc.cpu.rx_packets': 265690,
        'hv_netvsc.cpu.tx_bytes': 2332595871,
        'hv_netvsc.cpu.tx_packets': 2162169,
        'hv_netvsc.cpu.vf_rx_bytes': 111669918,
        'hv_netvsc.cpu.vf_rx_packets': 79369,
        'hv_netvsc.cpu.vf_tx_bytes': 2332575453,
        'hv_netvsc.cpu.vf_tx_packets': 2162129,
    },
    'cpu:1': {
        'hv_netvsc.cpu.rx_bytes': 1237224500,
        'hv_netvsc.cpu.rx_packets': 2561669,
        'hv_netvsc.cpu.tx_bytes': 2548076602,
        'hv_netvsc.cpu.tx_packets': 2077301,
        'hv_netvsc.cpu.vf_rx_bytes': 1139807243,
        'hv_netvsc.cpu.vf_rx_packets': 2371554,
        'hv_netvsc.cpu.vf_tx_bytes': 2547882028,
        'hv_netvsc.cpu.vf_tx_packets': 2077205,
    },
    'cpu:2': {
        'hv_netvsc.cpu.rx_bytes': 854059182,
        'hv_netvsc.cpu.rx_packets': 2373664,
        'hv_netvsc.cpu.tx_bytes': 4226031193,
        'hv_netvsc.cpu.tx_packets': 3312434,
        'hv_netvsc.cpu.vf_rx_bytes': 726403417,
        'hv_netvsc.cpu.vf_rx_packets': 2037547,
        'hv_netvsc.cpu.vf_tx_bytes': 4225313840,
        'hv_netvsc.cpu.vf_tx_packets': 3312031,
    },
    'cpu:3': {
        'hv_netvsc.cpu.rx_bytes': 958939049,
        'hv_netvsc.cpu.rx_packets': 2520782,
        'hv_netvsc.cpu.tx_bytes': 4672129227,
        'hv_netvsc.cpu.tx_packets': 3349434,
        'hv_netvsc.cpu.vf_rx_bytes': 901703186,
        'hv_netvsc.cpu.vf_rx_packets': 2358970,
        'hv_netvsc.cpu.vf_tx_bytes': 4672119527,
        'hv_netvsc.cpu.vf_tx_packets': 3349417,
    },
    'cpu:4': {
        'hv_netvsc.cpu.rx_bytes': 3687149916,
        'hv_netvsc.cpu.rx_packets': 4446524,
        'hv_netvsc.cpu.tx_bytes': 7290434777,
        'hv_netvsc.cpu.tx_packets': 5329581,
        'hv_netvsc.cpu.vf_rx_bytes': 3629802078,
        'hv_netvsc.cpu.vf_rx_packets': 4279496,
        'hv_netvsc.cpu.vf_tx_bytes': 7290386862,
        'hv_netvsc.cpu.vf_tx_packets': 5329529,
    },
    'cpu:5': {
        'hv_netvsc.cpu.rx_bytes': 2252499618,
        'hv_netvsc.cpu.rx_packets': 3448975,
        'hv_netvsc.cpu.tx_bytes': 5652959262,
        'hv_netvsc.cpu.tx_packets': 4020678,
        'hv_netvsc.cpu.vf_rx_bytes': 2195621415,
        'hv_netvsc.cpu.vf_rx_packets': 3282575,
        'hv_netvsc.cpu.vf_tx_bytes': 5652942399,
        'hv_netvsc.cpu.vf_tx_packets': 4020665,
    },
    'cpu:6': {
        'hv_netvsc.cpu.rx_bytes': 2648234282,
        'hv_netvsc.cpu.rx_packets': 4579181,
        'hv_netvsc.cpu.tx_bytes': 7967277235,
        'hv_netvsc.cpu.tx_packets': 5643851,
        'hv_netvsc.cpu.vf_rx_bytes': 2588463971,
        'hv_netvsc.cpu.vf_rx_packets': 4415573,
        'hv_netvsc.cpu.vf_tx_bytes': 7967249976,
        'hv_netvsc.cpu.vf_tx_packets': 5643794,
    },
    'cpu:7': {
        'hv_netvsc.cpu.rx_bytes': 1050540361,
        'hv_netvsc.cpu.rx_packets': 3362379,
        'hv_netvsc.cpu.tx_bytes': 6038160981,
        'hv_netvsc.cpu.tx_packets': 4145533,
        'hv_netvsc.cpu.vf_rx_bytes': 1050540361,
        'hv_netvsc.cpu.vf_rx_packets': 3362379,
        'hv_netvsc.cpu.vf_tx_bytes': 6038160981,
        'hv_netvsc.cpu.vf_tx_packets': 4145533,
    },
    'global': {
        'hv_netvsc.rx_comp_busy': 0,
        'hv_netvsc.rx_no_memory': 0,
        'hv_netvsc.stop_queue': 0,
        'hv_netvsc.tx_busy': 0,
        'hv_netvsc.tx_no_memory': 0,
        'hv_netvsc.tx_no_space': 0,
        'hv_netvsc.tx_scattered': 0,
        'hv_netvsc.tx_send_full': 0,
        'hv_netvsc.tx_too_big': 0,
        'hv_netvsc.wake_queue': 0,
    },
}

GVE_ETHTOOL_VALUES = {
    'queue:0': {
        'gve.queue.rx_bytes': 540727,
        'gve.queue.rx_completed_desc': 855,
        'gve.queue.rx_copied_pkt': 490,
        'gve.queue.rx_copybreak_pkt': 490,
        'gve.queue.rx_dropped_pkt': 0,
        'gve.queue.rx_drops_invalid_checksum': 0,
        'gve.queue.rx_drops_packet_over_mru': 0,
        'gve.queue.rx_no_buffers_posted': 0,
        'gve.queue.rx_posted_desc': 1879,
        'gve.queue.rx_queue_drop_cnt': 0,
        'gve.queue.tx_bytes': 215568,
        'gve.queue.tx_completed_desc': 2746,
        'gve.queue.tx_dma_mapping_error': 0,
        'gve.queue.tx_event_counter': 2746,
        'gve.queue.tx_posted_desc': 2746,
        'gve.queue.tx_stop': 0,
        'gve.queue.tx_wake': 0,
    },
    'queue:1': {
        'gve.queue.rx_bytes': 382521468,
        'gve.queue.rx_completed_desc': 262265,
        'gve.queue.rx_copied_pkt': 172283,
        'gve.queue.rx_copybreak_pkt': 1010,
        'gve.queue.rx_dropped_pkt': 0,
        'gve.queue.rx_drops_invalid_checksum': 0,
        'gve.queue.rx_drops_packet_over_mru': 0,
        'gve.queue.rx_no_buffers_posted': 0,
        'gve.queue.rx_posted_desc': 263289,
        'gve.queue.rx_queue_drop_cnt': 0,
        'gve.queue.tx_bytes': 518657,
        'gve.queue.tx_completed_desc': 6998,
        'gve.queue.tx_dma_mapping_error': 0,
        'gve.queue.tx_event_counter': 6998,
        'gve.queue.tx_posted_desc': 6998,
        'gve.queue.tx_stop': 0,
        'gve.queue.tx_wake': 0,
    },
    'queue:2': {
        'gve.queue.rx_bytes': 440781191,
        'gve.queue.rx_completed_desc': 301858,
        'gve.queue.rx_copied_pkt': 219260,
        'gve.queue.rx_copybreak_pkt': 795,
        'gve.queue.rx_dropped_pkt': 0,
        'gve.queue.rx_drops_invalid_checksum': 0,
        'gve.queue.rx_drops_packet_over_mru': 0,
        'gve.queue.rx_no_buffers_posted': 0,
        'gve.queue.rx_posted_desc': 302882,
        'gve.queue.rx_queue_drop_cnt': 0,
        'gve.queue.tx_bytes': 499988,
        'gve.queue.tx_completed_desc': 6928,
        'gve.queue.tx_dma_mapping_error': 0,
        'gve.queue.tx_event_counter': 6928,
        'gve.queue.tx_posted_desc': 6928,
        'gve.queue.tx_stop': 0,
        'gve.queue.tx_wake': 0,
    },
    'queue:3': {
        'gve.queue.rx_bytes': 26742505,
        'gve.queue.rx_completed_desc': 18895,
        'gve.queue.rx_copied_pkt': 4889,
        'gve.queue.rx_copybreak_pkt': 533,
        'gve.queue.rx_dropped_pkt': 0,
        'gve.queue.rx_drops_invalid_checksum': 0,
        'gve.queue.rx_drops_packet_over_mru': 0,
        'gve.queue.rx_no_buffers_posted': 0,
        'gve.queue.rx_posted_desc': 19919,
        'gve.queue.rx_queue_drop_cnt': 0,
        'gve.queue.tx_bytes': 168545,
        'gve.queue.tx_completed_desc': 1971,
        'gve.queue.tx_dma_mapping_error': 0,
        'gve.queue.tx_event_counter': 1971,
        'gve.queue.tx_posted_desc': 1971,
        'gve.queue.tx_stop': 0,
        'gve.queue.tx_wake': 0,
    },
    'global': {
        'gve.dma_mapping_error': 0,
        'gve.page_alloc_fail': 0,
        'gve.rx_buf_alloc_fail': 0,
        'gve.rx_desc_err_dropped_pkt': 0,
        'gve.rx_skb_alloc_fail': 0,
        'gve.tx_timeouts': 0,
    },
}

PROC_NET_STATS = {
    'system.net.ip.in_receives': 159747123,
    'system.net.ip.in_header_errors': 23,
    'system.net.ip.in_addr_errors': 0,
    'system.net.ip.in_unknown_protos': 0,
    'system.net.ip.in_discards': 0,
    'system.net.ip.in_delivers': 159745645,
    'system.net.ip.out_requests': 162992767,
    'system.net.ip.out_discards': 613,
    'system.net.ip.out_no_routes': 0,
    'system.net.ip.forwarded_datagrams': 1449,
    'system.net.ip.reassembly_timeouts': 0,
    'system.net.ip.reassembly_requests': 0,
    'system.net.ip.reassembly_oks': 0,
    'system.net.ip.reassembly_fails': 0,
    'system.net.ip.fragmentation_oks': 0,
    'system.net.ip.fragmentation_fails': 0,
    'system.net.ip.fragmentation_creates': 0,
    'system.net.ip.in_receives.count': 159747123,
    'system.net.ip.in_header_errors.count': 23,
    'system.net.ip.in_addr_errors.count': 0,
    'system.net.ip.in_unknown_protos.count': 0,
    'system.net.ip.in_discards.count': 0,
    'system.net.ip.in_delivers.count': 159745645,
    'system.net.ip.out_requests.count': 162992767,
    'system.net.ip.out_discards.count': 613,
    'system.net.ip.out_no_routes.count': 0,
    'system.net.ip.forwarded_datagrams.count': 1449,
    'system.net.ip.reassembly_timeouts.count': 0,
    'system.net.ip.reassembly_requests.count': 0,
    'system.net.ip.reassembly_oks.count': 0,
    'system.net.ip.reassembly_fails.count': 0,
    'system.net.ip.fragmentation_oks.count': 0,
    'system.net.ip.fragmentation_fails.count': 0,
    'system.net.ip.fragmentation_creates.count': 0,
    'system.net.tcp.active_opens': 6828054,
    'system.net.tcp.passive_opens': 4198200,
    'system.net.tcp.attempt_fails': 174,
    'system.net.tcp.established_resets': 761431,
    'system.net.tcp.current_established': 59,
    'system.net.tcp.in_errors': 0,
    'system.net.tcp.out_resets': 792992,
    'system.net.tcp.in_csum_errors': 0,
    'system.net.tcp.active_opens.count': 6828054,
    'system.net.tcp.passive_opens.count': 4198200,
    'system.net.tcp.attempt_fails.count': 174,
    'system.net.tcp.established_resets.count': 761431,
    'system.net.tcp.in_errors.count': 0,
    'system.net.tcp.out_resets.count': 792992,
    'system.net.tcp.in_csum_errors.count': 0,
    'system.net.ip.in_no_routes': 6,
    'system.net.ip.in_truncated_pkts': 0,
    'system.net.ip.in_csum_errors': 0,
    'system.net.ip.reassembly_overlaps': 0,
    'system.net.ip.in_no_routes.count': 6,
    'system.net.ip.in_truncated_pkts.count': 0,
    'system.net.ip.in_csum_errors.count': 0,
    'system.net.ip.reassembly_overlaps.count': 0,
}

if PY3:
    ESCAPE_ENCODING = 'unicode-escape'

    def decode_string(s):
        return s.decode(ESCAPE_ENCODING)

else:
    ESCAPE_ENCODING = 'string-escape'

    def decode_string(s):
        s.decode(ESCAPE_ENCODING)
        return s.decode("utf-8")


def read_int_file_mock(location):
    if location == '/sys/class/net/lo/mtu':
        return 65536
    elif location == '/sys/class/net/lo/tx_queue_len':
        return 1000
    elif location == '/sys/class/net/ens5/mtu':
        return 9001
    elif location == '/sys/class/net/ens5/tx_queue_len':
        return 1000
    elif location == '/sys/class/net/invalid/mtu':
        return None
    elif location == '/sys/class/net/invalid/tx_queue_len':
        return None


def os_list_dir_mock(location):
    if location == '/sys/class/net':
        return ['ens5', 'lo', 'invalid']
    elif location == '/sys/class/net/lo/queues':
        return ['rx-1', 'tx-1']
    elif location == '/sys/class/net/ens5/queues':
        return ['rx-1', 'rx-2', 'tx-1', 'tx-2', 'tx-3']
    elif location == '/sys/class/net/invalid/queues':
        raise OSError()


def ss_subprocess_mock(*args, **kwargs):
    if '--udp --all --ipv4' in args[0][2]:
        return '3', None, None
    elif '--udp --all --ipv6' in args[0][2]:
        return '4', None, None
    elif '--tcp --all --ipv4' in args[0][2]:
        file_name = 'ss_ipv4_tcp_short'
    elif '--tcp --all --ipv6' in args[0][2]:
        file_name = 'ss_ipv6_tcp_short'

    with open(os.path.join(FIXTURE_DIR, file_name), 'rb') as f:
        contents = f.read()
        return decode_string(contents), None, None


def netstat_subprocess_mock(*args, **kwargs):
    if args[0][0] == 'sh':
        raise OSError()
    elif args[0][0] == 'netstat':
        with open(os.path.join(FIXTURE_DIR, 'netstat'), 'rb') as f:
            contents = f.read()
            return decode_string(contents), None, None


@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
def test_cx_state(aggregator, check):
    instance = {'collect_connection_state': True}
    with mock.patch('datadog_checks.network.network.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check._collect_cx_state = True
        check.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)
        aggregator.reset()

        out.side_effect = netstat_subprocess_mock
        check.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)


@pytest.mark.skipif(platform.system() != 'Linux', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
@mock.patch('os.listdir', side_effect=os_list_dir_mock)
@mock.patch('datadog_checks.network.network.Network._read_int_file', side_effect=read_int_file_mock)
def test_linux_sys_net(is_linux, listdir, read_int_file, aggregator, check):
    check.check({})
    for metric, value in iteritems(LINUX_SYS_NET_STATS):
        aggregator.assert_metric(metric, value=value[0], tags=['iface:lo'])
        aggregator.assert_metric(metric, value=value[1], tags=['iface:ens5'])
    aggregator.reset()


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_cx_state_mocked(is_linux, aggregator, check):
    instance = {'collect_connection_state': True}
    with mock.patch('datadog_checks.network.network.get_subprocess_output') as out:
        out.side_effect = ss_subprocess_mock
        check._collect_cx_state = True
        check._get_linux_sys_net = lambda x: True
        check._is_collect_cx_state_runnable = lambda x: True
        check._get_net_proc_base_location = lambda x: FIXTURE_DIR
        check.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)
        aggregator.reset()

        out.side_effect = netstat_subprocess_mock
        check.check(instance)
        for metric, value in iteritems(CX_STATE_GAUGES_VALUES):
            aggregator.assert_metric(metric, value=value)


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_proc_net_metrics(is_linux, aggregator, check):
    check._get_net_proc_base_location = lambda x: FIXTURE_DIR
    instance = {'collect_count_metrics': True}
    check.check(instance)
    for metric, value in iteritems(PROC_NET_STATS):
        aggregator.assert_metric(metric, value=value)


def test_add_conntrack_stats_metrics(aggregator, check):
    mocked_conntrack_stats = (
        "cpu=0 found=27644 invalid=19060 ignore=485633411 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=39936711\n"
        "cpu=1 found=21960 invalid=17288 ignore=475938848 insert=0 insert_failed=1 "
        "drop=1 early_drop=0 error=0 search_restart=36983181"
    )
    with mock.patch('datadog_checks.network.network.get_subprocess_output') as subprocess:
        subprocess.return_value = mocked_conntrack_stats, None, None
        check._add_conntrack_stats_metrics(None, None, ['foo:bar'])

        for metric, value in iteritems(CONNTRACK_STATS):
            aggregator.assert_metric(metric, value=value[0], tags=['foo:bar', 'cpu:0'])
            aggregator.assert_metric(metric, value=value[1], tags=['foo:bar', 'cpu:1'])


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=True)
def test_win_uses_psutil(is_linux, is_bsd, is_solaris, is_windows, check):
    with mock.patch.object(check, '_check_psutil') as _check_psutil:
        check.check({})
        check._check_psutil = mock.MagicMock()
        _check_psutil.assert_called_once_with({})


def test_check_psutil(aggregator, check):
    with mock.patch.object(check, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check._collect_cx_state = False
        check._check_psutil({})
        _cx_state_psutil.assert_not_called()
        _cx_counters_psutil.assert_called_once_with(tags=[])

    with mock.patch.object(check, '_cx_state_psutil') as _cx_state_psutil, mock.patch.object(
        check, '_cx_counters_psutil'
    ) as _cx_counters_psutil:
        check._collect_cx_state = True
        check._check_psutil({})
        _cx_state_psutil.assert_called_once_with(tags=[])
        _cx_counters_psutil.assert_called_once_with(tags=[])


def test_cx_state_psutil(aggregator, check):
    sconn = namedtuple('sconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status', 'pid'])
    conn = [
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 50482),
            raddr=('127.0.0.1', 2638),
            status='ESTABLISHED',
            pid=1416,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::', 50482),
            raddr=('::', 2638),
            status='ESTABLISHED',
            pid=42,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::', 49163),
            raddr=(),
            status='LISTEN',
            pid=1416,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('0.0.0.0', 445),
            raddr=(),
            status='LISTEN',
            pid=4,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::1', 56521),
            raddr=('::1', 17123),
            status='TIME_WAIT',
            pid=0,
        ),
        sconn(
            fd=-1, family=socket.AF_INET6, type=socket.SOCK_DGRAM, laddr=('::', 500), raddr=(), status='NONE', pid=892
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            laddr=('::1', 56493),
            raddr=('::1', 17123),
            status='TIME_WAIT',
            pid=0,
        ),
        sconn(
            fd=-1,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            laddr=('127.0.0.1', 54541),
            raddr=('127.0.0.1', 54542),
            status='ESTABLISHED',
            pid=20500,
        ),
    ]

    results = {
        'system.net.tcp6.time_wait': 2,
        'system.net.tcp4.listening': 1,
        'system.net.tcp6.closing': 0,
        'system.net.tcp4.closing': 0,
        'system.net.tcp4.time_wait': 0,
        'system.net.tcp6.established': 1,
        'system.net.tcp4.established': 2,
        'system.net.tcp6.listening': 1,
        'system.net.tcp4.opening': 0,
        'system.net.udp4.connections': 0,
        'system.net.udp6.connections': 1,
        'system.net.tcp6.opening': 0,
    }

    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
        mock_psutil.net_connections.return_value = conn
        check._setup_metrics({})
        check._cx_state_psutil()
        for _, m in iteritems(aggregator._metrics):
            assert results[m[0].name] == m[0].value


def test_cx_counters_psutil(aggregator, check):
    snetio = namedtuple(
        'snetio', ['bytes_sent', 'bytes_recv', 'packets_sent', 'packets_recv', 'errin', 'errout', 'dropin', 'dropout']
    )
    counters = {
        'Ethernet': snetio(
            bytes_sent=long(3096403230),
            bytes_recv=long(3280598526),
            packets_sent=6777924,
            packets_recv=32888147,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        ),
        'Loopback Pseudo-Interface 1': snetio(
            bytes_sent=0, bytes_recv=0, packets_sent=0, packets_recv=0, errin=0, errout=0, dropin=0, dropout=0
        ),
    }
    with mock.patch('datadog_checks.network.network.psutil') as mock_psutil:
        mock_psutil.net_io_counters.return_value = counters
        check._excluded_ifaces = ['Loopback Pseudo-Interface 1']
        check._exclude_iface_re = ''
        check._cx_counters_psutil()
        for _, m in iteritems(aggregator._metrics):
            assert 'device:Ethernet' in m[0].tags
            if 'bytes_rcvd' in m[0].name:
                assert m[0].value == 3280598526


def test_parse_protocol_psutil(aggregator, check):
    import socket

    conn = mock.MagicMock()

    protocol = check._parse_protocol_psutil(conn)
    assert protocol == ''

    conn.type = socket.SOCK_STREAM
    conn.family = socket.AF_INET6
    protocol = check._parse_protocol_psutil(conn)
    assert protocol == 'tcp6'

    conn.type = socket.SOCK_DGRAM
    conn.family = socket.AF_INET
    protocol = check._parse_protocol_psutil(conn)
    assert protocol == 'udp4'


@pytest.mark.parametrize(
    "proc_location, envs, expected_net_proc_base_location",
    [
        ("/something/proc", {'DOCKER_DD_AGENT': 'true'}, "/something/proc/1"),
        ("/something/proc", {}, "/something/proc"),
        ("/proc", {'DOCKER_DD_AGENT': 'true'}, "/proc"),
        ("/proc", {}, "/proc"),
    ],
)
def test_get_net_proc_base_location(aggregator, check, proc_location, envs, expected_net_proc_base_location):
    with EnvVars(envs):
        actual = check._get_net_proc_base_location(proc_location)
        assert expected_net_proc_base_location == actual


@pytest.mark.skipif(not PY3, reason="mock builtins only works on Python 3")
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_proc_permissions_error(aggregator, check, caplog):
    caplog.set_level(logging.DEBUG)
    with mock.patch('builtins.open', mock.mock_open()) as mock_file:
        mock_file.side_effect = IOError()
        # force linux check so it will run on macOS too
        check._collect_cx_state = False
        check._check_linux(instance={})
        assert 'Unable to read /proc/net/dev.' in caplog.text
        assert 'Unable to read /proc/net/netstat.' in caplog.text
        assert 'Unable to read /proc/net/snmp.' in caplog.text


def test_invalid_excluded_interfaces(check):
    instance = {'excluded_interfaces': None}
    with pytest.raises(ConfigurationError):
        check.check(instance)


@pytest.mark.parametrize(
    "proc_location, ss_found, expected",
    [("/proc", False, True), ("/something/proc", False, False), ("/something/proc", True, True)],
)
def test_is_collect_cx_state_runnable(aggregator, check, proc_location, ss_found, expected):
    with mock.patch('distutils.spawn.find_executable', lambda x: "/bin/ss" if ss_found else None):
        check._collect_cx_state = True
        assert check._is_collect_cx_state_runnable(proc_location) == expected


@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_solaris', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_windows', return_value=False)
@mock.patch('distutils.spawn.find_executable', return_value='/bin/ss')
def test_ss_with_custom_procfs(is_linux, is_bsd, is_solaris, is_windows, aggregator, check):
    check._get_linux_sys_net = lambda x: True
    instance = {'collect_connection_state': True}
    with mock.patch(
        'datadog_checks.network.network.get_subprocess_output', side_effect=ss_subprocess_mock
    ) as get_subprocess_output:
        check._get_net_proc_base_location = lambda x: "/something/proc"
        check.check(instance)
        get_subprocess_output.assert_called_with(
            ["sh", "-c", "ss --numeric --udp --all --ipv6 | wc -l"],
            check.log,
            env={'PROC_ROOT': "/something/proc", 'PATH': os.environ["PATH"]},
        )


def send_ethtool_ioctl_mock(iface, sckt, data):
    for input, result in common.ETHTOOL_IOCTL_INPUTS_OUTPUTS.items():
        if input == (iface, data.tobytes() if PY3 else data.tostring()):
            data[:] = array.array('B', [])
            data.frombytes(result) if PY3 else data.fromstring(result)
            return
    raise ValueError("Couldn't match any iface/data combination in the test data")


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ena(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('eth0')
    assert (driver_name, driver_version) == ('ena', '5.11.0-1022-aws')
    assert check._get_ena_metrics(stats_names, stats) == {
        'aws.ec2.bw_in_allowance_exceeded': 0,
        'aws.ec2.bw_out_allowance_exceeded': 0,
        'aws.ec2.conntrack_allowance_exceeded': 0,
        'aws.ec2.linklocal_allowance_exceeded': 0,
        'aws.ec2.pps_allowance_exceeded': 0,
    }


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ethtool_metrics_ena(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('eth0')
    assert (driver_name, driver_version) == ('ena', '5.11.0-1022-aws')
    assert check._get_ethtool_metrics(driver_name, stats_names, stats) == ENA_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ethtool_metrics_virtio(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('virtio')
    assert (driver_name, driver_version) == ('virtio_net', '1.0.0')
    assert check._get_ethtool_metrics(driver_name, stats_names, stats) == VIRTIO_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ethtool_metrics_hv_netvsc(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('hv_netvsc')
    assert (driver_name, driver_version) == ('hv_netvsc', '5.8.0-1042-azure')
    assert check._get_ethtool_metrics(driver_name, stats_names, stats) == HV_NETVSC_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ethtool_metrics_gve(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('gve')
    assert (driver_name, driver_version) == ('gve', '1.0.0')
    assert check._get_ethtool_metrics(driver_name, stats_names, stats) == GVE_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_submit_ena(send_ethtool_ioctl, check, aggregator):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check._collect_ethtool_stats = True
    check._collect_ena_metrics = True
    check._collect_ethtool_metrics = False
    check._excluded_ifaces = []
    check._exclude_iface_re = ''
    check._handle_ethtool_stats('eth0', [])

    expected_metrics = [
        'system.net.aws.ec2.bw_in_allowance_exceeded',
        'system.net.aws.ec2.bw_out_allowance_exceeded',
        'system.net.aws.ec2.conntrack_allowance_exceeded',
        'system.net.aws.ec2.linklocal_allowance_exceeded',
        'system.net.aws.ec2.pps_allowance_exceeded',
    ]

    for m in expected_metrics:
        aggregator.assert_metric(
            m, count=1, value=0, tags=['device:eth0', 'driver_name:ena', 'driver_version:5.11.0-1022-aws']
        )


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_submit_ena_ethtool_metrics(send_ethtool_ioctl, check, aggregator):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check._collect_ethtool_stats = True
    check._collect_ena_metrics = False
    check._collect_ethtool_metrics = True
    check._excluded_ifaces = []
    check._exclude_iface_re = ''
    check._handle_ethtool_stats('eth0', [])

    for tag, metrics in iteritems(ENA_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:eth0', 'driver_name:ena', 'driver_version:5.11.0-1022-aws', tag],
            )


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_submit_hv_netvsc_ethtool_metrics(send_ethtool_ioctl, check, aggregator):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check._collect_ethtool_stats = True
    check._collect_ena_metrics = False
    check._collect_ethtool_metrics = True
    check._excluded_ifaces = []
    check._exclude_iface_re = ''
    check._handle_ethtool_stats('hv_netvsc', [])

    for tag, metrics in iteritems(HV_NETVSC_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:hv_netvsc', 'driver_name:hv_netvsc', 'driver_version:5.8.0-1042-azure', tag],
            )


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_submit_gve_ethtool_metrics(send_ethtool_ioctl, check, aggregator):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check._collect_ethtool_stats = True
    check._collect_ena_metrics = False
    check._collect_ethtool_metrics = True
    check._excluded_ifaces = []
    check._exclude_iface_re = ''
    check._handle_ethtool_stats('gve', [])

    for tag, metrics in iteritems(GVE_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:gve', 'driver_name:gve', 'driver_version:1.0.0', tag],
            )


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.network.Network._send_ethtool_ioctl')
def test_collect_ena_values_not_present(send_ethtool_ioctl, check):
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check._fetch_ethtool_stats('enp0s3')
    assert (driver_name, driver_version) == (None, None)
    assert check._get_ena_metrics(stats_names, stats) == {}


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('fcntl.ioctl')
def test_collect_ena_unsupported_on_iface(ioctl_mock, check, caplog):
    caplog.set_level(logging.DEBUG)
    ioctl_mock.side_effect = OSError('mock error')
    _, _, _, _ = check._fetch_ethtool_stats('eth0')
    assert 'OSError while trying to collect ethtool metrics for interface eth0: mock error' in caplog.text


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_queue_num(check):
    queue_name, metric_name = check._parse_ethtool_queue_num('queue_0_tx_cnt')
    assert queue_name == 'queue:0'
    assert metric_name == 'tx_cnt'

    queue_name, metric_name = check._parse_ethtool_queue_num('queue_10_tx_doorbells')
    assert queue_name == 'queue:10'
    assert metric_name == 'tx_doorbells'

    queue_name, metric_name = check._parse_ethtool_queue_num('aqueue_10_tx_doorbells')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_num('tx_doorbells_queue_')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_num('tx_doorbells_bqueue_')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_num('tx_doorbells_queue')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_num('rx_queue_0_packets')
    assert queue_name == 'queue:0'
    assert metric_name == 'rx_packets'

    queue_name, metric_name = check._parse_ethtool_queue_num('rx_queue_123_packets')
    assert queue_name == 'queue:123'
    assert metric_name == 'rx_packets'


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_cpu_num(check):
    cpu_name, metric_name = check._parse_ethtool_cpu_num('cpu0_rx_bytes')
    assert cpu_name == 'cpu:0'
    assert metric_name == 'rx_bytes'

    cpu_name, metric_name = check._parse_ethtool_cpu_num('cpu431_rx_bytes')
    assert cpu_name == 'cpu:431'
    assert metric_name == 'rx_bytes'

    cpu_name, metric_name = check._parse_ethtool_cpu_num('acpu431_rx_bytes')
    assert cpu_name is None
    assert metric_name is None

    cpu_name, metric_name = check._parse_ethtool_cpu_num('cpu_rx_bytes')
    assert cpu_name is None
    assert metric_name is None

    cpu_name, metric_name = check._parse_ethtool_cpu_num('rx_cpu_bytes')
    assert cpu_name is None
    assert metric_name is None


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_queue_array(check):
    queue_name, metric_name = check._parse_ethtool_queue_array('tx_wake[0]')
    assert queue_name == 'queue:0'
    assert metric_name == 'tx_wake'

    queue_name, metric_name = check._parse_ethtool_queue_array('tx_dma_mapping_error[123]')
    assert queue_name == 'queue:123'
    assert metric_name == 'tx_dma_mapping_error'

    queue_name, metric_name = check._parse_ethtool_queue_array('tx_wake[0]]')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_array('tx[_wake[0]')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = check._parse_ethtool_queue_array('[1]tx_wake[0]')
    assert queue_name is None
    assert metric_name is None
