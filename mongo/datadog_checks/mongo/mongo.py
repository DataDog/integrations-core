# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from copy import deepcopy
from distutils.version import LooseVersion

import pymongo
from six import PY3, itervalues

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

if PY3:
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
        self.config = MongoConfig(self.instance, self.log)

        if 'server' in self.instance:
            self.warning('Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.')

        # Get the list of metrics to collect
        self.metrics_to_collect = self._build_metric_list_to_collect()
        self.collectors = []
        self.last_states_by_server = {}

    @classmethod
    def get_library_versions(cls):
        return {'pymongo': pymongo.version}

    def refresh_collectors(self, deployment_type, mongo_version, all_dbs, tags):
        collect_tcmalloc_metrics = 'tcmalloc' in self.config.additional_metrics
        potential_collectors = [
            ConnPoolStatsCollector(self, tags),
            ReplicationOpLogCollector(self, tags),
            FsyncLockCollector(self, self.config.db_name, tags),
            CollStatsCollector(self, self.config.db_name, tags, coll_names=self.config.coll_names),
            ServerStatusCollector(self, self.config.db_name, tags, tcmalloc=collect_tcmalloc_metrics),
        ]
        if self.config.replica_check:
            potential_collectors.append(ReplicaCollector(self, tags))
        if 'jumbo_chunks' in self.config.additional_metrics:
            potential_collectors.append(JumboStatsCollector(self, tags))
        if 'top' in self.config.additional_metrics:
            potential_collectors.append(TopCollector(self, tags))
        if LooseVersion(mongo_version) >= LooseVersion("3.6"):
            potential_collectors.append(SessionStatsCollector(self, tags))
        if self.config.collections_indexes_stats:
            if LooseVersion(mongo_version) >= LooseVersion("3.2"):
                potential_collectors.append(
                    IndexStatsCollector(self, self.config.db_name, tags, self.config.coll_names)
                )
            else:
                self.log.debug(
                    "'collections_indexes_stats' is only available starting from mongo 3.2: "
                    "your mongo version is %s",
                    mongo_version,
                )
        for db_name in all_dbs:
            potential_collectors.append(DbStatCollector(self, db_name, tags))

        # Custom queries are always collected except if the node is a secondary or an arbiter in a replica set.
        # It is possible to collect custom queries from secondary nodes as well but this has to be explicitly
        # stated in the configuration of the query.
        is_secondary = isinstance(deployment_type, ReplicaSetDeployment) and deployment_type.is_secondary
        queries = self.config.custom_queries
        if is_secondary:
            # On a secondary node, only collect the custom queries that define the 'run_on_secondary' parameter.
            queries = [q for q in self.config.custom_queries if is_affirmative(q.get('run_on_secondary', False))]
            missing_queries = len(self.config.custom_queries) - len(queries)
            if missing_queries:
                self.log.debug(
                    "{} custom queries defined in the configuration won't be run because the mongod node is a "
                    "secondary and the queries don't specify 'run_on_secondary: true' in the configuration. "
                    "Custom queries are only run on mongos, primaries, or standalone by default to prevent "
                    "duplicated information."
                )

        potential_collectors.append(CustomQueriesCollector(self, self.config.db_name, tags, queries))

        self.collectors = [coll for coll in potential_collectors if coll.compatible_with(deployment_type)]

    def _build_metric_list_to_collect(self):
        """
        Build the metric list to collect based on the instance preferences.
        """
        metrics_to_collect = {}

        # Default metrics
        for default_metrics in itervalues(metrics.DEFAULT_METRICS):
            metrics_to_collect.update(default_metrics)

        # Additional metrics metrics
        for option in self.config.additional_metrics:
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

    def check(self, _):
        try:
            api = MongoApi(self.config, self.log)
            self.log.debug("Connected!")
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.service_check_tags)
            raise

        try:
            mongo_version = api.server_info().get('version', '0.0')
            self.set_metadata('version', mongo_version)
        except Exception:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.service_check_tags)
            self.log.exception("Error when collecting the version from the mongo server.")
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.config.service_check_tags)

        tags = deepcopy(self.config.metric_tags)
        deployment = api.deployment_type
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

        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            dbnames = []
        else:
            dbnames = api.list_database_names()
            self.gauge('mongodb.dbs', len(dbnames), tags=tags)

        self.refresh_collectors(api.deployment_type, mongo_version, dbnames, tags)
        for collector in self.collectors:
            try:
                collector.collect(api)
            except Exception:
                self.log.info(
                    "Unable to collect logs from collector %s. Some metrics will be missing.", collector, exc_info=True
                )
