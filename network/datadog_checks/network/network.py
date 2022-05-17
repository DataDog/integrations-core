# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Collects network metrics.
"""

import array
import distutils.spawn
import os
import re
import socket
import struct
from collections import defaultdict

import psutil
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.common import pattern_filter
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

try:
    import fcntl
except ImportError:
    fcntl = None

if PY3:
    long = int


BSD_TCP_METRICS = [
    (re.compile(r"^\s*(\d+) data packets \(\d+ bytes\) retransmitted\s*$"), 'system.net.tcp.retrans_packs'),
    (re.compile(r"^\s*(\d+) packets sent\s*$"), 'system.net.tcp.sent_packs'),
    (re.compile(r"^\s*(\d+) packets received\s*$"), 'system.net.tcp.rcv_packs'),
]

SOLARIS_TCP_METRICS = [
    (re.compile(r"\s*tcpRetransSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.retrans_segs'),
    (re.compile(r"\s*tcpOutDataSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.in_segs'),
    (re.compile(r"\s*tcpInSegs\s*=\s*(\d+)\s*"), 'system.net.tcp.out_segs'),
]

# constants for extracting ethtool data via ioctl
SIOCETHTOOL = 0x8946
ETHTOOL_GDRVINFO = 0x00000003
ETHTOOL_GSTRINGS = 0x0000001B
ETHTOOL_GSSET_INFO = 0x00000037
ETHTOOL_GSTATS = 0x0000001D
ETH_SS_STATS = 0x1
ETH_GSTRING_LEN = 32

# ENA metrics that we're collecting
# https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Agent-network-performance.html
ENA_METRIC_PREFIX = "aws.ec2."
ENA_METRIC_NAMES = [
    "bw_in_allowance_exceeded",
    "bw_out_allowance_exceeded",
    "conntrack_allowance_exceeded",
    "linklocal_allowance_exceeded",
    "pps_allowance_exceeded",
]

ETHTOOL_METRIC_NAMES = {
    # Example ethtool -S iface with ena driver:
    # queue_0_tx_cnt: 123665045
    # queue_0_tx_bytes: 34567996008
    # queue_0_tx_queue_stop: 0
    # queue_0_tx_queue_wakeup: 0
    # queue_0_tx_dma_mapping_err: 0
    # queue_0_tx_linearize: 0
    # queue_0_tx_linearize_failed: 0
    # queue_0_tx_napi_comp: 131999879
    # queue_0_tx_tx_poll: 131999896
    # queue_0_tx_doorbells: 117093522
    # queue_0_tx_prepare_ctx_err: 0
    # queue_0_tx_bad_req_id: 0
    # queue_0_tx_llq_buffer_copy: 87883427
    # queue_0_tx_missed_tx: 0
    # queue_0_tx_unmask_interrupt: 131999879
    # queue_0_rx_cnt: 15934470
    # queue_0_rx_bytes: 27955854239
    # queue_0_rx_rx_copybreak_pkt: 8504787
    # queue_0_rx_csum_good: 15923815
    # queue_0_rx_refil_partial: 0
    # queue_0_rx_bad_csum: 0
    # queue_0_rx_page_alloc_fail: 0
    # queue_0_rx_skb_alloc_fail: 0
    # queue_0_rx_dma_mapping_err: 0
    # queue_0_rx_bad_desc_num: 0
    # queue_0_rx_bad_req_id: 0
    # queue_0_rx_empty_rx_ring: 0
    # queue_0_rx_csum_unchecked: 0
    # queue_0_rx_xdp_aborted: 0
    # queue_0_rx_xdp_drop: 0
    # queue_0_rx_xdp_pass: 0
    # queue_0_rx_xdp_tx: 0
    # queue_0_rx_xdp_invalid: 0
    # queue_0_rx_xdp_redirect: 0
    'ena': [
        "rx_bad_csum",
        "rx_bad_desc_num",
        "rx_bad_req_id",
        "rx_bytes",
        "rx_cnt",
        "rx_csum_good",
        "rx_csum_unchecked",
        "rx_dma_mapping_err",
        "rx_empty_rx_ring",
        "rx_page_alloc_fail",
        "rx_refil_partial",
        "rx_rx_copybreak_pkt",
        "rx_skb_alloc_fail",
        "rx_xdp_aborted",
        "rx_xdp_drop",
        "rx_xdp_invalid",
        "rx_xdp_pass",
        "rx_xdp_redirect",
        "rx_xdp_tx",
        "tx_bad_req_id",
        "tx_bytes",
        "tx_cnt",
        "tx_dma_mapping_err",
        "tx_doorbells",
        "tx_linearize",
        "tx_linearize_failed",
        "tx_llq_buffer_copy",
        "tx_missed_tx",
        "tx_napi_comp",
        "tx_prepare_ctx_err",
        "tx_queue_stop",
        "tx_queue_wakeup",
        "tx_tx_poll",
        "tx_unmask_interrupt",
    ],
    # Example of output of ethtool -S iface with virtio driver:
    # rx_queue_0_packets: 16591239
    # rx_queue_0_bytes: 51217084980
    # rx_queue_0_drops: 0
    # rx_queue_0_xdp_packets: 0
    # rx_queue_0_xdp_tx: 0
    # rx_queue_0_xdp_redirects: 0
    # rx_queue_0_xdp_drops: 0
    # rx_queue_0_kicks: 408
    # tx_queue_0_packets: 5246609
    # tx_queue_0_bytes: 8455122678
    # tx_queue_0_xdp_tx: 0
    # tx_queue_0_xdp_tx_drops: 0
    # tx_queue_0_kicks: 81
    'virtio_net': [
        "rx_drops",
        "rx_kicks",
        "rx_packets",
        "rx_bytes",
        "rx_xdp_drops",
        "rx_xdp_packets",
        "rx_xdp_redirects",
        "rx_xdp_tx",
        "tx_kicks",
        "tx_packets",
        "tx_bytes",
        "tx_xdp_tx",
        "tx_xdp_tx_drops",
    ],
    # Example of output of ethtool -S iface with hv_netvsc driver:
    #  tx_queue_0_packets: 408
    #  tx_queue_0_bytes: 62025
    #  rx_queue_0_packets: 91312
    #  rx_queue_0_bytes: 64734440
    #  rx_queue_0_xdp_drop: 0
    #  tx_queue_1_packets: 0
    #  tx_queue_1_bytes: 0
    #  rx_queue_1_packets: 90945
    #  rx_queue_1_bytes: 66515649
    #  rx_queue_1_xdp_drop: 0
    #  cpu0_rx_packets: 90021
    #  cpu0_rx_bytes: 60954160
    #  cpu0_tx_packets: 2307011
    #  cpu0_tx_bytes: 996614053
    #  cpu0_vf_rx_packets: 762
    #  cpu0_vf_rx_bytes: 1730037
    #  cpu0_vf_tx_packets: 2307011
    #  cpu0_vf_tx_bytes: 996614053
    #  cpu1_rx_packets: 376562
    #  cpu1_rx_bytes: 665669328
    #  cpu1_tx_packets: 3176489
    #  cpu1_tx_bytes: 436967327
    #  cpu1_vf_rx_packets: 266749
    #  cpu1_vf_rx_bytes: 593435159
    #  cpu1_vf_tx_packets: 3176489
    #  cpu1_vf_tx_bytes: 436967327
    'hv_netvsc': [
        # Per queue metrics
        'tx_packets',
        'tx_bytes',
        'rx_packets',
        'rx_bytes',
        'rx_xdp_drop',
        # Per cpu metrics
        'vf_rx_packets',
        'vf_rx_bytes',
        'vf_tx_packets',
        'vf_tx_bytes',
    ],
    # ethtool output on an instance with gvnic:
    #      rx_packets: 584088
    #      tx_packets: 17643
    #      rx_bytes: 850689306
    #      tx_bytes: 1420648
    #      rx_dropped: 0
    #      tx_dropped: 0
    #      tx_timeouts: 0
    #      rx_skb_alloc_fail: 0
    #      rx_buf_alloc_fail: 0
    #      rx_desc_err_dropped_pkt: 0
    #      interface_up_cnt: 1
    #      interface_down_cnt: 0
    #      reset_cnt: 0
    #      page_alloc_fail: 0
    #      dma_mapping_error: 0
    #      stats_report_trigger_cnt: 0
    #      rx_posted_desc[0]: 1937
    #      rx_completed_desc[0]: 913
    #      rx_bytes[0]: 558287
    #      rx_dropped_pkt[0]: 0
    #      rx_copybreak_pkt[0]: 538
    #      rx_copied_pkt[0]: 538
    #      rx_queue_drop_cnt[0]: 0
    #      rx_no_buffers_posted[0]: 0
    #      rx_drops_packet_over_mru[0]: 0
    #      rx_drops_invalid_checksum[0]: 0
    #      rx_posted_desc[1]: 263357
    #      rx_completed_desc[1]: 262333
    #      rx_bytes[1]: 382572185
    #      rx_dropped_pkt[1]: 0
    #      rx_copybreak_pkt[1]: 1036
    #      rx_copied_pkt[1]: 172309
    #      rx_queue_drop_cnt[1]: 0
    #      rx_no_buffers_posted[1]: 0
    #      rx_drops_packet_over_mru[1]: 0
    #      rx_drops_invalid_checksum[1]: 0
    #      tx_posted_desc[0]: 2829
    #      tx_completed_desc[0]: 2829
    #      tx_bytes[0]: 221475
    #      tx_wake[0]: 0
    #      tx_stop[0]: 0
    #      tx_event_counter[0]: 2829
    #      tx_dma_mapping_error[0]: 0
    #      tx_posted_desc[1]: 7051
    #      tx_completed_desc[1]: 7051
    #      tx_bytes[1]: 522327
    #      tx_wake[1]: 0
    #      tx_stop[1]: 0
    #      tx_event_counter[1]: 7051
    #      tx_dma_mapping_error[1]: 0
    #      adminq_prod_cnt: 25
    #      adminq_cmd_fail: 0
    #      adminq_timeouts: 0
    #      adminq_describe_device_cnt: 1
    #      adminq_cfg_device_resources_cnt: 1
    #      adminq_register_page_list_cnt: 8
    #      adminq_unregister_page_list_cnt: 0
    #      adminq_create_tx_queue_cnt: 4
    #      adminq_create_rx_queue_cnt: 4
    #      adminq_destroy_tx_queue_cnt: 0
    #      adminq_destroy_rx_queue_cnt: 0
    #      adminq_dcfg_device_resources_cnt: 0
    #      adminq_set_driver_parameter_cnt: 0
    #      adminq_report_stats_cnt: 1
    #      adminq_report_link_speed_cnt: 6
    'gve': [
        'rx_posted_desc',
        'rx_completed_desc',
        'rx_bytes',
        'rx_dropped_pkt',
        'rx_copybreak_pkt',
        'rx_copied_pkt',
        'rx_queue_drop_cnt',
        'rx_no_buffers_posted',
        'rx_drops_packet_over_mru',
        'rx_drops_invalid_checksum',
        'tx_posted_desc',
        'tx_completed_desc',
        'tx_bytes',
        'tx_wake',
        'tx_stop',
        'tx_event_counter',
        'tx_dma_mapping_error',
    ],
}

ETHTOOL_GLOBAL_METRIC_NAMES = {
    'ena': [
        'tx_timeout',
        'suspend',
        'resume',
        'wd_expired',
    ],
    'hv_netvsc': [
        'tx_scattered',
        'tx_no_memory',
        'tx_no_space',
        'tx_too_big',
        'tx_busy',
        'tx_send_full',
        'rx_comp_busy',
        'rx_no_memory',
        'stop_queue',
        'wake_queue',
    ],
    'gve': [
        'tx_timeouts',
        'rx_skb_alloc_fail',
        'rx_buf_alloc_fail',
        'rx_desc_err_dropped_pkt',
        'page_alloc_fail',
        'dma_mapping_error',
    ],
}


class Network(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    PSUTIL_TYPE_MAPPING = {socket.SOCK_STREAM: 'tcp', socket.SOCK_DGRAM: 'udp'}

    PSUTIL_FAMILY_MAPPING = {socket.AF_INET: '4', socket.AF_INET6: '6'}

    def check(self, instance):
        if instance is None:
            instance = {}

        self._excluded_ifaces = instance.get('excluded_interfaces', [])
        if not isinstance(self._excluded_ifaces, list):
            raise ConfigurationError(
                "Expected 'excluded_interfaces' to be a list, got '{}'".format(type(self._excluded_ifaces).__name__)
            )

        self._collect_cx_state = instance.get('collect_connection_state', False)
        self._collect_cx_queues = instance.get('collect_connection_queues', False)
        self._collect_rate_metrics = instance.get('collect_rate_metrics', True)
        self._collect_count_metrics = instance.get('collect_count_metrics', False)
        self._collect_ena_metrics = instance.get('collect_aws_ena_metrics', False)
        self._collect_ethtool_metrics = instance.get('collect_ethtool_metrics', False)

        self._collect_ethtool_stats = self._collect_ena_metrics or self._collect_ethtool_metrics
        if fcntl is None and self._collect_ethtool_stats:
            raise ConfigurationError(
                "fcntl not importable, collect_aws_ena_metrics and collect_ethtool_metrics should be disabled"
            )

        # This decides whether we should split or combine connection states,
        # along with a few other things
        self._setup_metrics(instance)

        self._exclude_iface_re = None
        exclude_re = instance.get('excluded_interface_re', None)
        if exclude_re:
            self.log.debug("Excluding network devices matching: %s", exclude_re)
            self._exclude_iface_re = re.compile(exclude_re)

        if Platform.is_linux():
            self._check_linux(instance)
        elif Platform.is_bsd():
            self._check_bsd(instance)
        elif Platform.is_solaris():
            self._check_solaris(instance)
        elif Platform.is_windows():
            self._check_psutil(instance)

    def _setup_metrics(self, instance):
        self._combine_connection_states = instance.get('combine_connection_states', True)

        if self._combine_connection_states:
            self.cx_state_gauge = {
                ('udp4', 'connections'): 'system.net.udp4.connections',
                ('udp6', 'connections'): 'system.net.udp6.connections',
                ('tcp4', 'established'): 'system.net.tcp4.established',
                ('tcp4', 'opening'): 'system.net.tcp4.opening',
                ('tcp4', 'closing'): 'system.net.tcp4.closing',
                ('tcp4', 'listening'): 'system.net.tcp4.listening',
                ('tcp4', 'time_wait'): 'system.net.tcp4.time_wait',
                ('tcp6', 'established'): 'system.net.tcp6.established',
                ('tcp6', 'opening'): 'system.net.tcp6.opening',
                ('tcp6', 'closing'): 'system.net.tcp6.closing',
                ('tcp6', 'listening'): 'system.net.tcp6.listening',
                ('tcp6', 'time_wait'): 'system.net.tcp6.time_wait',
            }

            self.tcp_states = {
                "ss": {
                    "ESTAB": "established",
                    "SYN-SENT": "opening",
                    "SYN-RECV": "opening",
                    "FIN-WAIT-1": "closing",
                    "FIN-WAIT-2": "closing",
                    "TIME-WAIT": "time_wait",
                    "UNCONN": "closing",
                    "CLOSE-WAIT": "closing",
                    "LAST-ACK": "closing",
                    "LISTEN": "listening",
                    "CLOSING": "closing",
                },
                "netstat": {
                    "ESTABLISHED": "established",
                    "SYN_SENT": "opening",
                    "SYN_RECV": "opening",
                    "FIN_WAIT1": "closing",
                    "FIN_WAIT2": "closing",
                    "TIME_WAIT": "time_wait",
                    "CLOSE": "closing",
                    "CLOSE_WAIT": "closing",
                    "LAST_ACK": "closing",
                    "LISTEN": "listening",
                    "CLOSING": "closing",
                },
                "psutil": {
                    psutil.CONN_ESTABLISHED: "established",
                    psutil.CONN_SYN_SENT: "opening",
                    psutil.CONN_SYN_RECV: "opening",
                    psutil.CONN_FIN_WAIT1: "closing",
                    psutil.CONN_FIN_WAIT2: "closing",
                    psutil.CONN_TIME_WAIT: "time_wait",
                    psutil.CONN_CLOSE: "closing",
                    psutil.CONN_CLOSE_WAIT: "closing",
                    psutil.CONN_LAST_ACK: "closing",
                    psutil.CONN_LISTEN: "listening",
                    psutil.CONN_CLOSING: "closing",
                    psutil.CONN_NONE: "connections",  # CONN_NONE is always returned for udp connections
                },
            }
        else:
            self.cx_state_gauge = {
                ('udp4', 'connections'): 'system.net.udp4.connections',
                ('udp6', 'connections'): 'system.net.udp6.connections',
                ('tcp4', 'estab'): 'system.net.tcp4.estab',
                ('tcp4', 'syn_sent'): 'system.net.tcp4.syn_sent',
                ('tcp4', 'syn_recv'): 'system.net.tcp4.syn_recv',
                ('tcp4', 'fin_wait_1'): 'system.net.tcp4.fin_wait_1',
                ('tcp4', 'fin_wait_2'): 'system.net.tcp4.fin_wait_2',
                ('tcp4', 'time_wait'): 'system.net.tcp4.time_wait',
                ('tcp4', 'unconn'): 'system.net.tcp4.unconn',
                ('tcp4', 'close'): 'system.net.tcp4.close',
                ('tcp4', 'close_wait'): 'system.net.tcp4.close_wait',
                ('tcp4', 'closing'): 'system.net.tcp4.closing',
                ('tcp4', 'listen'): 'system.net.tcp4.listen',
                ('tcp4', 'last_ack'): 'system.net.tcp4.time_wait',
                ('tcp6', 'estab'): 'system.net.tcp6.estab',
                ('tcp6', 'syn_sent'): 'system.net.tcp6.syn_sent',
                ('tcp6', 'syn_recv'): 'system.net.tcp6.syn_recv',
                ('tcp6', 'fin_wait_1'): 'system.net.tcp6.fin_wait_1',
                ('tcp6', 'fin_wait_2'): 'system.net.tcp6.fin_wait_2',
                ('tcp6', 'time_wait'): 'system.net.tcp6.time_wait',
                ('tcp6', 'unconn'): 'system.net.tcp6.unconn',
                ('tcp6', 'close'): 'system.net.tcp6.close',
                ('tcp6', 'close_wait'): 'system.net.tcp6.close_wait',
                ('tcp6', 'closing'): 'system.net.tcp6.closing',
                ('tcp6', 'listen'): 'system.net.tcp6.listen',
                ('tcp6', 'last_ack'): 'system.net.tcp6.time_wait',
            }

            self.tcp_states = {
                "ss": {
                    "ESTAB": "estab",
                    "SYN-SENT": "syn_sent",
                    "SYN-RECV": "syn_recv",
                    "FIN-WAIT-1": "fin_wait_1",
                    "FIN-WAIT-2": "fin_wait_2",
                    "TIME-WAIT": "time_wait",
                    "UNCONN": "unconn",
                    "CLOSE-WAIT": "close_wait",
                    "LAST-ACK": "last_ack",
                    "LISTEN": "listen",
                    "CLOSING": "closing",
                },
                "netstat": {
                    "ESTABLISHED": "estab",
                    "SYN_SENT": "syn_sent",
                    "SYN_RECV": "syn_recv",
                    "FIN_WAIT1": "fin_wait_1",
                    "FIN_WAIT2": "fin_wait_2",
                    "TIME_WAIT": "time_wait",
                    "CLOSE": "close",
                    "CLOSE_WAIT": "close_wait",
                    "LAST_ACK": "last_ack",
                    "LISTEN": "listen",
                    "CLOSING": "closing",
                },
                "psutil": {
                    psutil.CONN_ESTABLISHED: "estab",
                    psutil.CONN_SYN_SENT: "syn_sent",
                    psutil.CONN_SYN_RECV: "syn_recv",
                    psutil.CONN_FIN_WAIT1: "fin_wait_1",
                    psutil.CONN_FIN_WAIT2: "fin_wait_2",
                    psutil.CONN_TIME_WAIT: "time_wait",
                    psutil.CONN_CLOSE: "close",
                    psutil.CONN_CLOSE_WAIT: "close_wait",
                    psutil.CONN_LAST_ACK: "last_ack",
                    psutil.CONN_LISTEN: "listen",
                    psutil.CONN_CLOSING: "closing",
                    psutil.CONN_NONE: "connections",  # CONN_NONE is always returned for udp connections
                },
            }

    def _submit_netmetric(self, metric, value, tags=None):
        if self._collect_rate_metrics:
            self.rate(metric, value, tags=tags)
        if self._collect_count_metrics:
            self.monotonic_count('{}.count'.format(metric), value, tags=tags)

    def _submit_netmetric_gauge(self, metric, value, tags=None):
        self.gauge(metric, value, tags=tags)

    def _submit_devicemetrics(self, iface, vals_by_metric, tags):
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return False

        # adding the device to the tags as device_name is deprecated
        metric_tags = [] if tags is None else tags[:]
        metric_tags.append('device:{}'.format(iface))

        expected_metrics = self._get_expected_metrics()
        for m in expected_metrics:
            assert m in vals_by_metric
        assert len(vals_by_metric) == len(expected_metrics)

        count = 0
        for metric, val in iteritems(vals_by_metric):
            self.rate('system.net.%s' % metric, val, tags=metric_tags)
            count += 1
        self.log.debug("tracked %s network metrics for interface %s", count, iface)

    def _get_expected_metrics(self):
        expected_metrics = [
            'bytes_rcvd',
            'bytes_sent',
            'packets_in.count',
            'packets_in.error',
            'packets_out.count',
            'packets_out.error',
        ]
        if Platform.is_linux() or Platform.is_windows():
            expected_metrics.extend(
                [
                    'packets_in.drop',
                    'packets_out.drop',
                ]
            )
        return expected_metrics

    def _submit_ena_metrics(self, iface, vals_by_metric, tags):
        if not vals_by_metric:
            return
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return

        metric_tags = [] if tags is None else tags[:]
        metric_tags.append('device:{}'.format(iface))

        allowed = [ENA_METRIC_PREFIX + m for m in ENA_METRIC_NAMES]
        for m in vals_by_metric:
            assert m in allowed

        count = 0
        for metric, val in iteritems(vals_by_metric):
            self.gauge('system.net.%s' % metric, val, tags=metric_tags)
            count += 1
        self.log.debug("tracked %s network ena metrics for interface %s", count, iface)

    def _submit_ethtool_metrics(self, iface, ethtool_metrics, base_tags):
        if not ethtool_metrics:
            return
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return

        base_tags_with_device = [] if base_tags is None else base_tags[:]
        base_tags_with_device.append('device:{}'.format(iface))

        count = 0
        for ethtool_tag, metric_map in iteritems(ethtool_metrics):
            tags = base_tags_with_device + [ethtool_tag]
            for metric, val in iteritems(metric_map):
                self.monotonic_count('system.net.%s' % metric, val, tags=tags)
                count += 1
        self.log.debug("tracked %s network ethtool metrics for interface %s", count, iface)

    def _parse_value(self, v):
        try:
            return long(v)
        except ValueError:
            return 0

    def _submit_regexed_values(self, output, regex_list, tags):
        lines = output.splitlines()
        for line in lines:
            for regex, metric in regex_list:
                value = re.match(regex, line)
                if value:
                    self._submit_netmetric(metric, self._parse_value(value.group(1)), tags=tags)

    def _is_collect_cx_state_runnable(self, proc_location):
        """
        Determine if collect_connection_state is set and can effectively run.
        If self._collect_cx_state is True and a custom proc_location is provided, the system cannot
         run `ss` or `netstat` over a custom proc_location
        :param proc_location: str
        :return: bool
        """
        if self._collect_cx_state is False:
            return False

        if proc_location != "/proc":
            # If we have `ss`, we're fine with a non-standard `/proc` location
            if distutils.spawn.find_executable("ss") is None:
                self.warning(
                    "Cannot collect connection state: `ss` cannot be found and "
                    "currently with a custom /proc path: %s",
                    proc_location,
                )
                return False
            else:
                return True

        return True

    def _check_linux(self, instance):
        """
        _check_linux can be run inside a container and still collects the network metrics from the host
        For that procfs_path can be set to something like "/host/proc"
        When a custom procfs_path is set, the collect_connection_state option is ignored
        """
        proc_location = datadog_agent.get_config('procfs_path')
        if not proc_location:
            proc_location = '/proc'
        proc_location = proc_location.rstrip('/')
        custom_tags = instance.get('tags', [])

        self._get_iface_sys_metrics(custom_tags)
        net_proc_base_location = self._get_net_proc_base_location(proc_location)

        if self._is_collect_cx_state_runnable(net_proc_base_location):
            try:
                self.log.debug("Using `ss` to collect connection state")
                # Try using `ss` for increased performance over `netstat`
                ss_env = {"PROC_ROOT": net_proc_base_location}

                # By providing the environment variables in ss_env, the PATH will be overridden. In CentOS,
                # datadog-agent PATH is "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin", while sh PATH
                # will be '/usr/local/bin:/usr/bin'. In CentOS, ss is located in /sbin and /usr/sbin, not
                # in the sh PATH, which will result in network metric collection failure.
                #
                # The line below will set sh PATH explicitly as the datadog-agent PATH to fix that issue.
                if "PATH" in os.environ:
                    ss_env["PATH"] = os.environ["PATH"]

                metrics = self._get_metrics()
                for ip_version in ['4', '6']:
                    # Call `ss` for each IP version because there's no built-in way of distinguishing
                    # between the IP versions in the output
                    # Also calls `ss` for each protocol, because on some systems (e.g. Ubuntu 14.04), there is a
                    # bug that print `tcp` even if it's `udp`
                    # The `-H` flag isn't available on old versions of `ss`.
                    cmd = "ss --numeric --tcp --all --ipv{} | cut -d ' ' -f 1 | sort | uniq -c".format(ip_version)
                    output, _, _ = get_subprocess_output(["sh", "-c", cmd], self.log, env=ss_env)

                    # 7624 CLOSE-WAIT
                    #   72 ESTAB
                    #    9 LISTEN
                    #    1 State
                    #   37 TIME-WAIT
                    lines = output.splitlines()

                    self._parse_short_state_lines(lines, metrics, self.tcp_states['ss'], ip_version=ip_version)

                    cmd = "ss --numeric --udp --all --ipv{} | wc -l".format(ip_version)
                    output, _, _ = get_subprocess_output(["sh", "-c", cmd], self.log, env=ss_env)
                    metric = self.cx_state_gauge[('udp{}'.format(ip_version), 'connections')]
                    metrics[metric] = int(output) - 1  # Remove header

                    if self._collect_cx_queues:
                        cmd = "ss --numeric --tcp --all --ipv{}".format(ip_version)
                        output, _, _ = get_subprocess_output(["sh", "-c", cmd], self.log, env=ss_env)
                        for (state, recvq, sendq) in self._parse_queues("ss", output):
                            self.histogram('system.net.tcp.recv_q', recvq, custom_tags + ["state:" + state])
                            self.histogram('system.net.tcp.send_q', sendq, custom_tags + ["state:" + state])

                for metric, value in iteritems(metrics):
                    self.gauge(metric, value, tags=custom_tags)

            except OSError as e:
                self.log.info("`ss` invocation failed: %s. Using `netstat` as a fallback", str(e))
                output, _, _ = get_subprocess_output(["netstat", "-n", "-u", "-t", "-a"], self.log)
                lines = output.splitlines()
                # Active Internet connections (w/o servers)
                # Proto Recv-Q Send-Q Local Address           Foreign Address         State
                # tcp        0      0 46.105.75.4:80          79.220.227.193:2032     SYN_RECV
                # tcp        0      0 46.105.75.4:143         90.56.111.177:56867     ESTABLISHED
                # tcp        0      0 46.105.75.4:50468       107.20.207.175:443      TIME_WAIT
                # tcp6       0      0 46.105.75.4:80          93.15.237.188:58038     FIN_WAIT2
                # tcp6       0      0 46.105.75.4:80          79.220.227.193:2029     ESTABLISHED
                # udp        0      0 0.0.0.0:123             0.0.0.0:*
                # udp6       0      0 :::41458                :::*

                metrics = self._parse_linux_cx_state(lines[2:], self.tcp_states['netstat'], 5)
                for metric, value in iteritems(metrics):
                    self.gauge(metric, value, tags=custom_tags)

                if self._collect_cx_queues:
                    for (state, recvq, sendq) in self._parse_queues("netstat", output):
                        self.histogram('system.net.tcp.recv_q', recvq, custom_tags + ["state:" + state])
                        self.histogram('system.net.tcp.send_q', sendq, custom_tags + ["state:" + state])

            except SubprocessOutputEmptyError:
                self.log.exception("Error collecting connection states.")

        proc_dev_path = "{}/net/dev".format(net_proc_base_location)
        try:
            with open(proc_dev_path, 'r') as proc:
                lines = proc.readlines()
        except IOError:
            # On Openshift, /proc/net/snmp is only readable by root
            self.log.debug("Unable to read %s.", proc_dev_path)
            lines = []

        # Inter-|   Receive                                                 |  Transmit
        #  face |bytes     packets errs drop fifo frame compressed multicast|bytes       packets errs drop fifo colls carrier compressed # noqa: E501
        #     lo:45890956   112797   0    0    0     0          0         0    45890956   112797    0    0    0     0       0          0 # noqa: E501
        #   eth0:631947052 1042233   0   19    0   184          0      1206  1208625538  1320529    0    0    0     0       0          0 # noqa: E501
        #   eth1:       0        0   0    0    0     0          0         0           0        0    0    0    0     0       0          0 # noqa: E501
        for line in lines[2:]:
            cols = line.split(':', 1)
            x = cols[1].split()
            # Filter inactive interfaces
            if self._parse_value(x[0]) or self._parse_value(x[8]):
                iface = cols[0].strip()
                metrics = {
                    'bytes_rcvd': self._parse_value(x[0]),
                    'bytes_sent': self._parse_value(x[8]),
                    'packets_in.count': self._parse_value(x[1]),
                    'packets_in.drop': self._parse_value(x[3]),
                    'packets_in.error': self._parse_value(x[2]) + self._parse_value(x[3]),
                    'packets_out.count': self._parse_value(x[9]),
                    'packets_out.drop': self._parse_value(x[11]),
                    'packets_out.error': self._parse_value(x[10]) + self._parse_value(x[11]),
                }
                self._submit_devicemetrics(iface, metrics, custom_tags)
                self._handle_ethtool_stats(iface, custom_tags)

        netstat_data = {}
        for f in ['netstat', 'snmp']:
            proc_data_path = "{}/net/{}".format(net_proc_base_location, f)
            try:
                with open(proc_data_path, 'r') as netstat:
                    while True:
                        n_header = netstat.readline()
                        if not n_header:
                            break  # No more? Abort!
                        n_data = netstat.readline()

                        h_parts = n_header.strip().split(' ')
                        h_values = n_data.strip().split(' ')
                        ns_category = h_parts[0][:-1]
                        netstat_data[ns_category] = {}
                        # Turn the data into a dictionary
                        for idx, hpart in enumerate(h_parts[1:]):
                            netstat_data[ns_category][hpart] = h_values[idx + 1]
            except IOError:
                # On Openshift, /proc/net/snmp is only readable by root
                self.log.debug("Unable to read %s.", proc_data_path)

        nstat_metrics_names = {
            'Ip': {
                'InReceives': 'system.net.ip.in_receives',
                'InHdrErrors': 'system.net.ip.in_header_errors',
                'InAddrErrors': 'system.net.ip.in_addr_errors',
                'InUnknownProtos': 'system.net.ip.in_unknown_protos',
                'InDiscards': 'system.net.ip.in_discards',
                'InDelivers': 'system.net.ip.in_delivers',
                'OutRequests': 'system.net.ip.out_requests',
                'OutDiscards': 'system.net.ip.out_discards',
                'OutNoRoutes': 'system.net.ip.out_no_routes',
                'ForwDatagrams': 'system.net.ip.forwarded_datagrams',
                'ReasmTimeout': 'system.net.ip.reassembly_timeouts',
                'ReasmReqds': 'system.net.ip.reassembly_requests',
                'ReasmOKs': 'system.net.ip.reassembly_oks',
                'ReasmFails': 'system.net.ip.reassembly_fails',
                'FragOKs': 'system.net.ip.fragmentation_oks',
                'FragFails': 'system.net.ip.fragmentation_fails',
                'FragCreates': 'system.net.ip.fragmentation_creates',
            },
            'IpExt': {
                'InNoRoutes': 'system.net.ip.in_no_routes',
                'InTruncatedPkts': 'system.net.ip.in_truncated_pkts',
                'InCsumErrors': 'system.net.ip.in_csum_errors',
                'ReasmOverlaps': 'system.net.ip.reassembly_overlaps',
            },
            'Tcp': {
                'RetransSegs': 'system.net.tcp.retrans_segs',
                'InSegs': 'system.net.tcp.in_segs',
                'OutSegs': 'system.net.tcp.out_segs',
                'ActiveOpens': 'system.net.tcp.active_opens',
                'PassiveOpens': 'system.net.tcp.passive_opens',
                'AttemptFails': 'system.net.tcp.attempt_fails',
                'EstabResets': 'system.net.tcp.established_resets',
                'InErrs': 'system.net.tcp.in_errors',
                'OutRsts': 'system.net.tcp.out_resets',
                'InCsumErrors': 'system.net.tcp.in_csum_errors',
            },
            'TcpExt': {
                'ListenOverflows': 'system.net.tcp.listen_overflows',
                'ListenDrops': 'system.net.tcp.listen_drops',
                'TCPBacklogDrop': 'system.net.tcp.backlog_drops',
                'TCPRetransFail': 'system.net.tcp.failed_retransmits',
                'IPReversePathFilter': 'system.net.ip.reverse_path_filter',
                'PruneCalled': 'system.net.tcp.prune_called',
                'RcvPruned': 'system.net.tcp.prune_rcv_drops',
                'OfoPruned': 'system.net.tcp.prune_ofo_called',
                'PAWSActive': 'system.net.tcp.paws_connection_drops',
                'PAWSEstab': 'system.net.tcp.paws_established_drops',
                'SyncookiesSent': 'system.net.tcp.syn_cookies_sent',
                'SyncookiesRecv': 'system.net.tcp.syn_cookies_recv',
                'SyncookiesFailed': 'system.net.tcp.syn_cookies_failed',
                'TCPAbortOnTimeout': 'system.net.tcp.abort_on_timeout',
                'TCPSynRetrans': 'system.net.tcp.syn_retrans',
                'TCPFromZeroWindowAdv': 'system.net.tcp.from_zero_window',
                'TCPToZeroWindowAdv': 'system.net.tcp.to_zero_window',
                'TWRecycled': 'system.net.tcp.tw_reused',
            },
            'Udp': {
                'InDatagrams': 'system.net.udp.in_datagrams',
                'NoPorts': 'system.net.udp.no_ports',
                'InErrors': 'system.net.udp.in_errors',
                'OutDatagrams': 'system.net.udp.out_datagrams',
                'RcvbufErrors': 'system.net.udp.rcv_buf_errors',
                'SndbufErrors': 'system.net.udp.snd_buf_errors',
                'InCsumErrors': 'system.net.udp.in_csum_errors',
            },
        }
        nstat_metrics_gauge_names = {
            'Tcp': {
                'CurrEstab': 'system.net.tcp.current_established',
            },
        }

        for k in nstat_metrics_names:
            for met in nstat_metrics_names[k]:
                if met in netstat_data.get(k, {}):
                    self._submit_netmetric(
                        nstat_metrics_names[k][met], self._parse_value(netstat_data[k][met]), tags=custom_tags
                    )

        for k in nstat_metrics_gauge_names:
            for met in nstat_metrics_gauge_names[k]:
                if met in netstat_data.get(k, {}):
                    self._submit_netmetric_gauge(
                        nstat_metrics_gauge_names[k][met], self._parse_value(netstat_data[k][met]), tags=custom_tags
                    )

        # Get the conntrack -S information
        conntrack_path = instance.get('conntrack_path')
        use_sudo_conntrack = is_affirmative(instance.get('use_sudo_conntrack', True))
        if conntrack_path is not None:
            self._add_conntrack_stats_metrics(conntrack_path, use_sudo_conntrack, custom_tags)

        # Get the rest of the metric by reading the files. Metrics available since kernel 3.6
        conntrack_files_location = os.path.join(proc_location, 'sys', 'net', 'netfilter')
        # By default, only max and count are reported. However if the blacklist is set,
        # the whitelist is losing its default value
        blacklisted_files = instance.get('blacklist_conntrack_metrics')
        whitelisted_files = instance.get('whitelist_conntrack_metrics')
        if blacklisted_files is None and whitelisted_files is None:
            whitelisted_files = ['max', 'count']

        available_files = []

        # Get the metrics to read
        try:
            for metric_file in os.listdir(conntrack_files_location):
                if (
                    os.path.isfile(os.path.join(conntrack_files_location, metric_file))
                    and 'nf_conntrack_' in metric_file
                ):
                    available_files.append(metric_file[len('nf_conntrack_') :])
        except Exception as e:
            self.log.debug("Unable to list the files in %s. %s", conntrack_files_location, e)

        filtered_available_files = pattern_filter(
            available_files, whitelist=whitelisted_files, blacklist=blacklisted_files
        )

        for metric_name in filtered_available_files:
            metric_file_location = os.path.join(conntrack_files_location, 'nf_conntrack_{}'.format(metric_name))
            value = self._read_int_file(metric_file_location)
            if value is not None:
                self.gauge('system.net.conntrack.{}'.format(metric_name), value, tags=custom_tags)

    @staticmethod
    def _get_net_proc_base_location(proc_location):
        if Platform.is_containerized() and proc_location != "/proc":
            net_proc_base_location = "%s/1" % proc_location
        else:
            net_proc_base_location = proc_location
        return net_proc_base_location

    def _read_int_file(self, file_location):
        try:
            with open(file_location, 'r') as f:
                try:
                    value = int(f.read().rstrip())
                    return value
                except ValueError:
                    self.log.debug("Content of %s is not an integer", file_location)
        except IOError as e:
            self.log.debug("Unable to read %s, skipping %s.", file_location, e)
            return None

    def _get_iface_sys_metrics(self, custom_tags):
        sys_net_location = '/sys/class/net'
        sys_net_metrics = ['mtu', 'tx_queue_len']
        try:
            ifaces = os.listdir(sys_net_location)
        except OSError as e:
            self.log.debug("Unable to list %s, skipping system iface metrics: %s.", sys_net_location, e)
            return None
        for iface in ifaces:
            for metric_name in sys_net_metrics:
                metric_file_location = os.path.join(sys_net_location, iface, metric_name)
                value = self._read_int_file(metric_file_location)
                if value is not None:
                    self.gauge('system.net.iface.{}'.format(metric_name), value, tags=custom_tags + ["iface:" + iface])
            iface_queues_location = os.path.join(sys_net_location, iface, 'queues')
            self._collect_iface_queue_metrics(iface, iface_queues_location, custom_tags)

    def _collect_iface_queue_metrics(self, iface, iface_queues_location, custom_tags):
        try:
            iface_queues = os.listdir(iface_queues_location)
        except OSError as e:
            self.log.debug("Unable to list %s, skipping %s.", iface_queues_location, e)
            return
        num_rx_queues = len([q for q in iface_queues if q.startswith('rx-')])
        num_tx_queues = len([q for q in iface_queues if q.startswith('tx-')])
        self.gauge('system.net.iface.num_tx_queues', num_tx_queues, tags=custom_tags + ["iface:" + iface])
        self.gauge('system.net.iface.num_rx_queues', num_rx_queues, tags=custom_tags + ["iface:" + iface])

    def _add_conntrack_stats_metrics(self, conntrack_path, use_sudo_conntrack, tags):
        """
        Parse the output of conntrack -S
        Add the parsed metrics
        """
        try:
            cmd = [conntrack_path, "-S"]
            if use_sudo_conntrack:
                cmd.insert(0, "sudo")
            output, _, _ = get_subprocess_output(cmd, self.log)
            # conntrack -S sample:
            # cpu=0 found=27644 invalid=19060 ignore=485633411 insert=0 insert_failed=1 \
            #       drop=1 early_drop=0 error=0 search_restart=39936711
            # cpu=1 found=21960 invalid=17288 ignore=475938848 insert=0 insert_failed=1 \
            #       drop=1 early_drop=0 error=0 search_restart=36983181

            lines = output.splitlines()

            for line in lines:
                cols = line.split()
                cpu_num = cols[0].split('=')[-1]
                cpu_tag = ['cpu:{}'.format(cpu_num)]
                cols = cols[1:]

                for cell in cols:
                    metric, value = cell.split('=')
                    self.monotonic_count('system.net.conntrack.{}'.format(metric), int(value), tags=tags + cpu_tag)
        except SubprocessOutputEmptyError:
            self.log.debug("Couldn't use %s to get conntrack stats", conntrack_path)

    def _get_metrics(self):
        return {val: 0 for val in itervalues(self.cx_state_gauge)}

    def _parse_short_state_lines(self, lines, metrics, tcp_states, ip_version):
        for line in lines:
            value, state = line.split()
            proto = "tcp{0}".format(ip_version)
            if state in tcp_states:
                metric = self.cx_state_gauge[proto, tcp_states[state]]
                metrics[metric] += int(value)

    def _parse_linux_cx_state(self, lines, tcp_states, state_col, protocol=None, ip_version=None):
        """
        Parse the output of the command that retrieves the connection state (either `ss` or `netstat`)
        Returns a dict metric_name -> value
        """
        metrics = self._get_metrics()
        for l in lines:
            cols = l.split()
            if cols[0].startswith('tcp') or protocol == 'tcp':
                proto = "tcp{0}".format(ip_version) if ip_version else ("tcp4", "tcp6")[cols[0] == "tcp6"]
                if cols[state_col] in tcp_states:
                    metric = self.cx_state_gauge[proto, tcp_states[cols[state_col]]]
                    metrics[metric] += 1
            elif cols[0].startswith('udp') or protocol == 'udp':
                proto = "udp{0}".format(ip_version) if ip_version else ("udp4", "udp6")[cols[0] == "udp6"]
                metric = self.cx_state_gauge[proto, 'connections']
                metrics[metric] += 1

        return metrics

    def _check_bsd(self, instance):
        netstat_flags = ['-i', '-b']

        custom_tags = instance.get('tags', [])

        # FreeBSD's netstat truncates device names unless you pass '-W'
        if Platform.is_freebsd():
            netstat_flags.append('-W')

        try:
            output, _, _ = get_subprocess_output(["netstat"] + netstat_flags, self.log)
            lines = output.splitlines()
            # Name  Mtu   Network       Address            Ipkts Ierrs     Ibytes    Opkts Oerrs     Obytes  Coll
            # lo0   16384 <Link#1>                        318258     0  428252203   318258     0  428252203     0
            # lo0   16384 localhost   fe80:1::1           318258     -  428252203   318258     -  428252203     -
            # lo0   16384 127           localhost         318258     -  428252203   318258     -  428252203     -
            # lo0   16384 localhost   ::1                 318258     -  428252203   318258     -  428252203     -
            # gif0* 1280  <Link#2>                             0     0          0        0     0          0     0
            # stf0* 1280  <Link#3>                             0     0          0        0     0          0     0
            # en0   1500  <Link#4>    04:0c:ce:db:4e:fa 20801309     0 13835457425 15149389     0 11508790198     0
            # en0   1500  seneca.loca fe80:4::60c:ceff: 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  192.168.1     192.168.1.63    20801309     - 13835457425 15149389     - 11508790198     -
            # en0   1500  2001:470:1f 2001:470:1f07:11d 20801309     - 13835457425 15149389     - 11508790198     -
            # p2p0  2304  <Link#5>    06:0c:ce:db:4e:fa        0     0          0        0     0          0     0
            # ham0  1404  <Link#6>    7a:79:05:4d:bf:f5    30100     0    6815204    18742     0    8494811     0
            # ham0  1404  5             5.77.191.245       30100     -    6815204    18742     -    8494811     -
            # ham0  1404  seneca.loca fe80:6::7879:5ff:    30100     -    6815204    18742     -    8494811     -
            # ham0  1404  2620:9b::54 2620:9b::54d:bff5    30100     -    6815204    18742     -    8494811     -

            headers = lines[0].split()

            # Given the irregular structure of the table above, better to parse from the end of each line
            # Verify headers first
            #          -7       -6       -5        -4       -3       -2        -1
            for h in ("Ipkts", "Ierrs", "Ibytes", "Opkts", "Oerrs", "Obytes", "Coll"):
                if h not in headers:
                    self.log.error("%s not found in %s; cannot parse", h, headers)
                    return False

            current = None
            for l in lines[1:]:
                # Another header row, abort now, this is IPv6 land
                if "Name" in l:
                    break

                x = l.split()
                if len(x) == 0:
                    break

                iface = x[0]
                if iface.endswith("*"):
                    iface = iface[:-1]
                if iface == current:
                    # skip multiple lines of same interface
                    continue
                else:
                    current = iface

                # Filter inactive interfaces
                if self._parse_value(x[-5]) or self._parse_value(x[-2]):
                    iface = current
                    metrics = {
                        'bytes_rcvd': self._parse_value(x[-5]),
                        'bytes_sent': self._parse_value(x[-2]),
                        'packets_in.count': self._parse_value(x[-7]),
                        'packets_in.error': self._parse_value(x[-6]),
                        'packets_out.count': self._parse_value(x[-4]),
                        'packets_out.error': self._parse_value(x[-3]),
                    }
                    self._submit_devicemetrics(iface, metrics, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting connection stats.")

        try:
            netstat, _, _ = get_subprocess_output(["netstat", "-s", "-p" "tcp"], self.log)
            # 3651535 packets sent
            #         972097 data packets (615753248 bytes)
            #         5009 data packets (2832232 bytes) retransmitted
            #         0 resends initiated by MTU discovery
            #         2086952 ack-only packets (471 delayed)
            #         0 URG only packets
            #         0 window probe packets
            #         310851 window update packets
            #         336829 control packets
            #         0 data packets sent after flow control
            #         3058232 checksummed in software
            #         3058232 segments (571218834 bytes) over IPv4
            #         0 segments (0 bytes) over IPv6
            # 4807551 packets received
            #         1143534 acks (for 616095538 bytes)
            #         165400 duplicate acks
            #         ...

            self._submit_regexed_values(netstat, BSD_TCP_METRICS, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting TCP stats.")

        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')

        net_proc_base_location = self._get_net_proc_base_location(proc_location)

        if self._is_collect_cx_state_runnable(net_proc_base_location):
            try:
                self.log.debug("Using `netstat` to collect connection state")
                output_TCP, _, _ = get_subprocess_output(["netstat", "-n", "-a", "-p", "tcp"], self.log)
                output_UDP, _, _ = get_subprocess_output(["netstat", "-n", "-a", "-p", "udp"], self.log)
                lines = output_TCP.splitlines() + output_UDP.splitlines()
                # Active Internet connections (w/o servers)
                # Proto Recv-Q Send-Q Local Address           Foreign Address         State
                # tcp        0      0 46.105.75.4:80          79.220.227.193:2032     SYN_RECV
                # tcp        0      0 46.105.75.4:143         90.56.111.177:56867     ESTABLISHED
                # tcp        0      0 46.105.75.4:50468       107.20.207.175:443      TIME_WAIT
                # tcp6       0      0 46.105.75.4:80          93.15.237.188:58038     FIN_WAIT2
                # tcp6       0      0 46.105.75.4:80          79.220.227.193:2029     ESTABLISHED
                # udp        0      0 0.0.0.0:123             0.0.0.0:*
                # udp6       0      0 :::41458                :::*

                metrics = self._parse_linux_cx_state(lines[2:], self.tcp_states['netstat'], 5)
                for metric, value in iteritems(metrics):
                    self.gauge(metric, value, tags=custom_tags)
            except SubprocessOutputEmptyError:
                self.log.exception("Error collecting connection states.")

    def _check_solaris(self, instance):
        # Can't get bytes sent and received via netstat
        # Default to kstat -p link:0:
        custom_tags = instance.get('tags', [])
        try:
            netstat, _, _ = get_subprocess_output(["kstat", "-p", "link:0:"], self.log)
            metrics_by_interface = self._parse_solaris_netstat(netstat)
            for interface, metrics in iteritems(metrics_by_interface):
                self._submit_devicemetrics(interface, metrics, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting kstat stats.")

        try:
            netstat, _, _ = get_subprocess_output(["netstat", "-s", "-P" "tcp"], self.log)
            # TCP: tcpRtoAlgorithm=     4 tcpRtoMin           =   200
            # tcpRtoMax           = 60000 tcpMaxConn          =    -1
            # tcpActiveOpens      =    57 tcpPassiveOpens     =    50
            # tcpAttemptFails     =     1 tcpEstabResets      =     0
            # tcpCurrEstab        =     0 tcpOutSegs          =   254
            # tcpOutDataSegs      =   995 tcpOutDataBytes     =1216733
            # tcpRetransSegs      =     0 tcpRetransBytes     =     0
            # tcpOutAck           =   185 tcpOutAckDelayed    =     4
            # ...
            self._submit_regexed_values(netstat, SOLARIS_TCP_METRICS, custom_tags)
        except SubprocessOutputEmptyError:
            self.log.exception("Error collecting TCP stats.")

    def _parse_solaris_netstat(self, netstat_output):
        """
        Return a mapping of network metrics by interface. For example:
            { interface:
                {'bytes_sent': 0,
                  'bytes_rcvd': 0,
                  'bytes_rcvd': 0,
                  ...
                }
            }
        """
        # Here's an example of the netstat output:
        #
        # link:0:net0:brdcstrcv   527336
        # link:0:net0:brdcstxmt   1595
        # link:0:net0:class       net
        # link:0:net0:collisions  0
        # link:0:net0:crtime      16359935.2637943
        # link:0:net0:ierrors     0
        # link:0:net0:ifspeed     10000000000
        # link:0:net0:ipackets    682834
        # link:0:net0:ipackets64  682834
        # link:0:net0:link_duplex 0
        # link:0:net0:link_state  1
        # link:0:net0:multircv    0
        # link:0:net0:multixmt    1595
        # link:0:net0:norcvbuf    0
        # link:0:net0:noxmtbuf    0
        # link:0:net0:obytes      12820668
        # link:0:net0:obytes64    12820668
        # link:0:net0:oerrors     0
        # link:0:net0:opackets    105445
        # link:0:net0:opackets64  105445
        # link:0:net0:rbytes      113983614
        # link:0:net0:rbytes64    113983614
        # link:0:net0:snaptime    16834735.1607669
        # link:0:net0:unknowns    0
        # link:0:net0:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c
        # link:0:net1:brdcstrcv   4947620
        # link:0:net1:brdcstxmt   1594
        # link:0:net1:class       net
        # link:0:net1:collisions  0
        # link:0:net1:crtime      16359935.2839167
        # link:0:net1:ierrors     0
        # link:0:net1:ifspeed     10000000000
        # link:0:net1:ipackets    4947620
        # link:0:net1:ipackets64  4947620
        # link:0:net1:link_duplex 0
        # link:0:net1:link_state  1
        # link:0:net1:multircv    0
        # link:0:net1:multixmt    1594
        # link:0:net1:norcvbuf    0
        # link:0:net1:noxmtbuf    0
        # link:0:net1:obytes      73324
        # link:0:net1:obytes64    73324
        # link:0:net1:oerrors     0
        # link:0:net1:opackets    1594
        # link:0:net1:opackets64  1594
        # link:0:net1:rbytes      304384894
        # link:0:net1:rbytes64    304384894
        # link:0:net1:snaptime    16834735.1613302
        # link:0:net1:unknowns    0
        # link:0:net1:zonename    53aa9b7e-48ba-4152-a52b-a6368c3d9e7c

        # A mapping of solaris names -> datadog names
        metric_by_solaris_name = {
            'rbytes64': 'bytes_rcvd',
            'obytes64': 'bytes_sent',
            'ipackets64': 'packets_in.count',
            'ierrors': 'packets_in.error',
            'opackets64': 'packets_out.count',
            'oerrors': 'packets_out.error',
        }

        lines = [l for l in netstat_output.splitlines() if len(l) > 0]

        metrics_by_interface = {}

        for l in lines:
            # Parse the metric & interface.
            cols = l.split()
            link, n, iface, name = cols[0].split(":")
            assert link == "link"

            # Get the datadog metric name.
            ddname = metric_by_solaris_name.get(name, None)
            if ddname is None:
                continue

            # Add it to this interface's list of metrics.
            metrics = metrics_by_interface.get(iface, {})
            metrics[ddname] = self._parse_value(cols[1])
            metrics_by_interface[iface] = metrics

        return metrics_by_interface

    def _check_psutil(self, instance):
        """
        Gather metrics about connections states and interfaces counters
        using psutil facilities
        """
        custom_tags = instance.get('tags', [])
        if self._collect_cx_state:
            self._cx_state_psutil(tags=custom_tags)

        self._cx_counters_psutil(tags=custom_tags)

    def _cx_state_psutil(self, tags=None):
        """
        Collect metrics about connections state using psutil
        """
        metrics = defaultdict(int)
        tags = [] if tags is None else tags
        for conn in psutil.net_connections():
            protocol = self._parse_protocol_psutil(conn)
            status = self.tcp_states['psutil'].get(conn.status)
            metric = self.cx_state_gauge.get((protocol, status))
            if metric is None:
                self.log.warning('Metric not found for: %s,%s', protocol, status)
            else:
                metrics[metric] += 1

        for metric, value in iteritems(metrics):
            self.gauge(metric, value, tags=tags)

    def _cx_counters_psutil(self, tags=None):
        """
        Collect metrics about interfaces counters using psutil
        """
        tags = [] if tags is None else tags
        for iface, counters in iteritems(psutil.net_io_counters(pernic=True)):
            metrics = {
                'bytes_rcvd': counters.bytes_recv,
                'bytes_sent': counters.bytes_sent,
                'packets_in.count': counters.packets_recv,
                'packets_in.drop': counters.dropin,
                'packets_in.error': counters.errin,
                'packets_out.count': counters.packets_sent,
                'packets_out.drop': counters.dropout,
                'packets_out.error': counters.errout,
            }
            self._submit_devicemetrics(iface, metrics, tags)

    def _parse_protocol_psutil(self, conn):
        """
        Returns a string describing the protocol for the given connection
        in the form `tcp4`, 'udp4` as in `self.cx_state_gauge`
        """
        protocol = self.PSUTIL_TYPE_MAPPING.get(conn.type, '')
        family = self.PSUTIL_FAMILY_MAPPING.get(conn.family, '')
        return '{}{}'.format(protocol, family)

    def _parse_queues(self, tool, ss_output):
        """
        for each line of `ss_output`, returns a triplet with:
        * a connection state (`established`, `listening`)
        * the receive queue size
        * the send queue size
        """
        for line in ss_output.splitlines():
            fields = line.split()

            if len(fields) < (6 if tool == "netstat" else 3):
                continue

            state_column = 0 if tool == "ss" else 5

            try:
                state = self.tcp_states[tool][fields[state_column]]
            except KeyError:
                continue

            yield (state, fields[1], fields[2])

    def _handle_ethtool_stats(self, iface, custom_tags):
        # read Ethtool metrics, if configured and available
        if not self._collect_ethtool_stats:
            return
        driver_name, driver_version, ethtool_stats_names, ethtool_stats = self._fetch_ethtool_stats(iface)
        tags = [] if custom_tags is None else custom_tags[:]
        tags.append('driver_name:{}'.format(driver_name))
        tags.append('driver_version:{}'.format(driver_version))
        if self._collect_ena_metrics:
            ena_metrics = self._get_ena_metrics(ethtool_stats_names, ethtool_stats)
            self._submit_ena_metrics(iface, ena_metrics, tags)
        if self._collect_ethtool_metrics:
            ethtool_metrics = self._get_ethtool_metrics(driver_name, ethtool_stats_names, ethtool_stats)
            self._submit_ethtool_metrics(iface, ethtool_metrics, tags)

    def _fetch_ethtool_stats(self, iface):
        """
        Collect ethtool metrics for given interface.

        Ethtool metrics are collected via the ioctl SIOCETHTOOL call. At the time of writing
        this method, there are no maintained Python libraries that do this. The solution
        is based on:

        * https://github.com/safchain/ethtool
        * https://gist.github.com/yunazuno/d7cd7e1e127a39192834c75d85d45df9
        """
        ethtool_socket = None
        try:
            ethtool_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            driver_name, driver_version = self._get_ethtool_drvinfo(iface, ethtool_socket)
            stats_names, stats = self._get_ethtool_stats(iface, ethtool_socket)
            return driver_name, driver_version, stats_names, stats
        except OSError as e:
            # this will happen for interfaces that don't support SIOCETHTOOL - e.g. loopback or docker
            self.log.debug('OSError while trying to collect ethtool metrics for interface %s: %s', iface, str(e))
        except Exception:
            self.log.exception('Unable to collect ethtool metrics for interface %s', iface)
        finally:
            if ethtool_socket is not None:
                ethtool_socket.close()
        return (None, None, [], [])

    def _send_ethtool_ioctl(self, iface, sckt, data):
        """
        Send an ioctl SIOCETHTOOL call for given interface with given data.
        """
        ifr = struct.pack('16sP', iface.encode('utf-8'), data.buffer_info()[0])
        fcntl.ioctl(sckt.fileno(), SIOCETHTOOL, ifr)

    def _byte_array_to_string(self, s):
        """
        Convert a byte array to string
        b'hv_netvsc\x00\x00\x00\x00' -> 'hv_netvsc'
        """
        s = s.tobytes() if PY3 else s.tostring()
        s = s.partition(b'\x00')[0].decode('utf-8')
        return s

    def _get_ethtool_gstringset(self, iface, sckt):
        """
        Retrieve names of all ethtool stats for given interface.
        """
        sset_info = array.array('B', struct.pack('IIQI', ETHTOOL_GSSET_INFO, 0, 1 << ETH_SS_STATS, 0))
        self._send_ethtool_ioctl(iface, sckt, sset_info)
        sset_mask, sset_len = struct.unpack('8xQI', sset_info)
        if sset_mask == 0:
            sset_len = 0

        strings = array.array('B', struct.pack('III', ETHTOOL_GSTRINGS, ETH_SS_STATS, sset_len))
        strings.extend([0] * sset_len * ETH_GSTRING_LEN)
        self._send_ethtool_ioctl(iface, sckt, strings)

        all_names = []
        for i in range(sset_len):
            offset = 12 + ETH_GSTRING_LEN * i
            s = self._byte_array_to_string(strings[offset : offset + ETH_GSTRING_LEN])
            all_names.append(s)
        return all_names

    def _get_ethtool_drvinfo(self, iface, sckt):
        drvinfo = array.array('B', struct.pack('I', ETHTOOL_GDRVINFO))
        # Struct in
        # https://github.com/torvalds/linux/blob/448f413a8bdc727d25d9a786ccbdb974fb85d973/include/uapi/linux/ethtool.h#L187-L200
        # Total size: 196
        # Same result as printf("%zu\n", sizeof(struct ethtool_drvinfo));
        drvinfo.extend([0] * (4 + 32 + 32 + 32 + 32 + 32 + 12 + 5 * 4))
        self._send_ethtool_ioctl(iface, sckt, drvinfo)
        driver_name = self._byte_array_to_string(drvinfo[4 : 4 + 32])
        driver_version = self._byte_array_to_string(drvinfo[4 + 32 : 32 + 32])
        return driver_name, driver_version

    def _get_ethtool_stats(self, iface, sckt):
        stats_names = list(self._get_ethtool_gstringset(iface, sckt))
        stats_count = len(stats_names)

        stats = array.array('B', struct.pack('II', ETHTOOL_GSTATS, stats_count))
        # we need `stats_count * (length of uint64)` for the result
        stats.extend([0] * len(struct.pack('Q', 0)) * stats_count)
        self._send_ethtool_ioctl(iface, sckt, stats)
        return stats_names, stats

    def _parse_ethtool_queue_num(self, stat_name):
        """
        Extract the queue and the metric name from ethtool stat name:
        queue_0_tx_cnt -> (queue:0, tx_cnt)
        tx_queue_0_bytes -> (queue:0, tx_bytes)
        """
        if 'queue_' not in stat_name:
            return None, None
        parts = stat_name.split('_')
        if 'queue' not in parts:
            return None, None
        queue_index = parts.index('queue')
        queue_num = parts[queue_index + 1]
        if not queue_num.isdigit():
            return None, None
        parts.pop(queue_index)
        parts.pop(queue_index)
        return 'queue:{}'.format(queue_num), '_'.join(parts)

    def _parse_ethtool_queue_array(self, stat_name):
        """
        Extract the queue and the metric name from ethtool stat name:
        tx_stop[0] -> (queue:0, tx_stop)
        """
        if '[' not in stat_name or not stat_name.endswith(']'):
            return None, None
        parts = stat_name.split('[')
        if len(parts) != 2:
            return None, None
        metric_name = parts[0]
        queue_num = parts[1][:-1]
        if not queue_num.isdigit():
            return None, None
        return 'queue:{}'.format(queue_num), metric_name

    def _parse_ethtool_cpu_num(self, stat_name):
        """
        Extract the cpu and the metric name from ethtool stat name:
        cpu0_rx_bytes -> (cpu:0, rx_bytes)
        """
        if not stat_name.startswith('cpu'):
            return None, None
        parts = stat_name.split('_')
        cpu_num = parts[0][3:]
        if not cpu_num.isdigit():
            return None, None
        parts.pop(0)
        return 'cpu:{}'.format(cpu_num), '_'.join(parts)

    def _get_stat_value(self, stats, index):
        offset = 8 + 8 * index
        value = struct.unpack('Q', stats[offset : offset + 8])[0]
        return value

    def _get_ethtool_metrics(self, driver_name, stats_names, stats):
        """
        Get all ethtool metrics specified in ETHTOOL_METRIC_NAMES list and their values from ethtool.
        We convert the queue and cpu number to a tag: queue_0_tx_cnt will be submitted as tx_cnt with the tag queue:0

        Return [tag][metric] -> value
        """
        res = defaultdict(dict)
        if driver_name not in ETHTOOL_METRIC_NAMES:
            return res
        ethtool_global_metrics = ETHTOOL_GLOBAL_METRIC_NAMES.get(driver_name, {})
        for i, stat_name in enumerate(stats_names):
            tag, metric_name = self._parse_ethtool_queue_num(stat_name)
            metric_prefix = '.queue.'
            if not tag:
                tag, metric_name = self._parse_ethtool_cpu_num(stat_name)
                metric_prefix = '.cpu.'
            if not tag:
                tag, metric_name = self._parse_ethtool_queue_array(stat_name)
                metric_prefix = '.queue.'
            if metric_name and metric_name not in ETHTOOL_METRIC_NAMES[driver_name]:
                # A per queue/cpu metric was found but is not part of the collected metrics
                continue
            if not tag and stat_name in ethtool_global_metrics:
                tag = 'global'
                metric_prefix = '.'
                metric_name = stat_name
            if not tag:
                continue
            res[tag][driver_name + metric_prefix + metric_name] = self._get_stat_value(stats, i)
        return res

    def _get_ena_metrics(self, stats_names, stats):
        """
        Get all ENA metrics specified in ENA_METRICS_NAMES list and their values from ethtool.
        """
        metrics = {}
        for i, stat_name in enumerate(stats_names):
            if stat_name in ENA_METRIC_NAMES:
                metrics[ENA_METRIC_PREFIX + stat_name] = self._get_stat_value(stats, i)

        return metrics
