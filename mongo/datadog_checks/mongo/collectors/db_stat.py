from datadog_checks.mongo.collectors.base import MongoCollector


class DbStatCollector(MongoCollector):
    """Collects database statistics using the 'dbstats' mongo command. This collector can be instantiated multiple
    times, for each database to monitor.
    Metrics are tagged with the database name so they don't overlap with each other.
    """

    def __init__(self, check, db_name, tags):
        super(DbStatCollector, self).__init__(check, tags)
        self.db_name = db_name

    def collect(self, client):
        db = client[self.db_name]
        # Submit the metric
        additional_tags = [
            u"cluster:db:{0}".format(self.db_name),  # FIXME: 8.x, was kept for backward compatibility
            u"db:{0}".format(self.db_name),
        ]
        stats = {'stats': db.command('dbstats')}
        return self._submit_payload(stats, additional_tags)
