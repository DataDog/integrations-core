from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.mongo.common import ReplicaSetDeployment

DEFAULT_MAX_DATABASES = 100
DEFAULT_REFRESH_INTERVAL = 600


class MongoDBDatabaseAutodiscovery(Discovery):
    def __init__(self, check):
        self._autodiscovery_config = check._config.database_autodiscovery_config
        self.autodiscovery_enabled = self._autodiscovery_config.get("enabled", False)

        super(MongoDBDatabaseAutodiscovery, self).__init__(
            self._get_databases,
            include={db: 0 for db in self._autodiscovery_config.get("include", [".*"])},
            exclude=self._autodiscovery_config.get("exclude"),
            interval=self._autodiscovery_config.get('refresh_interval', DEFAULT_REFRESH_INTERVAL),
        )
        self._check = check
        self._log = self._check.log
        self._max_databases = self._autodiscovery_config.get("max_databases", DEFAULT_MAX_DATABASES)

        self._server_databases = []  # discovered databases from the server before filtering

    def _get_databases(self):
        deployment = self._check.api_client.deployment_type

        databases = []
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self._log.debug("Replicaset and arbiter deployment, no databases will be checked")
        elif isinstance(deployment, ReplicaSetDeployment) and deployment.replset_state == 3:
            self._log.debug("Replicaset is in recovering state, will skip reading database names")
        else:
            databases = self._check.api_client.list_database_names()
            self._server_databases = databases
        return databases

    @property
    def databases(self):
        '''
        The databases property returns a tuple of two lists:
        1. dbnames: a list of database names to be monitored
        2. server_databases: a list of all databases discovered on the server
        '''
        dbnames = [database[1] for database in self.get_items()]
        dbnames = dbnames[: self._max_databases]
        return dbnames, self._server_databases
