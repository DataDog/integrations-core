# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.mongo.common import ReplicaSetDeployment

DEFAULT_MAX_DATABASES = 100
DEFAULT_REFRESH_INTERVAL = 600


class MongoDBDatabaseAutodiscovery(Discovery):
    def __init__(self, check):
        self._autodiscovery_config = check._config.database_autodiscovery_config
        self.autodiscovery_enabled = self._autodiscovery_config.get("enabled", False)

        super(MongoDBDatabaseAutodiscovery, self).__init__(
            self._list_databases,
            include={db: 0 for db in self._autodiscovery_config.get("include", [".*"])},
            exclude=self._autodiscovery_config.get("exclude"),
            interval=self._autodiscovery_config.get('refresh_interval', DEFAULT_REFRESH_INTERVAL),
        )
        self._check = check
        self._log = self._check.log
        self._max_databases = self._autodiscovery_config.get("max_databases", DEFAULT_MAX_DATABASES)

        self.database_count = 0  # total number of databases on the server

    def _list_databases(self):
        deployment = self._check.deployment_type

        databases = []
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self._log.debug("Replicaset and arbiter deployment, no databases will be checked")
        elif isinstance(deployment, ReplicaSetDeployment) and deployment.replset_state == 3:
            self._log.debug("Replicaset is in recovering state, will skip reading database names")
        else:
            databases = self._check.api_client.list_database_names()
            self.database_count = len(databases)
        return databases

    @property
    def databases(self):
        '''
        The databases property returns a list of database names to monitor, capped at the max_databases limit.
        '''
        dbnames = [database[1] for database in self.get_items()]
        dbnames = dbnames[: self._max_databases]  # limit the number of databases to monitor
        return dbnames

    def get_databases_and_count(self):
        return self.databases, self.database_count
