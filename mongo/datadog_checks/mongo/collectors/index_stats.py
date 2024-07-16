# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pymongo.errors import OperationFailure

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

    def _get_collections(self, api):
        if self.coll_names:
            return self.coll_names
        return api.list_authorized_collections(self.db_name)

    def collect(self, api):
        coll_names = self._get_collections(api)
        for coll_name in coll_names:
            try:
                for stats in api.index_stats(self.db_name, coll_name):
                    idx_tags = self.base_tags + [
                        "name:{0}".format(stats.get('name', 'unknown')),
                        "collection:{0}".format(coll_name),
                        "db:{0}".format(self.db_name),
                    ]
                    val = int(stats.get('accesses', {}).get('ops', 0))
                    self.gauge('mongodb.collection.indexes.accesses.ops', val, idx_tags)
            except OperationFailure as e:
                # Atlas restricts $indexStats on system collections
                self.log.warning("Could not collect index stats for collection %s: %s", coll_name, e)
            except Exception as e:
                self.log.error("Could not fetch indexes stats for collection %s: %s", coll_name, e)
                raise e
