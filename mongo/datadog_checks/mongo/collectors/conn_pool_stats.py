from datadog_checks.mongo.collectors.base import MongoCollector


class ConnPoolStatsCollector(MongoCollector):
    """Collect statistics from the connPoolStats command.
    connPoolStats only returns meaningful results for mongos instances and
    for mongod instances in sharded clusters.
    The output of connPoolStats varies depending on the deployment and the member against
    which you run connPoolStats among other factors.
    """

    def collect(self, client):
        db = client["admin"]
        stats = {'connection_pool': db.command('connPoolStats')}
        self._submit_payload(stats)
