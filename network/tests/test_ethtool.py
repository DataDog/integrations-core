# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import array
import copy
import logging
import platform

import mock
import pytest
from six import PY3, iteritems

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.network import ethtool

from . import common

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


def send_ethtool_ioctl_mock(iface, sckt, data):
    for input, result in common.ETHTOOL_IOCTL_INPUTS_OUTPUTS.items():
        if input == (iface, data.tobytes() if PY3 else data.tostring()):
            data[:] = array.array('B', [])
            data.frombytes(result) if PY3 else data.fromstring(result)
            return
    raise ValueError("Couldn't match any iface/data combination in the test data")


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ena(is_linux, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('eth0')
    assert (driver_name, driver_version) == ('ena', '5.11.0-1022-aws')
    assert ethtool.get_ena_metrics(stats_names, stats) == {
        'aws.ec2.bw_in_allowance_exceeded': 0,
        'aws.ec2.bw_out_allowance_exceeded': 0,
        'aws.ec2.conntrack_allowance_exceeded': 0,
        'aws.ec2.linklocal_allowance_exceeded': 0,
        'aws.ec2.pps_allowance_exceeded': 0,
        'aws.ec2.conntrack_allowance_available': 0,
    }


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ethtool_metrics_ena(is_linux, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('eth0')
    assert (driver_name, driver_version) == ('ena', '5.11.0-1022-aws')
    assert ethtool.get_ethtool_metrics(driver_name, stats_names, stats) == ENA_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ethtool_metrics_virtio(is_linux, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('virtio')
    assert (driver_name, driver_version) == ('virtio_net', '1.0.0')
    assert ethtool.get_ethtool_metrics(driver_name, stats_names, stats) == VIRTIO_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ethtool_metrics_hv_netvsc(is_linu, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('hv_netvsc')
    assert (driver_name, driver_version) == ('hv_netvsc', '5.8.0-1042-azure')
    assert ethtool.get_ethtool_metrics(driver_name, stats_names, stats) == HV_NETVSC_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ethtool_metrics_gve(is_linux, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)
    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('gve')
    assert (driver_name, driver_version) == ('gve', '1.0.0')
    assert ethtool.get_ethtool_metrics(driver_name, stats_names, stats) == GVE_ETHTOOL_VALUES


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_submit_ena(is_linux, is_bsd, send_ethtool_ioctl, check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_aws_ena_metrics'] = True
    check_instance = check(instance)

    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check_instance._handle_ethtool_stats('eth0', [])

    expected_metrics = [
        'system.net.aws.ec2.bw_in_allowance_exceeded',
        'system.net.aws.ec2.bw_out_allowance_exceeded',
        'system.net.aws.ec2.conntrack_allowance_exceeded',
        'system.net.aws.ec2.linklocal_allowance_exceeded',
        'system.net.aws.ec2.pps_allowance_exceeded',
        'system.net.aws.ec2.conntrack_allowance_available',
    ]
    for m in expected_metrics:
        aggregator.assert_metric(
            m, count=1, value=0, tags=['device:eth0', 'driver_name:ena', 'driver_version:5.11.0-1022-aws']
        )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_submit_ena_ethtool_metrics(is_linux, is_bsd, send_ethtool_ioctl, check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_ethtool_metrics'] = True
    check_instance = check(instance)

    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check_instance._handle_ethtool_stats('eth0', [])

    for tag, metrics in iteritems(ENA_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:eth0', 'driver_name:ena', 'driver_version:5.11.0-1022-aws', tag],
            )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_submit_hv_netvsc_ethtool_metrics(is_linux, is_bsd, send_ethtool_ioctl, check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_ethtool_metrics'] = True
    check_instance = check(instance)

    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check_instance._handle_ethtool_stats('hv_netvsc', [])

    for tag, metrics in iteritems(HV_NETVSC_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:hv_netvsc', 'driver_name:hv_netvsc', 'driver_version:5.8.0-1042-azure', tag],
            )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_submit_gve_ethtool_metrics(is_linux, is_bsd, send_ethtool_ioctl, check, aggregator):
    instance = copy.deepcopy(common.INSTANCE)
    instance['collect_ethtool_metrics'] = True
    check_instance = check(instance)

    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    check_instance._handle_ethtool_stats('gve', [])

    for tag, metrics in iteritems(GVE_ETHTOOL_VALUES):
        for metric_suffix, value in iteritems(metrics):
            aggregator.assert_metric(
                'system.net.' + metric_suffix,
                count=1,
                value=value,
                tags=['device:gve', 'driver_name:gve', 'driver_version:1.0.0', tag],
            )
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('datadog_checks.network.ethtool._send_ethtool_ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ena_values_not_present(is_linux, is_bsd, send_ethtool_ioctl, check):
    check_instance = check(common.INSTANCE)

    send_ethtool_ioctl.side_effect = send_ethtool_ioctl_mock
    driver_name, driver_version, stats_names, stats = check_instance._fetch_ethtool_stats('enp0s3')
    assert (driver_name, driver_version) == (None, None)
    assert ethtool.get_ena_metrics(stats_names, stats) == {}


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
@mock.patch('fcntl.ioctl')
@mock.patch('datadog_checks.network.network.Platform.is_bsd', return_value=False)
@mock.patch('datadog_checks.network.network.Platform.is_linux', return_value=True)
def test_collect_ena_unsupported_on_iface(is_linux, is_bsd, ioctl_mock, check, caplog):
    check_instance = check(common.INSTANCE)
    caplog.set_level(logging.DEBUG)
    ioctl_mock.side_effect = OSError('mock error')

    _, _, _, _ = check_instance._fetch_ethtool_stats('eth0')

    assert 'OSError while trying to collect ethtool metrics for interface eth0: mock error' in caplog.text


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_queue_num():
    queue_name, metric_name = ethtool._parse_ethtool_queue_num('queue_0_tx_cnt')
    assert queue_name == 'queue:0'
    assert metric_name == 'tx_cnt'

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('queue_10_tx_doorbells')
    assert queue_name == 'queue:10'
    assert metric_name == 'tx_doorbells'

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('aqueue_10_tx_doorbells')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('tx_doorbells_queue_')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('tx_doorbells_bqueue_')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('tx_doorbells_queue')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('rx_queue_0_packets')
    assert queue_name == 'queue:0'
    assert metric_name == 'rx_packets'

    queue_name, metric_name = ethtool._parse_ethtool_queue_num('rx_queue_123_packets')
    assert queue_name == 'queue:123'
    assert metric_name == 'rx_packets'


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_cpu_num():
    cpu_name, metric_name = ethtool._parse_ethtool_cpu_num('cpu0_rx_bytes')
    assert cpu_name == 'cpu:0'
    assert metric_name == 'rx_bytes'

    cpu_name, metric_name = ethtool._parse_ethtool_cpu_num('cpu431_rx_bytes')
    assert cpu_name == 'cpu:431'
    assert metric_name == 'rx_bytes'

    cpu_name, metric_name = ethtool._parse_ethtool_cpu_num('acpu431_rx_bytes')
    assert cpu_name is None
    assert metric_name is None

    cpu_name, metric_name = ethtool._parse_ethtool_cpu_num('cpu_rx_bytes')
    assert cpu_name is None
    assert metric_name is None

    cpu_name, metric_name = ethtool._parse_ethtool_cpu_num('rx_cpu_bytes')
    assert cpu_name is None
    assert metric_name is None


@pytest.mark.skipif(platform.system() == 'Windows', reason="Only runs on Unix systems")
def test_parse_queue_array():
    queue_name, metric_name = ethtool._parse_ethtool_queue_array('tx_wake[0]')
    assert queue_name == 'queue:0'
    assert metric_name == 'tx_wake'

    queue_name, metric_name = ethtool._parse_ethtool_queue_array('tx_dma_mapping_error[123]')
    assert queue_name == 'queue:123'
    assert metric_name == 'tx_dma_mapping_error'

    queue_name, metric_name = ethtool._parse_ethtool_queue_array('tx_wake[0]]')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_array('tx[_wake[0]')
    assert queue_name is None
    assert metric_name is None

    queue_name, metric_name = ethtool._parse_ethtool_queue_array('[1]tx_wake[0]')
    assert queue_name is None
    assert metric_name is None
