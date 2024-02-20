# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import socket

from six import PY3, iteritems

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.common import pattern_filter
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output
from datadog_checks.network import ethtool
from datadog_checks.network.const import ENA_METRIC_NAMES, ENA_METRIC_PREFIX

from . import Network

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

if PY3:
    long = int


class LinuxNetwork(Network):
    def __init__(self, name, init_config, instances):
        super(LinuxNetwork, self).__init__(name, init_config, instances)
        self._collect_cx_queues = self.instance.get('collect_connection_queues', False)

    def check(self, _):
        """
        check can be run inside a container and still collects the network metrics from the host
        For that procfs_path can be set to something like "/host/proc"
        When a custom procfs_path is set, the collect_connection_state option is ignored
        """
        proc_location = datadog_agent.get_config('procfs_path')
        if not proc_location:
            proc_location = '/proc'
        proc_location = proc_location.rstrip('/')
        custom_tags = self.instance.get('tags', [])

        self._get_iface_sys_metrics(custom_tags)
        net_proc_base_location = self.get_net_proc_base_location(proc_location)

        if self.is_collect_cx_state_runnable(net_proc_base_location):
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
                        for state, recvq, sendq in self._parse_queues("ss", output):
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

                metrics = self.parse_cx_state(lines[2:], self.tcp_states['netstat'], 5)
                for metric, value in iteritems(metrics):
                    self.gauge(metric, value, tags=custom_tags)

                if self._collect_cx_queues:
                    for state, recvq, sendq in self._parse_queues("netstat", output):
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
            if self.parse_long(x[0]) or self.parse_long(x[8]):
                iface = cols[0].strip()
                metrics = {
                    'bytes_rcvd': self.parse_long(x[0]),
                    'bytes_sent': self.parse_long(x[8]),
                    'packets_in.count': self.parse_long(x[1]),
                    'packets_in.drop': self.parse_long(x[3]),
                    'packets_in.error': self.parse_long(x[2]) + self.parse_long(x[3]),
                    'packets_out.count': self.parse_long(x[9]),
                    'packets_out.drop': self.parse_long(x[11]),
                    'packets_out.error': self.parse_long(x[10]) + self.parse_long(x[11]),
                }
                self.submit_devicemetrics(iface, metrics, custom_tags)
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
                    self.submit_netmetric(
                        nstat_metrics_names[k][met], self.parse_long(netstat_data[k][met]), tags=custom_tags
                    )

        for k in nstat_metrics_gauge_names:
            for met in nstat_metrics_gauge_names[k]:
                if met in netstat_data.get(k, {}):
                    self._submit_netmetric_gauge(
                        nstat_metrics_gauge_names[k][met], self.parse_long(netstat_data[k][met]), tags=custom_tags
                    )

        # Get the conntrack -S information
        conntrack_path = self.instance.get('conntrack_path')
        use_sudo_conntrack = is_affirmative(self.instance.get('use_sudo_conntrack', True))
        if conntrack_path is not None:
            self._add_conntrack_stats_metrics(conntrack_path, use_sudo_conntrack, custom_tags)

        # Get the rest of the metric by reading the files. Metrics available since kernel 3.6
        conntrack_files_location = os.path.join(proc_location, 'sys', 'net', 'netfilter')
        # By default, only max and count are reported. However if the blacklist is set,
        # the whitelist is losing its default value
        blacklisted_files = self.instance.get('blacklist_conntrack_metrics')
        whitelisted_files = self.instance.get('whitelist_conntrack_metrics')
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

    def get_expected_metrics(self):
        expected_metrics = super(LinuxNetwork, self).get_expected_metrics()
        expected_metrics.extend(
            [
                'packets_in.drop',
                'packets_out.drop',
            ]
        )
        return expected_metrics

    def _submit_netmetric_gauge(self, metric, value, tags=None):
        self.gauge(metric, value, tags=tags)

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

    def _parse_short_state_lines(self, lines, metrics, tcp_states, ip_version):
        for line in lines:
            value, state = line.split()
            proto = "tcp{0}".format(ip_version)
            if state in tcp_states:
                metric = self.cx_state_gauge[proto, tcp_states[state]]
                metrics[metric] += int(value)

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
        self.log.debug("Handling ethtool stats")
        if not self._collect_ethtool_stats:
            self.log.debug("Ethtool stat collection not configured")
            return
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            self.log.debug("Skipping network interface %s", iface)
            return
        if iface in ['lo', 'lo0']:
            # Skip loopback ifaces as they don't support SIOCETHTOOL
            self.log.debug("Skipping loopback interface %s", iface)
            return

        driver_name, driver_version, ethtool_stats_names, ethtool_stats = self._fetch_ethtool_stats(iface)
        tags = [] if custom_tags is None else custom_tags[:]
        tags.append('driver_name:{}'.format(driver_name))
        tags.append('driver_version:{}'.format(driver_version))
        if self._collect_ena_metrics:
            self.log.debug("Getting ena metrics")
            ena_metrics = ethtool.get_ena_metrics(ethtool_stats_names, ethtool_stats)
            self.log.debug("ena metrics to submit %s", ena_metrics)
            self._submit_ena_metrics(iface, ena_metrics, tags)
        if self._collect_ethtool_metrics:
            self.log.debug("Getting ethtool metrics")
            ethtool_metrics = ethtool.get_ethtool_metrics(driver_name, ethtool_stats_names, ethtool_stats)
            self.log.debug("ethtool metrics to submit %s", ethtool_metrics)
            self._submit_ethtool_metrics(iface, ethtool_metrics, tags)

    def _submit_ena_metrics(self, iface, vals_by_metric, tags):
        self.log.debug("Submitting ena metrics for %s, %s, %s", iface, vals_by_metric, tags)
        if not vals_by_metric:
            self.log.debug("No vals_by_metric, returning without submitting ena metrics")
            return
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            self.log.debug("Skipping network interface %s", iface)
            return

        metric_tags = [] if tags is None else tags[:]
        metric_tags.append('device:{}'.format(iface))

        allowed = [ENA_METRIC_PREFIX + m for m in ENA_METRIC_NAMES]
        for m in vals_by_metric:
            assert m in allowed

        count = 0
        for metric, val in iteritems(vals_by_metric):
            self.log.debug("Submitting system.net.%s", metric)
            self.gauge('system.net.%s' % metric, val, tags=metric_tags)
            count += 1
        self.log.debug("tracked %s network ena metrics for interface %s", count, iface)

    def _submit_ethtool_metrics(self, iface, ethtool_metrics, base_tags):
        self.log.debug("Submitting ethtool metrics for %s, %s, %s", iface, ethtool_metrics, base_tags)
        if not ethtool_metrics:
            self.log.debug("No ethtool_metrics, returning without submitting ethtool metrics")
            return
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            self.log.debug("Skipping network interface %s", iface)
            return

        base_tags_with_device = [] if base_tags is None else base_tags[:]
        base_tags_with_device.append('device:{}'.format(iface))

        count = 0
        for ethtool_tag, metric_map in iteritems(ethtool_metrics):
            tags = base_tags_with_device + [ethtool_tag]
            for metric, val in iteritems(metric_map):
                self.log.debug("Submitting system.net.%s", metric)
                self.monotonic_count('system.net.%s' % metric, val, tags=tags)
                count += 1
        self.log.debug("tracked %s network ethtool metrics for interface %s", count, iface)

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
            self.log.debug("ethtool_socket: %s", ethtool_socket)
            driver_name, driver_version = ethtool.get_ethtool_drvinfo(iface, ethtool_socket)
            self.log.debug("driver_name = %s, driver_version = %s", driver_name, driver_version)
            stats_names, stats = ethtool.get_ethtool_stats(iface, ethtool_socket)
            self.log.debug("Returning stats_names = %s, stats = %s", stats_names, stats)
            return driver_name, driver_version, stats_names, stats
        except OSError as e:
            # this will happen for interfaces that don't support SIOCETHTOOL - e.g. loopback or docker
            self.log.debug('OSError while trying to collect ethtool metrics for interface %s: %s', iface, str(e))
        except Exception as generic_exception:
            self.log.exception('Unable to collect ethtool metrics for interface %s. %s', iface, str(generic_exception))
        finally:
            if ethtool_socket is not None:
                ethtool_socket.close()
        self.log.debug("Returning default values for driver_name, driver_version, stats_names, stats")
        return None, None, [], []
