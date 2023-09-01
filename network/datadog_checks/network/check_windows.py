# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from collections import defaultdict

import psutil
from six import PY3, iteritems

from . import Network

if PY3:
    long = int


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
            self.submit_devicemetrics(iface, metrics, tags)

    def _parse_protocol_psutil(self, conn):
        """
        Returns a string describing the protocol for the given connection
        in the form `tcp4`, 'udp4` as in `self.cx_state_gauge`
        """
        protocol = self.PSUTIL_TYPE_MAPPING.get(conn.type, '')
        family = self.PSUTIL_FAMILY_MAPPING.get(conn.family, '')
        return '{}{}'.format(protocol, family)
