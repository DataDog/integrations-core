# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from distutils.version import LooseVersion

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.tdd.metrics import CASE_SENSITIVE_METRIC_NAME_SUFFIXES, METRICS


class TddCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'tdd'

    def __init__(self, name, init_config, instances):
        super(TddCheck, self).__init__(name, init_config, instances)
        options = {
            'host': self.instance.get('hosts', 'localhost:27017'),
            'serverSelectionTimeoutMS': self.instance.get('timeout', 5) * 1000,
        }
        self._mongo_client = MongoClient(**options)
        self._mongo_version = None

    def check(self, _):
        service_check = self._report_service_check()
        if service_check == AgentCheck.OK:
            self.log.debug('Connected')
            self._report_metadata()
            self._report_metrics()

    def _report_service_check(self):
        service_check = AgentCheck.CRITICAL
        try:
            # The ping command is cheap and does not require auth.
            ping_output = self._mongo_client['admin'].command('ping')
            self.log.debug('ping_output: %s', ping_output)
            if ping_output['ok'] == 1:
                service_check = AgentCheck.OK
            else:
                self.log.error('ping returned no valid value')
        except ConnectionFailure as e:
            self.log.error('Exception: %s', e)
        self.service_check("can_connect", service_check)
        return service_check

    def _report_metadata(self):
        self._mongo_version = self._mongo_client.server_info().get('version', '0.0.0')
        self.set_metadata('version', self._mongo_version)
        self.log.debug('mongo_version: %s', self._mongo_version)

    def _report_metrics(self):
        self._report_server_status_metrics()
        self._report_coll_stats_metrics()
        self._report_collections_indexes_stats_metrics()
        self._report_top_metrics()

    def _report_server_status_metrics(self):
        tcmalloc = 'tcmalloc' in self.instance.get('additional_metrics', [])
        server_status_output = self._mongo_client['admin'].command('serverStatus', tcmalloc=tcmalloc)
        self.log.debug('server_status_output: %s', server_status_output)
        self._report_json(server_status_output)

    def _report_coll_stats_metrics(self):
        collstats_output = {'collection': self._mongo_client['admin'].command('collStats', 'foo')}
        self.log.debug('collstats_output: %s', collstats_output)
        self._report_json(collstats_output)
        # Submit the indexSizes metrics manually
        index_sizes = collstats_output['collection'].get('indexSizes', {})
        metric_name_alias = self._normalize("collection.indexSizes", AgentCheck.gauge)
        for name, value in index_sizes.items():
            self.log.debug('index %s: %s', name, value)
            self.gauge(metric_name_alias, value)

    def _report_collections_indexes_stats_metrics(self):
        if is_affirmative(self.instance.get('collections_indexes_stats')):
            if LooseVersion(self._mongo_version) >= LooseVersion("3.2"):
                indexstats_output = {
                    'collection': {'indexes': self._mongo_client['admin'].aggregate([{"$indexStats": {}}])}
                }
                self.log.debug('indexstats_output: %s', indexstats_output)
                self._report_json(indexstats_output)
            else:
                self.log.warning(
                    "'collections_indexes_stats' is only available starting from mongo 3.2, your mongo version is %s",
                    self._mongo_version,
                )

    def _report_top_metrics(self):
        if 'top' in self.instance.get('additional_metrics', []):
            top_output = {'usage': self._mongo_client['admin'].command('top')}
            self.log.debug('top_output: %s', top_output)
            for ns, ns_metrics in top_output['usage']['totals'].items():
                if "." not in ns:
                    continue
                self.log.debug('ns: %s, ns_metrics: %s', ns, ns_metrics)
                self._report_json(ns_metrics, 'usage.')

    def _report_json(self, json, prefix=None):
        for metric_name in METRICS:
            value = json
            try:
                for c in metric_name.split("."):
                    value = value[c]
            except KeyError:
                continue
            submit_method = METRICS[metric_name][0] if isinstance(METRICS[metric_name], tuple) else METRICS[metric_name]
            metric_name_alias = METRICS[metric_name][1] if isinstance(METRICS[metric_name], tuple) else metric_name
            metric_name_alias = self._normalize(metric_name_alias, submit_method, prefix)
            self.log.debug('%s: %s [alias: %s, method: %s]', metric_name, value, metric_name_alias, submit_method)
            submit_method(self, metric_name_alias, value)

    def _normalize(self, metric_name, submit_method, prefix=None):
        """Replace case-sensitive metric name characters, normalize the metric name,
        prefix and suffix according to its type.
        """
        metric_prefix = "" if not prefix else prefix
        metric_suffix = "ps" if submit_method == AgentCheck.rate else ""

        # Replace case-sensitive metric name characters
        for pattern, repl in CASE_SENSITIVE_METRIC_NAME_SUFFIXES.items():
            metric_name = re.compile(pattern).sub(repl, metric_name)

        # Normalize, and wrap
        return u"{metric_prefix}{normalized_metric_name}{metric_suffix}".format(
            normalized_metric_name=self.normalize(metric_name.lower()),
            metric_prefix=metric_prefix,
            metric_suffix=metric_suffix,
        )
