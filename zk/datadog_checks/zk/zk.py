# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

"""
Besides the usual zookeeper state of `leader`, `follower`, `observer` and `standalone`,
this check will report three other states:

    `down`: the check cannot connect to zookeeper
    `inactive`: the zookeeper instance has lost connection to the cluster
    `unknown`: an unexpected error has occurred in this check

States can be accessed through the gauge `zookeeper.instances.<state>,
through the set `zookeeper.instances`, or through the `mode:<state>` tag.

Parses the response from zookeeper's `stat` admin command, tested with Zookeeper
versions 3.0.0 to 3.4.5, which looks like:
```
Zookeeper version: 3.2.2--1, built on 03/16/2010 07:31 GMT
Clients:
 /10.42.114.160:32634[1](queued=0,recved=12,sent=0)
 /10.37.137.74:21873[1](queued=0,recved=53613,sent=0)
 /10.37.137.74:21876[1](queued=0,recved=57436,sent=0)
 /10.115.77.32:32990[1](queued=0,recved=16,sent=0)
 /10.37.137.74:21891[1](queued=0,recved=55011,sent=0)
 /10.37.137.74:21797[1](queued=0,recved=19431,sent=0)

Latency min/avg/max: -10/0/20007
Received: 101032173
Sent: 0
Outstanding: 0
Zxid: 0x1034799c7
Mode: leader
Node count: 487
```


The following is an example of the `mntr` commands output, tested with ZooKeeper
3.4.5:
```
zk_version  3.4.5-cdh4.4.0--1, built on 09/04/2013 01:46 GMT
zk_avg_latency  0
zk_max_latency  0
zk_min_latency  0
zk_packets_received 4
zk_packets_sent 3
zk_num_alive_connections    1
zk_outstanding_requests 0
zk_server_state standalone
zk_znode_count  4
zk_watch_count  0
zk_ephemerals_count 0
zk_approximate_data_size    27
zk_open_file_descriptor_count   29
zk_max_file_descriptor_count    4096
```

"""
import re
import socket
import struct
from collections import defaultdict
from contextlib import closing

from packaging.version import Version
from six import PY3, StringIO, iteritems

from datadog_checks.base import AgentCheck, ensure_bytes, ensure_unicode, is_affirmative

if PY3:
    long = int


class ZKConnectionFailure(Exception):
    """Raised when we are unable to connect or get the output of a command."""

    pass


class ZKMetric(tuple):
    """
    A Zookeeper metric.
    Tuple with optional values:
      - `m_type`: metric type (default is 'gauge')
      - `m_tags`: list of tags (default is None)
    """

    def __new__(cls, name, value, m_type="gauge", m_tags=None):
        if m_tags is None:
            m_tags = []
        return super(ZKMetric, cls).__new__(cls, [name, value, m_type, m_tags])


class ZookeeperCheck(AgentCheck):
    """
    ZooKeeper AgentCheck.

    Parse content from `stat` and `mntr`(if available) commands to retrieve health cluster metrics.
    """

    # example match:
    # "Zookeeper version: 3.4.10-39d3a4f269333c922ed3db283be479f9deacaa0f, built on 03/23/2017 10:13 GMT"
    # This regex matches the entire version rather than <major>.<minor>.<patch>
    METADATA_VERSION_PATTERN = re.compile(r'\w+ version: v?([^,]+)')
    METRIC_TAGGED_PATTERN = re.compile(r'(\w+){(\w+)="(.+)"}\s+(\S+)')

    SOURCE_TYPE_NAME = 'zookeeper'

    STATUS_TYPES = ['leader', 'follower', 'observer', 'standalone', 'down', 'inactive']

    # `mntr` information to report as `rate`
    _MNTR_RATES = {'zk_packets_received', 'zk_packets_sent'}

    def __init__(self, name, init_config, instances):
        super(ZookeeperCheck, self).__init__(name, init_config, instances)
        self.host = self.instance.get('host', 'localhost')
        self.port = int(self.instance.get('port', 2181))
        self.timeout = float(self.instance.get('timeout', 3.0))
        self.expected_mode = self.instance.get('expected_mode') or []
        if isinstance(self.expected_mode, str):
            self.expected_mode = [self.expected_mode]
        self.expected_mode = [x.strip() for x in self.expected_mode]
        self.base_tags = list(set(self.instance.get('tags', [])))
        self.sc_tags = ["host:{0}".format(self.host), "port:{0}".format(self.port)] + self.base_tags
        self.should_report_instance_mode = is_affirmative(self.instance.get("report_instance_mode", True))
        self.use_tls = is_affirmative(self.instance.get('use_tls', False))

    def check(self, _):
        # Send a service check based on the `ruok` response.
        # Set instance status to down if not ok.
        status = None
        message = None
        try:
            ruok_out = self._send_command('ruok')
        except ZKConnectionFailure:
            # The server should not respond at all if it's not OK.
            status = AgentCheck.CRITICAL
            message = 'No response from `ruok` command'
            self.increment('zookeeper.timeouts')

            if self.should_report_instance_mode:
                self.report_instance_mode('down')
            raise
        else:
            ruok_out.seek(0)
            ruok = ruok_out.readline()
            if ruok == 'imok':
                status = AgentCheck.OK
                message = None
            else:
                status = AgentCheck.WARNING
                message = u'Response from the server: %s' % ruok
        finally:
            self.service_check('zookeeper.ruok', status, message=message, tags=self.sc_tags)

        # Read metrics from the `stat` output
        try:
            stat_out = self._send_command('stat')
        except ZKConnectionFailure:
            self.increment('zookeeper.timeouts')
            if self.should_report_instance_mode:
                self.report_instance_mode('down')
            raise
        except Exception as e:
            self.warning(e)
            self.increment('zookeeper.datadog_client_exception')
            if self.should_report_instance_mode:
                self.report_instance_mode('unknown')
            raise
        else:
            # Parse the response
            metrics, new_tags, mode, zk_version = self.parse_stat(stat_out)

            # Write the data
            if mode != 'inactive':
                for metric, value, m_type, m_tags in metrics:
                    submit_metric = getattr(self, m_type)
                    submit_metric(metric, value, tags=self.base_tags + m_tags + new_tags)

            if self.should_report_instance_mode:
                self.report_instance_mode(mode)

            if self.expected_mode:
                if mode in self.expected_mode:
                    status = AgentCheck.OK
                    message = None
                else:
                    status = AgentCheck.CRITICAL
                    message = u"Server is in %s mode but check expects %s mode" % (
                        mode,
                        ' or '.join(self.expected_mode),
                    )
                self.service_check('zookeeper.mode', status, message=message, tags=self.sc_tags)

        # Read metrics from the `mntr` output
        if zk_version and Version(zk_version) > Version("3.4.0"):
            try:
                mntr_out = self._send_command('mntr')
            except ZKConnectionFailure:
                self.increment('zookeeper.timeouts')
                if self.should_report_instance_mode:
                    self.report_instance_mode('down')
                raise
            except Exception as e:
                self.warning(str(e))
                self.increment('zookeeper.datadog_client_exception')
                if self.should_report_instance_mode:
                    self.report_instance_mode('unknown')
                raise
            else:
                metrics, mode = self.parse_mntr(mntr_out)
                mode_tag = "mode:%s" % mode
                if mode != 'inactive':
                    for metric, value, m_type, m_tags in metrics:
                        submit_metric = getattr(self, m_type)
                        submit_metric(metric, value, tags=self.base_tags + m_tags + [mode_tag])

                if self.should_report_instance_mode:
                    self.report_instance_mode(mode)

    def report_instance_mode(self, mode):
        gauges = defaultdict(int)
        if mode not in self.STATUS_TYPES:
            mode = "unknown"

        tags = self.base_tags + ['mode:%s' % mode]
        self.gauge('zookeeper.instances', 1, tags=tags)
        gauges[mode] = 1
        for k, v in iteritems(gauges):
            gauge_name = 'zookeeper.instances.%s' % k
            self.gauge(gauge_name, v, tags=self.base_tags)

    @staticmethod
    def _get_data(sock, command):
        chunk_size = 1024
        max_reads = 10000
        buf = StringIO()
        # Zookeeper expects a newline character at the end of commands, add it to prevent removal by proxies
        sock.sendall(ensure_bytes(command + "\n"))
        # Read the response into a StringIO buffer
        chunk = ensure_unicode(sock.recv(chunk_size))
        buf.write(chunk)
        num_reads = 1

        while chunk:
            if num_reads > max_reads:
                # Safeguard against an infinite loop
                raise Exception("Read %s bytes before exceeding max reads of %s. " % (buf.tell(), max_reads))
            chunk = ensure_unicode(sock.recv(chunk_size))
            buf.write(chunk)
            num_reads += 1
        return buf

    def _send_command(self, command):
        try:
            with closing(socket.create_connection((self.host, self.port))) as sock:
                sock.settimeout(self.timeout)
                if self.use_tls:
                    context = self.get_tls_context()
                    with closing(context.wrap_socket(sock, server_hostname=self.host)) as ssock:
                        return self._get_data(ssock, command)
                else:
                    return self._get_data(sock, command)
        except (socket.timeout, socket.error) as exc:
            raise ZKConnectionFailure(exc)  # Include `exc` message for PY2.

    def parse_stat(self, buf):
        """
        `buf` is a readable file-like object
        returns a tuple: (metrics, tags, mode, version)
        """
        metrics = []
        buf.seek(0)

        # Check the version line to make sure we parse the rest of the
        # body correctly. Particularly, the Connections val was added in
        # >= 3.4.4.
        start_line = buf.readline()
        # this is to grab the additional version information
        total_match = self.METADATA_VERSION_PATTERN.search(start_line)
        if total_match is None:
            return None, None, "inactive", None
        else:
            version = total_match.group(1).split("-")[0]
            # grabs the entire version number for inventories.
            metadata_version = total_match.group(1)
            self.set_metadata('version', metadata_version)
        has_connections_val = Version(version) > Version("3.4.4")

        # Clients:
        buf.readline()  # skip the Clients: header
        connections = 0
        client_line = buf.readline().strip()
        if client_line:
            connections += 1
        while client_line:
            client_line = buf.readline().strip()
            if client_line:
                connections += 1

        # Latency min/avg/max: -10/0.0/20007
        _, value = buf.readline().split(':')
        l_min, l_avg, l_max = [float(v) for v in value.strip().split('/')]
        metrics.append(ZKMetric('zookeeper.latency.min', l_min))
        metrics.append(ZKMetric('zookeeper.latency.avg', l_avg))
        metrics.append(ZKMetric('zookeeper.latency.max', l_max))

        # Received: 101032173
        _, value = buf.readline().split(':')
        # Fixme: This metric name is wrong. It should be removed in a major version of the agent
        # See https://github.com/DataDog/integrations-core/issues/816
        metrics.append(ZKMetric('zookeeper.bytes_received', long(value.strip())))
        metrics.append(ZKMetric('zookeeper.packets.received', long(value.strip()), "rate"))

        # Sent: 1324
        _, value = buf.readline().split(':')
        # Fixme: This metric name is wrong. It should be removed in a major version of the agent
        # See https://github.com/DataDog/integrations-core/issues/816
        metrics.append(ZKMetric('zookeeper.bytes_sent', long(value.strip())))
        metrics.append(ZKMetric('zookeeper.packets.sent', long(value.strip()), "rate"))

        if has_connections_val:
            # Connections: 1
            _, value = buf.readline().split(':')
            metrics.append(ZKMetric('zookeeper.connections', int(value.strip())))
        else:
            # If the zk version doesn't explicitly give the Connections val,
            # use the value we computed from the client list.
            metrics.append(ZKMetric('zookeeper.connections', connections))

        # Outstanding: 0
        _, value = buf.readline().split(':')
        metrics.append(ZKMetric('zookeeper.outstanding_requests', long(value.strip())))

        # Zxid: 0x1034799c7
        _, value = buf.readline().split(':')
        # Parse as a 64 bit hex int
        zxid = long(value.strip(), 16)
        # convert to bytes
        zxid_bytes = struct.pack('>q', zxid)
        # the higher order 4 bytes is the epoch
        (zxid_epoch,) = struct.unpack('>i', zxid_bytes[0:4])
        # the lower order 4 bytes is the count
        (zxid_count,) = struct.unpack('>i', zxid_bytes[4:8])

        metrics.append(ZKMetric('zookeeper.zxid.epoch', zxid_epoch))
        metrics.append(ZKMetric('zookeeper.zxid.count', zxid_count))

        # Mode: leader
        _, value = buf.readline().split(':')
        mode = value.strip().lower()
        tags = [u'mode:' + mode]

        # Node count: 487
        _, value = buf.readline().split(':')
        metrics.append(ZKMetric('zookeeper.nodes', long(value.strip())))

        return metrics, tags, mode, version

    def parse_mntr(self, buf):
        """
        Parse `mntr` command's content.
        `buf` is a readable file-like object

        Returns: a tuple (metrics, mode)
        if mode == 'inactive', metrics will be None
        """
        buf.seek(0)
        first = buf.readline()  # First is version string or error
        if first == 'This ZooKeeper instance is not currently serving requests':
            return None, 'inactive'

        metrics = []
        mode = 'inactive'
        for line in buf:
            try:
                tags = []
                m = re.match(self.METRIC_TAGGED_PATTERN, line)
                if m:
                    key, tag_name, tag_val, value = m.groups()
                    tags.append('{}:{}'.format(tag_name, tag_val))
                else:
                    try:
                        key, value = line.split()
                    except ValueError as e:
                        self.log.debug("Unexpected 'mntr' output `%s`: %s", line, str(e))
                        continue

                if key == "zk_server_state":
                    mode = value.lower()
                    continue

                # we are parsing version from the `stat` output for now
                if key == 'zk_version':
                    continue

                metric_name = self.normalize_metric_label(key)
                metric_type = "rate" if key in self._MNTR_RATES else "gauge"

                if value == 'NaN':
                    self.log.debug('Metric value "%s" is not supported for metric %s', value, key)
                    continue
                else:
                    metric_value = int(float(value))

                metrics.append(ZKMetric(metric_name, metric_value, metric_type, tags))

            except ValueError as e:
                self.log.warning("Cannot format `mntr` value from `%s`: %s", line, str(e))

            except Exception:
                self.log.exception("Unexpected exception occurred while parsing `mntr` command content:\n%s", buf)

        return metrics, mode

    @staticmethod
    def normalize_metric_label(key):
        if re.match('zk', key):
            key = key.replace('zk', 'zookeeper', 1)
        return key.replace('_', '.', 1)
