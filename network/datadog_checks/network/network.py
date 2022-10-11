# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Collects network metrics.
"""

import distutils.spawn
import os
import re
import socket
from collections import defaultdict

import psutil
from six import PY3, iteritems, itervalues

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.subprocess_output import SubprocessOutputEmptyError, get_subprocess_output

from . import ethtool
from .const import ENA_METRIC_NAMES, ENA_METRIC_PREFIX

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


class Network(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    PSUTIL_TYPE_MAPPING = {socket.SOCK_STREAM: 'tcp', socket.SOCK_DGRAM: 'udp'}
    PSUTIL_FAMILY_MAPPING = {socket.AF_INET: '4', socket.AF_INET6: '6'}

    def __init__(self, name, init_config, instances):
        super(Network, self).__init__(name, init_config, instances)
        self._excluded_ifaces = self.instance.get('excluded_interfaces', [])
        self._collect_cx_state = self.instance.get('collect_connection_state', False)
        self._collect_cx_queues = self.instance.get('collect_connection_queues', False)
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
        if Platform.is_linux():
            self._check_linux(self.instance)
        elif Platform.is_bsd():
            self._check_bsd(self.instance)
        elif Platform.is_solaris():
            self._check_solaris(self.instance)
        elif Platform.is_windows():
            self._check_psutil(self.instance)

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
            return

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
        if iface in self._excluded_ifaces or (self._exclude_iface_re and self._exclude_iface_re.match(iface)):
            # Skip this network interface.
            return
        if iface in ['lo', 'lo0']:
            # Skip loopback ifaces as they don't support SIOCETHTOOL
            return

        driver_name, driver_version, ethtool_stats_names, ethtool_stats = self._fetch_ethtool_stats(iface)
        tags = [] if custom_tags is None else custom_tags[:]
        tags.append('driver_name:{}'.format(driver_name))
        tags.append('driver_version:{}'.format(driver_version))
        if self._collect_ena_metrics:
            ena_metrics = ethtool.get_ena_metrics(ethtool_stats_names, ethtool_stats)
            self._submit_ena_metrics(iface, ena_metrics, tags)
        if self._collect_ethtool_metrics:
            ethtool_metrics = ethtool.get_ethtool_metrics(driver_name, ethtool_stats_names, ethtool_stats)
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
            driver_name, driver_version = ethtool.get_ethtool_drvinfo(iface, ethtool_socket)
            stats_names, stats = ethtool.get_ethtool_stats(iface, ethtool_socket)
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
