# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector, collection_interval_checker
from datadog_checks.mongo.common import MongosDeployment
from datadog_checks.mongo.metrics import SHARDED_DATA_DISTRIBUTION_METRICS


class ShardedDataDistributionStatsCollector(MongoCollector):
    """
    Collects data distribution statistics for sharded collections.
    """

    def __init__(self, check, tags):
        super(ShardedDataDistributionStatsCollector, self).__init__(check, tags)
        self._collection_interval = check._config.metrics_collection_interval['sharded_data_distribution']

    def compatible_with(self, deployment):
        # Can only be run on mongos nodes.
        return isinstance(deployment, MongosDeployment)

    @collection_interval_checker
    def collect(self, api):
        for distribution in api.sharded_data_distribution_stats():
            ns = distribution['ns']
            db, collection = ns.split('.', 1)
            for shard in distribution.get('shards', []):
                shard_name = shard.pop('shardName')
                additional_tags = ["db:%s" % db, "collection:%s" % collection, "shard:%s" % shard_name]
                self._submit_payload(shard, additional_tags, SHARDED_DATA_DISTRIBUTION_METRICS)
