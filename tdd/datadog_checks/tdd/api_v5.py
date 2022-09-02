from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from datadog_checks.base import is_affirmative
from datadog_checks.tdd.api import Api


class Apiv5(Api):
    def __init__(self, check, instance):
        super(Apiv5, self).__init__(check, instance)
        options = {
            'host': self._instance.get('hosts', 'localhost:27017'),
            'serverSelectionTimeoutMS': self._instance.get('timeout', 5) * 1000,
            'directConnection': True,
        }
        self._mongo_client = MongoClient(**options)

    def report_service_check(self):
        service_check = self._check.CRITICAL
        try:
            # The ping command is cheap and does not require auth.
            ping_output = self._mongo_client['admin'].command('ping')
            self._log.debug('ping_output: %s', ping_output)
            if ping_output['ok'] == 1:
                service_check = self._check.OK
            else:
                self._log.error('ping returned no valid value')
        except ConnectionFailure as e:
            self._log.error('Exception: %s', e)
        self._check.service_check("can_connect", service_check)
        return service_check

    def report_metadata(self):
        mongo_version = self._mongo_client.server_info().get('version', '0.0.0')
        self._check.set_metadata('version', mongo_version)
        self._log.debug('mongo_version: %s', mongo_version)

    def report_metrics(self):
        self._report_server_status_metrics()
        self._report_coll_stats_metrics()
        self._report_collections_indexes_stats_metrics()
        self._report_top_metrics()

    def _report_server_status_metrics(self):
        tcmalloc = 'tcmalloc' in self._instance.get('additional_metrics', [])
        server_status_output = self._mongo_client['admin'].command('serverStatus', tcmalloc=tcmalloc)
        self._log.debug('server_status_output: %s', server_status_output)
        self._report_json(server_status_output)

    def _report_coll_stats_metrics(self):
        collstats_output = {'collection': self._mongo_client['admin'].command('collStats', 'foo')}
        self._log.debug('collstats_output: %s', collstats_output)
        self._report_json(collstats_output)
        # Submit the indexSizes metrics manually
        index_sizes = collstats_output['collection'].get('indexSizes', {})
        metric_name_alias = self._normalize("collection.indexSizes", self._check.gauge)
        for name, value in index_sizes.items():
            self._log.debug('index %s: %s', name, value)
            self._check.gauge(metric_name_alias, value)

    def _report_collections_indexes_stats_metrics(self):
        if is_affirmative(self._instance.get('collections_indexes_stats')):
            indexstats_output = {
                'collection': {'indexes': self._mongo_client['admin'].aggregate([{"$indexStats": {}}])}
            }
            self._log.debug('indexstats_output: %s', indexstats_output)
            self._report_json(indexstats_output)

    def _report_top_metrics(self):
        if 'top' in self._instance.get('additional_metrics', []):
            top_output = {'usage': self._mongo_client['admin'].command('top')}
            self._log.debug('top_output: %s', top_output)
            for ns, ns_metrics in top_output['usage']['totals'].items():
                if "." not in ns:
                    continue
                self._log.debug('ns: %s, ns_metrics: %s', ns, ns_metrics)
                self._report_json(ns_metrics, 'usage.')
