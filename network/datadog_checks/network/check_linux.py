# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

from six import PY3, iteritems

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import pattern_filter
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output
from . import Network

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


class LinuxNetwork(Network):
    def __init__(self, name, init_config, instances):
        super(LinuxNetwork, self).__init__(name, init_config, instances)

    def check(self, instance):
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
                    available_files.append(metric_file[len('nf_conntrack_'):])
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
