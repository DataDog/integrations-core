# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


class DbStatCollector(MongoCollector):
    """Collects database statistics using the 'dbstats' mongo command. This collector can be instantiated multiple
    times, for each database to monitor.
    Metrics are tagged with the database name so they don't overlap with each other.
    You can choose to exclude the database name as a tag using the parameter 'dbstats_tag_dbname'.
    """

    def __init__(self, check, db_name, dbstats_tag_dbname, tags):
        super(DbStatCollector, self).__init__(check, tags)
        self.db_name = db_name
        self.dbstats_tag_dbname = dbstats_tag_dbname

    def compatible_with(self, deployment):
        # Can theoretically be run on any node as long as it contains data.
        # i.e Arbiters are ruled out
        if self.db_name == 'local':
            if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
                self.log.debug("DbStatCollector can only be run on mongod nodes, arbiter node detected.")
                return False
            if isinstance(deployment, MongosDeployment):
                self.log.debug("DbStatCollector can only be run on mongod nodes, mongos deployment detected.")
                return False
            return True
        else:
            return deployment.is_principal()

    def collect(self, api):
        db = api[self.db_name]
        # Submit the metric
        # Check if parameter dbstats_tag_dbname is true to include dbname as a tag
        if self.dbstats_tag_dbname:
            additional_tags = [
                u"cluster:db:{0}".format(self.db_name),  # FIXME: 8.x, was kept for backward compatibility
                u"db:{0}".format(self.db_name),
            ]
        else:
            additional_tags = None
        stats = {'stats': db.command('dbstats')}
        return self._submit_payload(stats, additional_tags)
