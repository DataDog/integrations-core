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
            return False
        if isinstance(deployment, MongosDeployment):
            return False
        return True

    def collect(self, api):
        db = api['admin']
        ops = db.aggregate([{"$currentOp": {}}])
        for op in ops:
            payload = {'fsyncLocked': 1 if op.get('fsyncLock') else 0}
            self._submit_payload(payload)
