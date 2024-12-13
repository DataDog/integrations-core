# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
from collections import defaultdict
from ctypes import Structure, byref, windll
from ctypes.wintypes import DWORD

import psutil

from . import Network

Iphlpapi = windll.Iphlpapi


class TCPSTATS(Structure):
    """
    https://learn.microsoft.com/en-us/windows/win32/api/tcpmib/ns-tcpmib-mib_tcpstats_lh
    """

    _fields_ = [
        ("dwRtoAlgorithm", DWORD),
        ("dwRtoMin", DWORD),
        ("dwRtoMax", DWORD),
        ("dwMaxConn", DWORD),
        ("dwActiveOpens", DWORD),
        ("dwPassiveOpens", DWORD),
        ("dwAttemptFails", DWORD),
        ("dwEstabResets", DWORD),
        ("dwCurrEstab", DWORD),
        ("dwInSegs", DWORD),
        ("dwOutSegs", DWORD),
        ("dwRetransSegs", DWORD),
        ("dwInErrs", DWORD),
        ("dwOutRsts", DWORD),
        ("dwNumConns", DWORD),
    ]


class WindowsNetwork(Network):
    """
    Gather metrics about connections states and interfaces counters
    using psutil facilities
    """

    def __init__(self, name, init_config, instances):
        super(WindowsNetwork, self).__init__(name, init_config, instances)

    def check(self, _):
        custom_tags = self.instance.get('tags', [])
        if self._collect_cx_state:
            self._cx_state_psutil(tags=custom_tags)
        self._tcp_stats(tags=custom_tags)

        self._cx_counters_psutil(tags=custom_tags)

    def get_expected_metrics(self):
        expected_metrics = super(WindowsNetwork, self).get_expected_metrics()
        expected_metrics.extend(
            [
                'packets_in.drop',
                'packets_out.drop',
            ]
        )
        return expected_metrics

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

        for metric, value in metrics.items():
            self.gauge(metric, value, tags=tags)

    def _cx_counters_psutil(self, tags=None):
        """
        Collect metrics about interfaces counters using psutil
        """
        tags = [] if tags is None else tags
        for iface, counters in psutil.net_io_counters(pernic=True).items():
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
            self.submit_devicemetrics(iface, metrics, tags)

    def _get_tcp_stats(self, inet):
        stats = TCPSTATS()
        try:
            Iphlpapi.GetTcpStatisticsEx(byref(stats), inet)
        except OSError as e:
            self.log.error("OSError: %s", e)
            return None
        return stats

    def _tcp_stats(self, tags):
        """
        Collect metrics from Microsoft's TCPSTATS
        """
        tags = [] if tags is None else tags

        tcpstats_dict = {
            'dwActiveOpens': '.active_opens',
            'dwPassiveOpens': '.passive_opens',
            'dwAttemptFails': '.attempt_fails',
            'dwEstabResets': '.established_resets',
            'dwCurrEstab': '.current_established',
            'dwInSegs': '.in_segs',
            'dwOutSegs': '.out_segs',
            'dwRetransSegs': '.retrans_segs',
            'dwInErrs': '.in_errors',
            'dwOutRsts': '.out_resets',
            'dwNumConns': '.connections',
        }
        # similar to the linux check
        nstat_metrics_gauge_names = [
            '.connections',
            '.current_established',
        ]

        proto_dict = {}
        tcp4stats = self._get_tcp_stats(socket.AF_INET)
        if tcp4stats:
            proto_dict["tcp4"] = tcp4stats
        tcp6stats = self._get_tcp_stats(socket.AF_INET6)
        if tcp6stats:
            proto_dict["tcp6"] = tcp6stats

        tcpAllstats = TCPSTATS()
        # Create tcp metrics that are a sum of tcp4 and tcp6 metrics
        if 'tcp4' in proto_dict and 'tcp6' in proto_dict:
            for fieldname, _ in tcpAllstats._fields_:
                tcp_sum = getattr(proto_dict['tcp4'], fieldname) + getattr(proto_dict['tcp6'], fieldname)
                setattr(tcpAllstats, fieldname, tcp_sum)
            proto_dict["tcp"] = tcpAllstats

        for proto, stats in proto_dict.items():
            for fieldname in tcpstats_dict:
                fieldvalue = getattr(stats, fieldname)
                metric_name = "system.net." + str(proto) + tcpstats_dict[fieldname]
                if tcpstats_dict[fieldname] in nstat_metrics_gauge_names:
                    self._submit_netmetric_gauge(metric_name, fieldvalue, tags)
                else:
                    self.submit_netmetric(metric_name, fieldvalue, tags)

    def _parse_protocol_psutil(self, conn):
        """
        Returns a string describing the protocol for the given connection
        in the form `tcp4`, 'udp4` as in `self.cx_state_gauge`
        """
        protocol = self.PSUTIL_TYPE_MAPPING.get(conn.type, '')
        family = self.PSUTIL_FAMILY_MAPPING.get(conn.family, '')
        return '{}{}'.format(protocol, family)
