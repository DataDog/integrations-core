from datadog_checks.mongo.collectors.base import MongoCollector


class CurrentOpCollector(MongoCollector):
    """Collects the mongodb.fsyncLock metric by checking the output of the 'currentOp' command.
    Useful to know if the selected database is currently write-locked."""

    def collect(self, client):
        db = client[self.db_name]
        ops = db.current_op()
        payload = {'fsyncLocked': 1 if ops.get('fsyncLock') else 0}
        self._submit_payload(payload)
