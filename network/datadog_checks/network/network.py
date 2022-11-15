# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Collects network metrics.
"""

import distutils.spawn
import re
import socket

import psutil
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output

from .const import SOLARIS_TCP_METRICS

try:
    import fcntl
except ImportError:
    fcntl = None

if PY3:
    long = int


class Network(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    PSUTIL_TYPE_MAPPING = {socket.SOCK_STREAM: 'tcp', socket.SOCK_DGRAM: 'udp'}
    PSUTIL_FAMILY_MAPPING = {socket.AF_INET: '4', socket.AF_INET6: '6'}

    def __new__(cls, name, init_config, instances):
        if cls is not Network:
            # avoid infinite recursion
            return super(Network, cls).__new__(cls)
        if Platform.is_linux():
            from .check_linux import LinuxNetwork

            return LinuxNetwork(name, init_config, instances)
        elif Platform.is_windows():
            from .check_windows import WindowsNetwork

            return WindowsNetwork(name, init_config, instances)
        elif Platform.is_bsd():
            from .check_bsd import BSDNetwork

            return BSDNetwork(name, init_config, instances)
        else:
            # Todo: remove later in the refactor
            return super(Network, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(Network, self).__init__(name, init_config, instances)
        self._excluded_ifaces = self.instance.get('excluded_interfaces', [])
        self._collect_cx_state = self.instance.get('collect_connection_state', False)
        self._collect_rate_metrics = self.instance.get('collect_rate_metrics', True)
        self._collect_count_metrics = self.instance.get('collect_count_metrics', False)
        self._collect_ena_metrics = self.instance.get('collect_aws_ena_metrics', False)
        self._collect_ethtool_metrics = self.instance.get('collect_ethtool_metrics', False)
        self._collect_ethtool_stats = self._collect_ena_metrics or self._collect_ethtool_metrics
        self._exclude_iface_re = None
        exclude_re = self.instance.get('excluded_interface_re', None)
        if exclude_re:
            self.log.debug("Excluding network devices matching: %s", exclude_re)
            self._exclude_iface_re = re.compile(exclude_re)
        # This decides whether we should split or combine connection states,
        # along with a few other things
        self._setup_metrics(self.instance)
        self.check_initializations.append(self._validate)

    def _validate(self):
        if not isinstance(self._excluded_ifaces, list):
            raise ConfigurationError(
                "Expected 'excluded_interfaces' to be a list, got '{}'".format(type(self._excluded_ifaces).__name__)
            )

        if fcntl is None and self._collect_ethtool_stats:
            if Platform.is_windows():
                raise ConfigurationError(
                    "fcntl is not available on Windows, "
                    "collect_aws_ena_metrics and collect_ethtool_metrics should be disabled"
                )
            else:
                raise ConfigurationError(
                    "fcntl not importable, collect_aws_ena_metrics and collect_ethtool_metrics should be disabled"
                )

    def check(self, _):
        if Platform.is_solaris():
            self._check_solaris(self.instance)
        else:
            raise CheckException("Not implemented")

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

    def submit_devicemetrics(self, iface, vals_by_metric, tags):
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return

        # adding the device to the tags as device_name is deprecated
        metric_tags = [] if tags is None else tags[:]
        metric_tags.append('device:{}'.format(iface))

        expected_metrics = self.get_expected_metrics()
        for m in expected_metrics:
            assert m in vals_by_metric, 'Missing expected metric {}'.format(m)
        assert len(vals_by_metric) == len(expected_metrics), 'Expected {} metrics, found {}'.format(
            len(vals_by_metric), len(expected_metrics)
        )

        count = 0
        for metric, val in iteritems(vals_by_metric):
            self.rate('system.net.%s' % metric, val, tags=metric_tags)
            count += 1
        self.log.debug("tracked %s network metrics for interface %s", count, iface)

    def get_expected_metrics(self):
        expected_metrics = [
            'bytes_rcvd',
            'bytes_sent',
            'packets_in.count',
            'packets_in.error',
            'packets_out.count',
            'packets_out.error',
        ]
        return expected_metrics

    def parse_long(self, v):
        try:
            return long(v)
        except ValueError:
            return 0

    def submit_regexed_values(self, output, regex_list, tags):
        lines = output.splitlines()
        for line in lines:
            for regex, metric in regex_list:
                value = re.match(regex, line)
                if value:
                    self._submit_netmetric(metric, self.parse_long(value.group(1)), tags=tags)

    def is_collect_cx_state_runnable(self, proc_location):
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

    @staticmethod
    def get_net_proc_base_location(proc_location):
        if Platform.is_containerized() and proc_location != "/proc":
            net_proc_base_location = "%s/1" % proc_location
        else:
            net_proc_base_location = proc_location
        return net_proc_base_location

    def _get_metrics(self):
        return {val: 0 for val in itervalues(self.cx_state_gauge)}

    def parse_cx_state(self, lines, tcp_states, state_col, protocol=None, ip_version=None):
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

    def _check_solaris(self, instance):
        # Can't get bytes sent and received via netstat
        # Default to kstat -p link:0:
        custom_tags = instance.get('tags', [])
        try:
            netstat, _, _ = get_subprocess_output(["kstat", "-p", "link:0:"], self.log)
            metrics_by_interface = self._parse_solaris_netstat(netstat)
            for interface, metrics in iteritems(metrics_by_interface):
                self.submit_devicemetrics(interface, metrics, custom_tags)
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
            self.submit_regexed_values(netstat, SOLARIS_TCP_METRICS, custom_tags)
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
            metrics[ddname] = self.parse_long(cols[1])
            metrics_by_interface[iface] = metrics

        return metrics_by_interface
