# (C) Datadog, Inc. 2019
# (C) 2018 Aerospike, Inc.
# (C) 2017 Red Sift
# (C) 2015 Pippio, Inc. All rights reserved.
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import re

import aerospike
from six import iteritems

from datadog_checks.base import AgentCheck

SOURCE_TYPE_NAME = 'aerospike'
SERVICE_CHECK_UP = '%s.cluster_up' % SOURCE_TYPE_NAME
SERVICE_CHECK_CONNECT = '%s.can_connect' % SOURCE_TYPE_NAME
CLUSTER_METRIC_TYPE = SOURCE_TYPE_NAME
NAMESPACE_METRIC_TYPE = '%s.namespace' % SOURCE_TYPE_NAME
NAMESPACE_TPS_METRIC_TYPE = '%s.namespace.tps' % SOURCE_TYPE_NAME
SINDEX_METRIC_TYPE = '%s.sindex' % SOURCE_TYPE_NAME
SET_METRIC_TYPE = '%s.set' % SOURCE_TYPE_NAME
MAX_AEROSPIKE_SETS = 200
MAX_AEROSPIKE_SINDEXS = 100

AEROSPIKE_CAP_MAP = {
    SINDEX_METRIC_TYPE: MAX_AEROSPIKE_SINDEXS,
    SET_METRIC_TYPE: MAX_AEROSPIKE_SETS,
}
AEROSPIKE_CAP_CONFIG_KEY_MAP = {
    SINDEX_METRIC_TYPE: "max_sindexs",
    SET_METRIC_TYPE: "max_sets",
}


def parse_namespace(data, namespace, secondary):
    idxs = []
    while data:
        line = data.pop(0)

        # $ asinfo -v 'sindex/phobos_sindex'
        # ns=phobos_sindex:set=longevity:indexname=str_100_idx:num_bins=1:bins=str_100_bin:type=TEXT:sync_state=synced:state=RW
        # ns=phobos_sindex:set=longevity:indexname=str_uniq_idx:num_bins=1:bins=str_uniq_bin:type=TEXT:sync_state=synced:state=RW
        # ns=phobos_sindex:set=longevity:indexname=int_uniq_idx:num_bins=1:bins=int_uniq_bin:type=INT SIGNED:\
        # sync_state=synced:state=RW
        #
        # $ asinfo -v 'sets/bar'
        # ns=bar:set=demo:objects=1:tombstones=0:memory_data_bytes=34:truncate_lut=0:stop-writes-count=0:set-enable-xdr=use-default:disable-eviction=false
        # ns=bar:set=demo2:objects=123456:tombstones=0:memory_data_bytes=8518464:truncate_lut=0:stop-writes-count=0:set-enable-xdr=use-default:disable-eviction=false

        match = re.match('^ns=%s:([^:]+:)?%s=([^:]+):.*$' % (namespace, secondary), line)
        if match is None:
            continue
        idxs.append(match.groups()[1])

    return idxs


class AerospikeCheck(AgentCheck):

    def __init__(self, name, init_config, instances):
        super(AerospikeCheck, self).__init__(name, init_config, instances)

        host = self.instance.get('host', 'localhost')
        port = int(self.instance.get('port', 3000))

        self._host = (host, port)
        self._metrics = set(self.instance.get('metrics', []))
        self._namespace_metrics = set(self.instance.get('namespace_metrics', []))
        self._required_namespaces = self.instance.get('namespaces')
        self._tags = self.instance.get('tags', [])

        # We'll connect on the first check run
        self._client = None

    def check(self, instance):
        if self._client is None:
            client = self.get_client()
            if client is None:
                return

            self._client = client

        self.collect_info('statistics', CLUSTER_METRIC_TYPE, required_keys=self._metrics, tags=self._tags)

        namespaces = self.get_namespaces()

        for ns in namespaces:
            namespace_tags = ['namespace:{}'.format(ns)]
            namespace_tags.extend(self._tags)

            self.collect_info(
                'namespace/{}'.format(ns),
                NAMESPACE_METRIC_TYPE,
                required_keys=self._namespace_metrics,
                tags=namespace_tags
            )

            sindex = self.get_info('sindex/{}'.format(ns))
            for idx in parse_namespace(sindex[:-1], ns, 'indexname'):
                sindex_tags = ['sindex:{}'.format(idx)]
                sindex_tags.extend(namespace_tags)
                self.collect_info('sindex/{}/{}'.format(ns, idx), SINDEX_METRIC_TYPE, tags=sindex_tags)

            sets = self.get_info('sets/{}'.format(ns))
            for s in parse_namespace(sets, ns, 'set'):
                set_tags = ['set:{}'.format(s)]
                set_tags.extend(namespace_tags)
                self.collect_info('sets/{}/{}'.format(ns, s), SET_METRIC_TYPE, separator=':', tags=set_tags)

        self.collect_throughput(namespaces)

        self.service_check(SERVICE_CHECK_UP, self.OK, tags=self._tags)

    def collect_info(self, command, metric_type, separator=';', required_keys=None, tags=None):
        entries = self.get_info(command, separator=separator)

        if required_keys:
            required_data = {}
            for entry in entries:
                key, value = entry.split('=', 1)
                if key in required_keys:
                    required_data[key] = value
        else:
            required_data = dict(entry.split('=', 1) for entry in entries)

        if metric_type in AEROSPIKE_CAP_MAP:
            cap = self.instance.get(AEROSPIKE_CAP_CONFIG_KEY_MAP[metric_type], AEROSPIKE_CAP_MAP[metric_type])
            if len(required_data) > cap:
                self.log.warn(
                    'Exceeded cap `{}` for metric type `{}` - please contact support'.format(cap, metric_type)
                )
                return

        for key, value in iteritems(required_data):
            self._send(metric_type, key, value, tags)

    def get_namespaces(self):
        namespaces = self.get_info('namespaces')

        if self._required_namespaces:
            return [ns for ns in namespaces if ns in self._required_namespaces]

        return namespaces

    def get_client(self):
        try:
            client = aerospike.client({'hosts': [self._host]}).connect()
        except Exception as e:
            self.log.error('Unable to connect to database: {}'.format(e))
            self.service_check(SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return client

    def get_info(self, command, separator=';'):
        # command\tKEY=VALUE;KEY=VALUE;...
        data = self._client.info_node(command, self._host)

        # Get rid of command and whitespace
        data = data[len(command):].strip()

        if not separator:
            return data

        return data.split(separator)

    def collect_throughput(self, namespaces):
        data = self.get_info('throughput:')

        while data:
            line = data.pop(0)

            # skip errors
            while line.startswith('error-'):
                if not data:
                    return
                line = data.pop(0)

            # $ asinfo -v 'throughput:'
            # {ns}-read:23:56:38-GMT,ops/sec;23:56:48,0.0;{ns}-write:23:56:38-GMT,ops/sec;23:56:48,0.0; \
            # error-no-data-yet-or-back-too-small;error-no-data-yet-or-back-too-small
            #
            # data = [ "{ns}-read..","23:56:40,0.0", "{ns}-write...","23:56:48,0.0" ... ]

            match = re.match('^{(.+)}-([^:]+):', line)
            if match is None:
                continue

            ns = match.groups()[0]
            if ns not in namespaces:
                continue

            key = match.groups()[1]
            if not data:
                # unexpected EOF
                return

            namespace_tags = ['namespace:{}'.format(ns)]
            namespace_tags.extend(self._tags)
            val = data.pop(0).split(',')[1]
            self._send(NAMESPACE_TPS_METRIC_TYPE, key, val, namespace_tags)

    def _send(self, metric_type, key, val, tags):
        if re.match('^{(.+)}-(.*)hist-track', key):
            self.log.debug("Histogram config skipped: %s=%s", key, str(val))
            return  # skip histogram configuration

        if key == 'cluster_key':
            val = str(int(val, 16))

        if val.isdigit():
            if key in self.init_config.get('mappings', []):
                datatype = 'rate'
            else:
                datatype = 'gauge'
        elif val.lower() in ('true', 'on', 'enable', 'enabled'):  # boolean : true
            val = 1
            datatype = 'gauge'
        elif val.lower() in ('false', 'off', 'disable', 'disabled'):  # boolean : false
            val = 0
            datatype = 'gauge'
        else:
            try:
                float(val)
                datatype = 'gauge'
            except ValueError:
                datatype = 'event'

        if datatype == 'gauge':
            self.gauge(self._make_key(metric_type, key), val, tags=tags)
        elif datatype == 'rate':
            self.rate(self._make_key(metric_type, key), val, tags=tags)
        else:
            return  # Non numeric/boolean metric, discard

    @staticmethod
    def _make_key(event_type, n):
        return '%s.%s' % (event_type, n.replace('-', '_'))
