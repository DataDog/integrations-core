# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.metrics import COLLECTION_METRICS


class CollStatsCollector(MongoCollector):
    """Collects metrics from the 'collstats' command.
    Note: Collecting those metrics requires that 'collection' is set in the 'additional_metrics' section of the config.
    Also, the collections to be monitored have to be explicitly listed in the config as well.
    Finally, it is currently not possible to monitor collections from multiple databases using a single check instance.
    The check will always use the main database name defined in the configuration (or 'admin' by default).
    """

    def __init__(self, check, db_name, tags, coll_names=None):
        super(CollStatsCollector, self).__init__(check, tags)
        self.coll_names = coll_names
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can only be run once per cluster.
        return deployment.is_principal()

    def collect(self, api):
        # Ensure that you're on the right db
        db = api[self.db_name]
        # Loop through the collections
        for coll_name in self.coll_names:
            # Grab the stats from the collection
            payload = {'collection': db.command("collstats", coll_name)}
            additional_tags = ["db:%s" % self.db_name, "collection:%s" % coll_name]
            self._submit_payload(payload, additional_tags, COLLECTION_METRICS)

            # Submit the indexSizes metrics manually
            index_sizes = payload['collection'].get('indexSizes', {})
            metric_name_alias = self._normalize("collection.indexSizes", AgentCheck.gauge)
            for idx, val in iteritems(index_sizes):
                # we tag the index
                idx_tags = self.base_tags + additional_tags + ["index:%s" % idx]
                self.gauge(metric_name_alias, val, tags=idx_tags)
