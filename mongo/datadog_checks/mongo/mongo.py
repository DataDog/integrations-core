# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy
from functools import cached_property

from packaging.version import Version

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.mongo.api import CRITICAL_FAILURE, MongoApi
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
    * `mongodb.can_connect`
      Connectivity health to the instance.
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

        self.diagnosis.register(self._diagnose_tls)

    @cached_property
    def api_client(self):
        # This needs to be a property for our unit test mocks to work.
        return MongoApi(self._config, self.log)

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
        assert self._mongo_version is not None, "No MongoDB version is set, make sure you refreshed the metadata."
        if self._mongo_version_parsed >= Version("3.6"):
            potential_collectors.append(SessionStatsCollector(self, tags))
        if self._config.collections_indexes_stats:
            if self._mongo_version_parsed >= Version("3.2"):
                potential_collectors.append(
                    IndexStatsCollector(self, self._config.db_name, tags, self._config.coll_names)
                )
            else:
                self.log.debug(
                    "'collections_indexes_stats' is only available starting from mongo 3.2: "
                    "your mongo version is %s",
                    self._mongo_version,
                )
        dbstats_tag_dbname = self._config.dbstats_tag_dbname
        for db_name in all_dbs:
            potential_collectors.append(DbStatCollector(self, db_name, dbstats_tag_dbname, tags))

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
        if self.api_client.deployment_type is None or isinstance(self.api_client.deployment_type, ReplicaSetDeployment):
            self.log.debug("Refreshing deployment type")
            self.api_client.refresh_deployment_type()

    def check(self, _):
        try:
            self._refresh_metadata()
            self._collect_metrics()
        except CRITICAL_FAILURE as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags)
            self._unset_metadata()
            raise e  # Let exception bubble up to global handler and show full error in the logs.
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags)

    def _refresh_metadata(self):
        if self._mongo_version is None:
            self.log.debug('No metadata present, refreshing it.')
            self._mongo_version = self.api_client.server_info().get('version', '0.0')
            self._mongo_version_parsed = Version(self._mongo_version.split("-")[0])
            self.set_metadata('version', self._mongo_version)
            self.log.debug('version: %s', self._mongo_version)

    def _unset_metadata(self):
        self.log.debug('Due to connection failure we will need to reset the metadata.')
        self._mongo_version = None

    def _collect_metrics(self):
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
            except CRITICAL_FAILURE as e:
                self.log.info(
                    "Unable to collect logs from collector %s. Some metrics will be missing.", collector, exc_info=True
                )
                raise e  # Critical failures must bubble up to trigger a CRITICAL service check.
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

    def _diagnose_tls(self):
        # Check TLS config. Specifically, we might want to check that if `tls` is
        # enabled (either explicitly or implicitly), the provided
        # tls_certificate_key_file and tls_ca_file actually exist on the file system.
        if "tls_certificate_key_file" in self.instance:
            self._diagnose_readable('tls', self.instance["tls_certificate_key_file"], "tls_certificate_key_file")
        if "tls_ca_file" in self.instance:
            self._diagnose_readable('tls', self.instance["tls_ca_file"], "tls_ca_file")

    def _diagnose_readable(self, name, path, option_name):
        try:
            open(path).close()
        except FileNotFoundError:
            self.diagnosis.fail(name, f"file `{path}` provided in the `{option_name}` option does not exist")
        except OSError as exc:
            self.diagnosis.fail(
                name,
                f"file `{path}` provided as the `{option_name}` option could not be opened: {exc.strerror}",
            )
        else:
            self.diagnosis.success(
                name,
                f"file `{path}` provided as the `{option_name}` exists and is readable",
            )
