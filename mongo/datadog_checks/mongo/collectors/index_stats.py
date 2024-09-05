# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pymongo.errors import OperationFailure

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.metrics import INDEX_METRICS


class IndexStatsCollector(MongoCollector):
    """Collect statistics on collection indexes by running the indexStats command."""

    def __init__(self, check, db_name, tags, coll_names=None):
        super(IndexStatsCollector, self).__init__(check, tags)
        self.coll_names = coll_names
        self.db_name = db_name
        self.max_collections_per_database = check._config.database_autodiscovery_config['max_collections_per_database']

    def compatible_with(self, deployment):
        # Can only be run once per cluster.
        return deployment.is_principal()

    def _get_collections(self, api):
        if self.coll_names:
            return self.coll_names
        return api.list_authorized_collections(self.db_name, limit=self.max_collections_per_database)

    def collect(self, api):
        coll_names = self._get_collections(api)
        for coll_name in coll_names:
            try:
                for stats in api.index_stats(self.db_name, coll_name):
                    additional_tags = [
                        "name:{0}".format(stats.get('name', 'unknown')),
                        "collection:{0}".format(coll_name),
                        "db:{0}".format(self.db_name),
                    ]
                    if stats.get('shard'):
                        additional_tags.append("shard:{0}".format(stats['shard']))
                    self._submit_payload({"indexes": stats}, additional_tags, INDEX_METRICS, "collection")
            except OperationFailure as e:
                # Atlas restricts $indexStats on system collections
                if e.code == 13:
                    self.log.warning("Unauthorized to run $indexStats on collection %s.%s", self.db_name, coll_name)
                else:
                    self.log.warning(
                        "Could not collect index stats for collection %s.%s: %s", self.db_name, coll_name, e.details
                    )
            except Exception as e:
                self.log.error(
                    "Unexpected error when fetch indexes stats for collection %s.%s: %s", self.db_name, coll_name, e
                )
                raise e
