# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.collectors import MongoCollector
from datadog_checks.mongo.common import MongosDeployment


class JumboStatsCollector(MongoCollector):
    """Sharded deployments of mongo partition the data into chunks.
    MongoDB automatically splits chunks based on the shard key when they exceed the maximum size
    or number of documents.
    Sometimes, chunks grow beyond their maximum size but cannot be split they are considered 'jumbo'."""

    def compatible_with(self, deployment):
        # Can only be run on mongos nodes.
        return isinstance(deployment, MongosDeployment)

    def collect(self, api):
        chunks = api['config']['chunks']
        total_chunks_count = chunks.count_documents({})
        jumbo_chunks_count = chunks.count_documents({'jumbo': True})

        total_chunks_metric_name = self._normalize("chunks.total", AgentCheck.gauge)
        jumbo_chunks_metric_name = self._normalize("chunks.jumbo", AgentCheck.gauge)
        self.check.gauge(total_chunks_metric_name, total_chunks_count, tags=self.base_tags)
        self.check.gauge(jumbo_chunks_metric_name, jumbo_chunks_count, tags=self.base_tags)
