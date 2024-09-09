# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pymongo.errors import OperationFailure
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.metrics import COLLECTION_METRICS


class CollStatsCollector(MongoCollector):
    """Collects metrics from the 'collstats' command.
    Note: Collecting those metrics requires that 'collection' is set in the 'additional_metrics' section of the config.
    """

    def __init__(self, check, db_name, tags, coll_names=None):
        super(CollStatsCollector, self).__init__(check, tags)
        self.coll_names = coll_names
        self.db_name = db_name
        self.max_collections_per_database = check._config.database_autodiscovery_config['max_collections_per_database']
        self.coll_stats_pipeline_supported = True

    def compatible_with(self, deployment):
        # Can only be run once per cluster.
        return deployment.is_principal()

    def _get_collections(self, api):
        if self.coll_names:
            return self.coll_names
        return api.list_authorized_collections(self.db_name, limit=self.max_collections_per_database)

    def __calculate_oplatency_avg(self, latency_stats):
        """Calculate the average operation latency."""
        for latency in latency_stats.values():
            if latency['ops'] > 0:
                latency['latency_avg'] = round(latency.get('latency', 0) / latency['ops'], 1)
        return latency_stats

    def _get_collection_stats(self, api, coll_name):
        if not self.coll_stats_pipeline_supported:
            return [api.coll_stats_compatable(self.db_name, coll_name)]
        try:
            return api.coll_stats(self.db_name, coll_name)
        except OperationFailure as e:
            if e.code == 13:
                # Unauthorized to run $collStats, do not try use the compatible mode, raise the exception
                raise e
            # Failed to get collection stats using $collStats aggregation
            self.log.debug(
                "Failed not collect stats for collection %s with $collStats, fallback to collStats command",
                coll_name,
                e.details,
            )
            self.coll_stats_pipeline_supported = False
            return [api.coll_stats_compatable(self.db_name, coll_name)]

    def collect(self, api):
        coll_names = self._get_collections(api)
        for coll_name in coll_names:
            # Grab the stats from the collection
            try:
                collection_stats = self._get_collection_stats(api, coll_name)
            except OperationFailure as e:
                # Atlas restricts $collStats on system collections
                if e.code == 13:
                    self.log.warning("Unauthorized to run $collStats on collection %s.%s", self.db_name, coll_name)
                else:
                    self.log.warning(
                        "Could not collect stats for collection %s.%s: %s", self.db_name, coll_name, e.details
                    )
                continue
            except Exception as e:
                self.log.error("Unexpected error when fetch stats for collection %s.%s: %s", self.db_name, coll_name, e)
                continue

            for coll_stats in collection_stats:
                additional_tags = ["db:%s" % self.db_name, "collection:%s" % coll_name]
                if coll_stats.get('shard'):
                    # If the collection is sharded, add the shard tag
                    additional_tags.append("shard:%s" % coll_stats['shard'])
                # Submit the metrics
                if self.coll_stats_pipeline_supported:
                    storage_stats = coll_stats.get('storageStats', {})
                    latency_stats = coll_stats.get('latencyStats', {})
                    query_stats = coll_stats.get('queryExecStats', {})
                    latency_stats = self.__calculate_oplatency_avg(latency_stats)
                    payload = {'collection': {**storage_stats, **latency_stats, **query_stats}}
                    index_sizes = storage_stats.get('indexSizes', {})
                else:
                    payload = {'collection': coll_stats}
                    index_sizes = coll_stats.get('indexSizes', {})
                self._submit_payload(payload, additional_tags, COLLECTION_METRICS)

                # Submit the indexSizes metrics manually
                if index_sizes:
                    metric_name_alias = self._normalize("collection.indexSizes", AgentCheck.gauge)
                    for idx, val in iteritems(index_sizes):
                        # we tag the index
                        idx_tags = self.base_tags + additional_tags + ["index:%s" % idx]
                        self.gauge(metric_name_alias, val, tags=idx_tags)
