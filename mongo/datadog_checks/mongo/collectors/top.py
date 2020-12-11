from six import iteritems

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment
from datadog_checks.mongo.metrics import TOP_METRICS


class TopCollector(MongoCollector):
    """Additional metrics coming from the 'top' command. Needs to be explicitly defined in the 'additional_metrics'
    section of the configuration.
    Can only be fetched from a mongod service."""

    def compatible_with(self, deployment):
        # Can only be run on mongod nodes, and not on arbiters.
        if isinstance(deployment, MongosDeployment):
            return False
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            return False
        return True

    def collect(self, client):
        dbtop = client["admin"].command('top')
        for ns, ns_metrics in iteritems(dbtop['totals']):
            if "." not in ns:
                continue

            # configure tags for db name and collection name
            dbname, collname = ns.split(".", 1)
            additional_tags = ["db:%s" % dbname, "collection:%s" % collname]

            self._submit_payload(ns_metrics, additional_tags, TOP_METRICS, prefix="usage")
