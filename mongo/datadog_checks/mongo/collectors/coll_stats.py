from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.metrics import COLLECTION_METRICS


class CollStatsCollector(MongoCollector):
    def __init__(self, check, db_name, tags, coll_names=None):
        super(CollStatsCollector, self).__init__(check, db_name, tags)
        self.coll_names = coll_names

    def collect(self, client):
        # Ensure that you're on the right db
        db = client[self.db_name]
        # loop through the collections
        for coll_name in self.coll_names:
            # grab the stats from the collection
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
