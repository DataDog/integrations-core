# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Collects network metrics.
"""
# stdlib
import re
import socket
from collections import defaultdict

# project
from datadog_checks.checks import AgentCheck
from datadog_checks.utils.platform import Platform
from datadog_checks.utils.subprocess_output import (
    get_subprocess_output,
    SubprocessOutputEmptyError,
)
import psutil

BSD_TCP_METRICS = [
    (re.compile(
        "^\s*(\d+) data packets \(\d+ bytes\) retransmitted\s*$"
    ), 'system.net.tcp.retrans_packs'),
    (re.compile(
        "^\s*(\d+) packets sent\s*$"
    ), 'system.net.tcp.sent_packs'),
    (re.compile(
        "^\s*(\d+) packets received\s*$"
    ), 'system.net.tcp.rcv_packs')
]

SOLARIS_TCP_METRICS = [
    (re.compile(
        "\s*tcpRetransSegs\s*=\s*(\d+)\s*"
    ), 'system.net.tcp.retrans_segs'),
    (re.compile(
        "\s*tcpOutDataSegs\s*=\s*(\d+)\s*"
    ), 'system.net.tcp.in_segs'),
    (re.compile(
        "\s*tcpInSegs\s*=\s*(\d+)\s*"
    ), 'system.net.tcp.out_segs')
]


class Network(AgentCheck):

    SOURCE_TYPE_NAME = 'system'

    PSUTIL_TYPE_MAPPING = {
        socket.SOCK_STREAM: 'tcp',
        socket.SOCK_DGRAM: 'udp',
    }

    PSUTIL_FAMILY_MAPPING = {
        socket.AF_INET: '4',
        socket.AF_INET6: '6',
    }

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(
            self, name, init_config,
            agentConfig, instances=instances)
        if instances is not None and len(instances) > 1:
            raise Exception("Network check only supports one configured instance.")

    def check(self, instance):
        if instance is None:
            instance = {}

        self._excluded_ifaces = instance.get('excluded_interfaces', [])
        self._collect_cx_state = instance.get(
            'collect_connection_state', False)
        self._collect_rate_metrics = instance.get(
            'collect_rate_metrics', True)
        self._collect_count_metrics = instance.get(
            'collect_count_metrics', False)

        # This decides whether we should split or combine connection states,
        # along with a few other things
        self._setup_metrics(instance)

        self._exclude_iface_re = None
        exclude_re = instance.get('excluded_interface_re', None)
        if exclude_re:
            self.log.debug("Excluding network devices matching: %s" % exclude_re)
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
                }
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
                }
            }

    def _submit_netmetric(self, metric, value, tags=None):
        if self._collect_rate_metrics:
            self.rate(metric, value, tags=tags)
        if self._collect_count_metrics:
            self.monotonic_count('{}.count'.format(metric), value, tags=tags)

    def _submit_devicemetrics(self, iface, vals_by_metric, tags):
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return False

        expected_metrics = [
            'bytes_rcvd',
            'bytes_sent',
            'packets_in.count',
            'packets_in.error',
            'packets_out.count',
            'packets_out.error',
        ]
        for m in expected_metrics:
            assert m in vals_by_metric
        assert len(vals_by_metric) == len(expected_metrics)

        count = 0
        for metric, val in vals_by_metric.iteritems():
            self.rate('system.net.%s' % metric, val, device_name=iface, tags=tags)
            count += 1
        self.log.debug("tracked %s network metrics for interface %s" % (count, iface))

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
            self.warning("Cannot collect connection state: currently with a custom /proc path: %s" % proc_location)
            return False

        return True

    def _check_linux(self, instance):
        """
        _check_linux can be run inside a container and still collects the network metrics from the host
        For that procfs_path can be set to something like "/host/proc"
        When a custom procfs_path is set, the collect_connection_state option is ignored
        """
        proc_location = self.agentConfig.get('procfs_path', '/proc').rstrip('/')
        custom_tags = instance.get('tags', [])

        if Platform.is_containerized() and proc_location != "/proc":
            proc_location = "%s/1" % proc_location

        if self._is_collect_cx_state_runnable(proc_location):
            try:
                self.log.debug("Using `ss` to collect connection state")
                # Try using `ss` for increased performance over `netstat`
                for ip_version in ['4', '6']:
                    for protocol in ['tcp', 'udp']:
                        # Call `ss` for each IP version because there's no built-in way of distinguishing
                        # between the IP versions in the output
                        # Also calls `ss` for each protocol, because on some systems (e.g. Ubuntu 14.04), there is a
                        # bug that print `tcp` even if it's `udp`
                        output, _, _ = get_subprocess_output(["ss", "-n", "-{0}".format(protocol[0]),
                                                              "-a", "-{0}".format(ip_version)], self.log)
                        lines = output.splitlines()

                        # State      Recv-Q Send-Q     Local Address:Port       Peer Address:Port
                        # UNCONN     0      0              127.0.0.1:8125                  *:*
                        # ESTAB      0      0              127.0.0.1:37036         127.0.0.1:8125
                        # UNCONN     0      0        fe80::a00:27ff:fe1c:3c4:123          :::*
                        # TIME-WAIT  0      0          90.56.111.177:56867        46.105.75.4:143
                        # LISTEN     0      0       ::ffff:127.0.0.1:33217  ::ffff:127.0.0.1:7199
                        # ESTAB      0      0       ::ffff:127.0.0.1:58975  ::ffff:127.0.0.1:2181

                        metrics = self._parse_linux_cx_state(lines[1:], self.tcp_states['ss'], 0, protocol=protocol,
                                                             ip_version=ip_version)
                        # Only send the metrics which match the loop iteration's ip version
                        for stat, metric in self.cx_state_gauge.iteritems():
                            if stat[0].endswith(ip_version) and stat[0].startswith(protocol):
                                self.gauge(metric, metrics.get(metric), tags=custom_tags)

            except OSError:
                self.log.info("`ss` not found: using `netstat` as a fallback")
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
                for metric, value in metrics.iteritems():
                    self.gauge(metric, value, tags=custom_tags)
            except SubprocessOutputEmptyError:
                self.log.exception("Error collecting connection stats.")

        proc_dev_path = "{}/net/dev".format(proc_location)
        with open(proc_dev_path, 'r') as proc:
            lines = proc.readlines()
        # Inter-|   Receive                                                 |  Transmit
        #  face |bytes     packets errs drop fifo frame compressed multicast|bytes       packets errs drop fifo colls carrier compressed # noqa: E501
        #     lo:45890956   112797   0    0    0     0          0         0    45890956   112797    0    0    0     0       0          0 # noqa: E501
        #   eth0:631947052 1042233   0   19    0   184          0      1206  1208625538  1320529    0    0    0     0       0          0 # noqa: E501
        #   eth1:       0        0   0    0    0     0          0         0           0        0    0    0    0     0       0          0 # noqa: E501
        for l in lines[2:]:
            cols = l.split(':', 1)
            x = cols[1].split()
            # Filter inactive interfaces
            if self._parse_value(x[0]) or self._parse_value(x[8]):
                iface = cols[0].strip()
                metrics = {
                    'bytes_rcvd': self._parse_value(x[0]),
                    'bytes_sent': self._parse_value(x[8]),
                    'packets_in.count': self._parse_value(x[1]),
                    'packets_in.error': self._parse_value(x[2]) + self._parse_value(x[3]),
                    'packets_out.count': self._parse_value(x[9]),
                    'packets_out.error': self._parse_value(x[10]) + self._parse_value(x[11]),
                }
                self._submit_devicemetrics(iface, metrics, custom_tags)

        netstat_data = {}
        for f in ['netstat', 'snmp']:
            proc_data_path = "{}/net/{}".format(proc_location, f)
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
            'Tcp': {
                'RetransSegs': 'system.net.tcp.retrans_segs',
                'InSegs': 'system.net.tcp.in_segs',
                'OutSegs': 'system.net.tcp.out_segs',
            },
            'TcpExt': {
                'ListenOverflows': 'system.net.tcp.listen_overflows',
                'ListenDrops': 'system.net.tcp.listen_drops',
                'TCPBacklogDrop': 'system.net.tcp.backlog_drops',
                'TCPRetransFail': 'system.net.tcp.failed_retransmits',
            },
            'Udp': {
                'InDatagrams': 'system.net.udp.in_datagrams',
                'NoPorts': 'system.net.udp.no_ports',
                'InErrors': 'system.net.udp.in_errors',
                'OutDatagrams': 'system.net.udp.out_datagrams',
                'RcvbufErrors': 'system.net.udp.rcv_buf_errors',
                'SndbufErrors': 'system.net.udp.snd_buf_errors',
                'InCsumErrors': 'system.net.udp.in_csum_errors'
            }
        }

        # Skip the first line, as it's junk
        for k in nstat_metrics_names:
            for met in nstat_metrics_names[k]:
                if met in netstat_data.get(k, {}):
                    self._submit_netmetric(nstat_metrics_names[k][met], self._parse_value(netstat_data[k][met]),
                                           tags=custom_tags)

    def _parse_linux_cx_state(self, lines, tcp_states, state_col, protocol=None, ip_version=None):
        """
        Parse the output of the command that retrieves the connection state (either `ss` or `netstat`)
        Returns a dict metric_name -> value
        """
        metrics = dict.fromkeys(self.cx_state_gauge.values(), 0)
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
                    self.log.error("%s not found in %s; cannot parse" % (h, headers))
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

    def _check_solaris(self, instance):
        # Can't get bytes sent and received via netstat
        # Default to kstat -p link:0:
        custom_tags = instance.get('tags', [])
        try:
            netstat, _, _ = get_subprocess_output(["kstat", "-p", "link:0:"], self.log)
            metrics_by_interface = self._parse_solaris_netstat(netstat)
            for interface, metrics in metrics_by_interface.iteritems():
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

        for metric, value in metrics.iteritems():
            self.gauge(metric, value, tags=tags)

    def _cx_counters_psutil(self, tags=None):
        """
        Collect metrics about interfaces counters using psutil
        """
        tags = [] if tags is None else tags
        for iface, counters in psutil.net_io_counters(pernic=True).iteritems():
            metrics = {
                'bytes_rcvd': counters.bytes_recv,
                'bytes_sent': counters.bytes_sent,
                'packets_in.count': counters.packets_recv,
                'packets_in.error': counters.errin,
                'packets_out.count': counters.packets_sent,
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
