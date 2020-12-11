from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


class FsyncLockCollector(MongoCollector):
    """Collects the mongodb.fsyncLock metric by checking the output of the 'currentOp' command.
    Useful to know if the selected database is currently write-locked."""

    def __init__(self, check, db_name, tags):
        super(FsyncLockCollector, self).__init__(check, tags)
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can be run on any mongod instance excepts arbiters.
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            return False
        if isinstance(deployment, MongosDeployment):
            return False
        return True

    def collect(self, client):
        db = client[self.db_name]
        ops = db.current_op()
        payload = {'fsyncLocked': 1 if ops.get('fsyncLock') else 0}
        self._submit_payload(payload)
