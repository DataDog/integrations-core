# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import time
from collections import namedtuple
from fnmatch import fnmatch

import pymysql

from datadog_checks.base.checks import AgentCheck

try:
    import rrdtool
except ImportError:
    rrdtool = None


CFUNC_TO_AGGR = {'AVERAGE': 'avg', 'MAXIMUM': 'max', 'MINIMUM': 'min'}

CACTI_TO_DD = {
    'hdd_free': 'system.disk.free',
    'hdd_used': 'system.disk.used',
    'swap_free': 'system.swap.free',
    'load_1min': 'system.load.1',
    'load_5min': 'system.load.5',
    'load_15min': 'system.load.15',
    'mem_buffers': 'system.mem.buffered',
    'proc': 'system.proc.running',
    'users': 'system.users.current',
    'mem_swap': 'system.swap.free',
    'ping': 'system.ping.latency',
}


class CactiCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(CactiCheck, self).__init__(name, init_config, instances)
        self.last_ts = {}
        # Load the instance config
        self.config = self._get_config(instances[0])

    @staticmethod
    def get_library_versions():
        if rrdtool is not None:
            return {"rrdtool": rrdtool.__version__}
        return {"rrdtool": "Not Found"}

    def check(self, instance):
        if rrdtool is None:
            raise Exception("Unable to import python rrdtool module")

        connection = self._get_connection()

        self.log.debug("Connected to MySQL to fetch Cacti metadata")

        # Get whitelist patterns, if available
        patterns = self._get_whitelist_patterns(self.config.whitelist)

        # Fetch the RRD metadata from MySQL
        rrd_meta = self._fetch_rrd_meta(
            connection, self.config.rrd_path, patterns, self.config.field_names, self.config.tags
        )

        # Load the metrics from each RRD, tracking the count as we go
        metric_count = 0
        for hostname, device_name, rrd_path in rrd_meta:
            m_count = self._read_rrd(rrd_path, hostname, device_name, self.config.tags)
            metric_count += m_count

        self.gauge('cacti.metrics.count', metric_count, tags=self.config.tags)

    def _get_connection(self):
        return pymysql.connect(
            self.config.host, self.config.user, self.config.password, self.config.db, self.config.port
        )

    def _get_whitelist_patterns(self, whitelist=None):
        patterns = []
        if whitelist:
            if not os.path.isfile(whitelist) or not os.access(whitelist, os.R_OK):
                # Don't run the check if the whitelist is unavailable
                self.log.exception("Unable to read whitelist file at %s", whitelist)

            wl = open(whitelist)
            for line in wl:
                patterns.append(line.strip())
            wl.close()

        return patterns

    @classmethod
    def _get_config(cls, instance):
        required = ['mysql_host', 'mysql_user', 'rrd_path']
        for param in required:
            if not instance.get(param):
                raise Exception("Cacti instance missing %s. Skipping." % (param))

        host = instance.get('mysql_host')
        user = instance.get('mysql_user')
        password = instance.get('mysql_password', '') or ''
        db = instance.get('mysql_db', 'cacti')
        port = instance.get('mysql_port')
        rrd_path = instance.get('rrd_path')
        whitelist = instance.get('rrd_whitelist')
        field_names = instance.get('field_names', ['ifName', 'dskDevice'])
        tags = instance.get('tags', [])

        Config = namedtuple(
            'Config', ['host', 'user', 'password', 'db', 'port', 'rrd_path', 'whitelist', 'field_names', 'tags']
        )

        return Config(host, user, password, db, port, rrd_path, whitelist, field_names, tags)

    @staticmethod
    def _get_rrd_info(rrd_path):
        return rrdtool.info(rrd_path)

    @staticmethod
    def _get_rrd_fetch(rrd_path, c, start):
        return rrdtool.fetch(rrd_path, c, '--start', str(start))

    def _read_rrd(self, rrd_path, hostname, device_name, tags):
        """ Main metric fetching method."""
        metric_count = 0

        try:
            info = self._get_rrd_info(rrd_path)
        except Exception:
            # Unable to read RRD file, ignore it
            self.log.exception("Unable to read RRD file at %s", rrd_path)
            return metric_count

        # Find the consolidation functions for the RRD metrics
        c_funcs = set([v for k, v in info.items() if k.endswith('.cf')])
        if not c_funcs:
            self.log.debug("No funcs found for %s", rrd_path)

        for c in list(c_funcs):
            last_ts_key = '%s.%s' % (rrd_path, c)
            if last_ts_key not in self.last_ts:
                self.last_ts[last_ts_key] = int(time.time())
                continue

            start = self.last_ts[last_ts_key]
            last_ts = start

            try:
                fetched = self._get_rrd_fetch(rrd_path, c, start)
            except rrdtool.error:
                # Start time was out of range, skip this RRD
                self.log.warning("Time %s out of range for %s", rrd_path, start)
                return metric_count

            # Extract the data
            (start_ts, end_ts, interval) = fetched[0]
            metric_names = fetched[1]
            points = fetched[2]
            for k, m_name in enumerate(metric_names):
                m_name = self._format_metric_name(m_name, c)
                for i, p in enumerate(points):
                    ts = start_ts + (i * interval)

                    if p[k] is None:
                        continue

                    # Save this metric as a gauge
                    val = self._transform_metric(m_name, p[k])
                    self.gauge(m_name, val, hostname=hostname, device_name=device_name, tags=tags)
                    metric_count += 1
                    last_ts = ts + interval

            # Update the last timestamp based on the last valid metric
            self.last_ts[last_ts_key] = last_ts
        return metric_count

    def _fetch_rrd_meta(self, connection, rrd_path_root, whitelist, field_names, tags):
        """ Fetch metadata about each RRD in this Cacti DB, returning a list of
            tuples of (hostname, device_name, rrd_path).
        """

        def _in_whitelist(rrd):
            path = rrd.replace('<path_rra>/', '')
            for pattern in whitelist:
                if fnmatch(path, pattern):
                    return True
            return False

        c = connection.cursor()

        and_parameters = " OR ".join(["hsc.field_name = '%s'" % field_name for field_name in field_names])

        # Check for the existence of the `host_snmp_cache` table
        rrd_query = """
            SELECT
                h.hostname as hostname,
                hsc.field_value as device_name,
                dt.data_source_path as rrd_path
            FROM data_local dl
                JOIN host h on dl.host_id = h.id
                JOIN data_template_data dt on dt.local_data_id = dl.id
                LEFT JOIN host_snmp_cache hsc on h.id = hsc.host_id
                    AND dl.snmp_index = hsc.snmp_index
            WHERE dt.data_source_path IS NOT NULL
            AND dt.data_source_path != ''
            AND ({} OR hsc.field_name is NULL) """.format(
            and_parameters
        )

        c.execute(rrd_query)
        res = []
        for hostname, device_name, rrd_path in c.fetchall():
            if not whitelist or _in_whitelist(rrd_path):
                if hostname in ('localhost', '127.0.0.1'):
                    hostname = self.hostname
                rrd_path = rrd_path.replace('<path_rra>', rrd_path_root)
                device_name = device_name or None
                res.append((hostname, device_name, rrd_path))

        # Collect stats
        num_hosts = len(set([r[0] for r in res]))
        self.gauge('cacti.rrd.count', len(res), tags=tags)
        self.gauge('cacti.hosts.count', num_hosts, tags=tags)

        return res

    @staticmethod
    def _format_metric_name(m_name, cfunc):
        """ Format a cacti metric name into a Datadog-friendly name. """
        try:
            aggr = CFUNC_TO_AGGR[cfunc]
        except KeyError:
            aggr = cfunc.lower()

        try:
            m_name = CACTI_TO_DD[m_name]
            if aggr != 'avg':
                m_name += '.{}'.format(aggr)
            return m_name
        except KeyError:
            return "cacti.{}.{}".format(m_name.lower(), aggr)

    @staticmethod
    def _transform_metric(m_name, val):
        """ Add any special case transformations here. """
        # Report memory in MB
        if m_name[0:11] in ('system.mem.', 'system.disk'):
            return val / 1024
        return val
