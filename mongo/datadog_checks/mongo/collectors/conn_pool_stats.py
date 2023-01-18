# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import ReplicaSetDeployment


class ConnPoolStatsCollector(MongoCollector):
    """Collect statistics from the connPoolStats command.
    connPoolStats only returns meaningful results for mongos instances and
    for mongod instances in sharded clusters.
    The output of connPoolStats varies depending on the deployment and the member against
    which you run connPoolStats among other factors.
    """

    def compatible_with(self, deployment):
        # Can only be run on:
        #  - a mongod node in a sharded cluster, as long as it's not an arbiter
        #  - a mongos
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            return False
        return deployment.use_shards

    def collect(self, api):
        db = api["admin"]
        stats = {'connection_pool': db.command('connPoolStats')}
        self._submit_payload(stats)
