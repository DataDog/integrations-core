# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck
from datadog_checks.mongo.collectors.base import MongoCollector, collection_interval_checker
from datadog_checks.mongo.common import MongosDeployment


class SessionStatsCollector(MongoCollector):
    """Gets the count of current sessions stored in the system.sessions config database.
    The system.sessions collection is sharded so it's only collected from mongos."""

    def __init__(self, check, tags):
        super(SessionStatsCollector, self).__init__(check, tags)
        self._collection_interval = check._config.metrics_collection_interval['session_stats']

    def compatible_with(self, deployment):
        # Can only be run on mongos nodes.
        return isinstance(deployment, MongosDeployment)

    @collection_interval_checker
    def collect(self, api):
        config_db = api["config"]
        try:
            # 3.6+ only
            sessions_count = next(
                config_db['system.sessions'].aggregate([{"$listSessions": {"allUsers": True}}, {"$count": "total"}])
            )['total']
        except Exception as e:
            self.log.info('Unable to fetch system.session statistics.')
            raise e
        metric_name = self._normalize("sessions.count", AgentCheck.gauge)
        self.check.gauge(metric_name, sessions_count, tags=self.base_tags)
