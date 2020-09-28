from datadog_checks.mongo.collectors.base import MongoCollector


class ServerStatusCollector(MongoCollector):
    """The main collectors, simply performs the 'serverStatus' command and forwards metrics to Datadog."""

    def __init__(self, check, db_name, tags, tcmalloc=False):
        super(ServerStatusCollector, self).__init__(check, db_name, tags)
        self.collect_tcmalloc_metrics = tcmalloc

    def collect(self, client):
        db = client[self.db_name]
        # No need to check for `result['ok']`, already handled by pymongo
        payload = db.command('serverStatus', tcmalloc=self.collect_tcmalloc_metrics)

        # If these keys exist, remove them for now as they cannot be serialized.
        payload.get('backgroundFlushing', {}).pop('last_finished', None)
        payload.pop('localTime', None)

        self._submit_payload(payload)
