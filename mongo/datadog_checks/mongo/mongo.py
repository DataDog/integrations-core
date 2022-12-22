# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy

from packaging.version import Version

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.mongo.api import MongoApi
from datadog_checks.mongo.collectors import (
    CollStatsCollector,
    CustomQueriesCollector,
    DbStatCollector,
    FsyncLockCollector,
    IndexStatsCollector,
    ReplicaCollector,
    ReplicationOpLogCollector,
    ServerStatusCollector,
    TopCollector,
)
from datadog_checks.mongo.collectors.conn_pool_stats import ConnPoolStatsCollector
from datadog_checks.mongo.collectors.jumbo_stats import JumboStatsCollector
from datadog_checks.mongo.collectors.session_stats import SessionStatsCollector
from datadog_checks.mongo.common import SERVICE_CHECK_NAME, MongosDeployment, ReplicaSetDeployment
from datadog_checks.mongo.config import MongoConfig

from . import metrics

long = int


class MongoDb(AgentCheck):
    """
    MongoDB agent check.

    # Metrics
    Metric available for collection are listed by topic as `MongoDb` class variables.

    Various metric topics are collected by default. Others require the
    corresponding option enabled in the check configuration file.

    ## Format
    Metrics are listed with the following format:
        ```
        metric_name -> metric_type
        ```
        or
        ```
        metric_name -> (metric_type, alias)*
        ```

    * `alias` parameter is optional, if unspecified, MongoDB metrics are reported
       with their original metric names.

    # Service checks
    Available service checks:
    * `mongodb.can_connect`
      Connectivity health to the instance.
    * `mongodb.replica_set_member_state`
      Disposition of the member replica set state.
    """

    def __init__(self, name, init_config, instances=None):
        super(MongoDb, self).__init__(name, init_config, instances)
        self._config = MongoConfig(self.instance, self.log)

        if 'server' in self.instance:
            self.warning('Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.')

        # Get the list of metrics to collect
        self.metrics_to_collect = self._build_metric_list_to_collect()
        self.collectors = []
        self.last_states_by_server = {}

        self._api_client = None
        self._mongo_version = None

    @property
    def api_client(self):
        return self._api_client

    def refresh_collectors(self, deployment_type, all_dbs, tags):
        collect_tcmalloc_metrics = 'tcmalloc' in self._config.additional_metrics
        potential_collectors = [
            ConnPoolStatsCollector(self, tags),
            ReplicationOpLogCollector(self, tags),
            FsyncLockCollector(self, tags),
            CollStatsCollector(self, self._config.db_name, tags, coll_names=self._config.coll_names),
            ServerStatusCollector(self, self._config.db_name, tags, tcmalloc=collect_tcmalloc_metrics),
        ]
        if self._config.replica_check:
            potential_collectors.append(ReplicaCollector(self, tags))
        if 'jumbo_chunks' in self._config.additional_metrics:
            potential_collectors.append(JumboStatsCollector(self, tags))
        if 'top' in self._config.additional_metrics:
            potential_collectors.append(TopCollector(self, tags))
        if Version(self._mongo_version) >= Version("3.6"):
            potential_collectors.append(SessionStatsCollector(self, tags))
        if self._config.collections_indexes_stats:
            if Version(self._mongo_version) >= Version("3.2"):
                potential_collectors.append(
                    IndexStatsCollector(self, self._config.db_name, tags, self._config.coll_names)
                )
            else:
                self.log.debug(
                    "'collections_indexes_stats' is only available starting from mongo 3.2: "
                    "your mongo version is %s",
                    self._mongo_version,
                )
        for db_name in all_dbs:
            potential_collectors.append(DbStatCollector(self, db_name, tags))

        # Custom queries are always collected except if the node is a secondary or an arbiter in a replica set.
        # It is possible to collect custom queries from secondary nodes as well but this has to be explicitly
        # stated in the configuration of the query.
        is_secondary = isinstance(deployment_type, ReplicaSetDeployment) and deployment_type.is_secondary
        queries = self._config.custom_queries
        if is_secondary:
            # On a secondary node, only collect the custom queries that define the 'run_on_secondary' parameter.
            queries = [q for q in self._config.custom_queries if is_affirmative(q.get('run_on_secondary', False))]
            missing_queries = len(self._config.custom_queries) - len(queries)
            if missing_queries:
                self.log.debug(
                    "{} custom queries defined in the configuration won't be run because the mongod node is a "
                    "secondary and the queries don't specify 'run_on_secondary: true' in the configuration. "
                    "Custom queries are only run on mongos, primaries, or standalone by default to prevent "
                    "duplicated information."
                )

        potential_collectors.append(CustomQueriesCollector(self, self._config.db_name, tags, queries))

        self.collectors = [coll for coll in potential_collectors if coll.compatible_with(deployment_type)]

    def _build_metric_list_to_collect(self):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Default metrics
        for default_metrics in metrics.DEFAULT_METRICS.values():
            metrics_to_collect.update(default_metrics)

        # Additional metrics metrics
        for option in self._config.additional_metrics:
            if option not in metrics.AVAILABLE_METRICS:
                if option in metrics.DEFAULT_METRICS:
                    self.log.warning(
                        u"`%s` option is deprecated. The corresponding metrics are collected by default.", option
                    )
                else:
                    self.log.warning(
                        u"Failed to extend the list of metrics to collect: unrecognized `%s` option", option
                    )
                continue
            additional_metrics = metrics.AVAILABLE_METRICS[option]
            self.log.debug(u"Adding `%s` corresponding metrics to the list of metrics to collect.", option)
            metrics_to_collect.update(additional_metrics)

        return metrics_to_collect

    def _refresh_replica_role(self):
        if self._api_client and (
            self._api_client.deployment_type is None
            or isinstance(self._api_client.deployment_type, ReplicaSetDeployment)
        ):
            self.log.debug("Refreshing deployment type")
            self._api_client.deployment_type = self._api_client.get_deployment_type()

    def check(self, _):
        if self._connect():
            self._check()

    def _connect(self) -> bool:
        if self._api_client is None:
            try:
                self._api_client = MongoApi(self._config, self.log)
                self.log.debug("Connecting to '%s'", self._config.hosts)
                self._api_client.connect()
                self.log.debug("Connected!")
                self._mongo_version = self.api_client.server_info().get('version', '0.0')
                self.set_metadata('version', self._mongo_version)
                self.log.debug('version: %s', self._mongo_version)
            except Exception as e:
                self._api_client = None
                self.log.error('Exception: %s', e)
                self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags)
                return False
        self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags)
        return True

    def _check(self):
        self._refresh_replica_role()
        tags = deepcopy(self._config.metric_tags)
        deployment = self.api_client.deployment_type
        if isinstance(deployment, ReplicaSetDeployment):
            tags.extend(
                [
                    "replset_name:{}".format(deployment.replset_name),
                    "replset_state:{}".format(deployment.replset_state_name),
                ]
            )
            if deployment.use_shards:
                tags.append('sharding_cluster_role:{}'.format(deployment.cluster_role))
        elif isinstance(deployment, MongosDeployment):
            tags.append('sharding_cluster_role:mongos')

        dbnames = self._get_db_names(self.api_client, deployment, tags)
        self.refresh_collectors(deployment, dbnames, tags)
        for collector in self.collectors:
            try:
                collector.collect(self.api_client)
            except Exception:
                self.log.info(
                    "Unable to collect logs from collector %s. Some metrics will be missing.", collector, exc_info=True
                )

    def _get_db_names(self, api, deployment, tags):
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self.log.debug("Replicaset and arbiter deployment, no databases will be checked")
            dbnames = []
        elif isinstance(deployment, ReplicaSetDeployment) and deployment.replset_state == 3:
            self.log.debug("Replicaset is in recovering state, will skip reading database names")
            dbnames = []
        else:
            server_databases = api.list_database_names()
            self.gauge('mongodb.dbs', len(server_databases), tags=tags)
            if self._config.db_names is None:
                self.log.debug("No databases configured. Retrieving list of databases from the mongo server")
                dbnames = server_databases
            else:
                self.log.debug("Collecting only from the configured databases: %s", self._config.db_names)
                dbnames = []
                self.log.debug("Checking the configured databases that exist on the mongo server")
                for config_dbname in self._config.db_names:
                    if config_dbname in server_databases:
                        self.log.debug("'%s' database found on the mongo server", config_dbname)
                        dbnames.append(config_dbname)
                    else:
                        self.log.warning(
                            "'%s' database not found on the mongo server"
                            ", will not append to list of databases to check",
                            config_dbname,
                        )
        self.log.debug("List of databases to check: %s", dbnames)
        return dbnames
