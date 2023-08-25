# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector


class IndexStatsCollector(MongoCollector):
    """Collect statistics on collection indexes by running the indexStats command."""

    def __init__(self, check, db_name, tags, coll_names=None):
        super(IndexStatsCollector, self).__init__(check, tags)
        self.coll_names = coll_names
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can only be run once per cluster.
        return deployment.is_principal()

    def collect(self, api):
        db = api[self.db_name]
        for coll_name in self.coll_names:
            try:
                for stats in db[coll_name].aggregate([{"$indexStats": {}}], cursor={}):
                    idx_tags = self.base_tags + [
                        "name:{0}".format(stats.get('name', 'unknown')),
                        "collection:{0}".format(coll_name),
                    ]
                    val = int(stats.get('accesses', {}).get('ops', 0))
                    self.gauge('mongodb.collection.indexes.accesses.ops', val, idx_tags)
            except Exception as e:
                self.log.error("Could not fetch indexes stats for collection %s: %s", coll_name, e)
                raise e
