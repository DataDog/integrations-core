from six import iteritems

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.metrics import TOP_METRICS


class TopCollector(MongoCollector):
    def __init__(self, check, tags):
        super(TopCollector, self).__init__(check, "admin", tags)

    # mongod only
    def collect(self, client):
        dbtop = client[self.db_name].command('top')
        for ns, ns_metrics in iteritems(dbtop['totals']):
            if "." not in ns:
                continue

            # configure tags for db name and collection name
            dbname, collname = ns.split(".", 1)
            additional_tags = ["db:%s" % dbname, "collection:%s" % collname]

            self._submit_payload(ns_metrics, additional_tags, TOP_METRICS, prefix="usage")
