# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


class DbStatCollector(MongoCollector):
    """Collects database statistics using the 'dbstats' mongo command. This collector can be instantiated multiple
    times, for each database to monitor.
    Metrics are tagged with the database name so they don't overlap with each other.
    """

    def __init__(self, check, db_name, tags):
        super(DbStatCollector, self).__init__(check, tags)
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can theoretically be run on any node as long as it contains data.
        # i.e Arbiters are ruled out
        if self.db_name == 'local':
            if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
                return False
            if isinstance(deployment, MongosDeployment):
                return False
            return True
        else:
            return deployment.is_principal()

    def collect(self, api):
        db = api[self.db_name]
        # Submit the metric
        additional_tags = [
            u"cluster:db:{0}".format(self.db_name),  # FIXME: 8.x, was kept for backward compatibility
            u"db:{0}".format(self.db_name),
        ]
        stats = {'stats': db.command('dbstats')}
        return self._submit_payload(stats, additional_tags)
