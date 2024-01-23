# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


class FsyncLockCollector(MongoCollector):
    """Collects the mongodb.fsyncLock metric by checking the output of the 'currentOp' command.
    Useful to know if the selected database is currently write-locked."""

    def __init__(self, check, tags):
        super(FsyncLockCollector, self).__init__(check, tags)

    def compatible_with(self, deployment):
        # Can be run on any mongod instance excepts arbiters.
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self.log.debug("FsyncLockCollector can only be run on mongod nodes, arbiter node detected.")
            return False
        if isinstance(deployment, MongosDeployment):
            self.log.debug("FsyncLockCollector can only be run on mongod nodes, mongos deployment detected.")
            return False
        return True

    def collect(self, api):
        db = api['admin']
        ops = db.command('currentOp')
        payload = {'fsyncLocked': 1 if ops.get('fsyncLock') else 0}
        self._submit_payload(payload)
