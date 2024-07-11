# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import json
import time
from copy import deepcopy
from functools import cached_property

from cachetools import TTLCache
from packaging.version import Version

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.mongo.__about__ import __version__
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
from datadog_checks.mongo.dbm.operation_metrics import MongoOperationMetrics
from datadog_checks.mongo.dbm.operation_samples import MongoOperationSamples
from datadog_checks.mongo.discovery import MongoDBDatabaseAutodiscovery

from . import metrics

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

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
        self._resolved_hostname = None

        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

        self.diagnosis.register(self._diagnose_tls)

        # DBM
        self._operation_samples = MongoOperationSamples(check=self)
        self._operation_metrics = MongoOperationMetrics(check=self)

        # Database autodiscovery
        self._database_autodiscovery = MongoDBDatabaseAutodiscovery(check=self)

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

        dbstats_tag_dbname = self._config.dbstats_tag_dbname
        for db_name in all_dbs:
            # DbStatCollector is always collected on all monitored databases (filtered by db_names config option)
            # For backward compatibility, we keep collecting from all monitored databases
            # regardless of the auto-discovery settings.
            potential_collectors.append(DbStatCollector(self, db_name, dbstats_tag_dbname, tags))

        monitored_dbs = all_dbs if self._database_autodiscovery.autodiscovery_enabled else [self._config.db_name]
        # When autodiscovery is enabled, we collect collstats and indexstats for all auto-discovered databases
        # Otherwise, we collect collstats and indexstats for the database specified in the configuration
        for db_name in monitored_dbs:
            # For backward compatibility, coll_names is ONLY applied when autodiscovery is not enabled
            # Otherwise, we collect collstats & indexstats for all auto-discovered databases and authorized collections
            coll_names = None if self._database_autodiscovery.autodiscovery_enabled else self._config.coll_names
            potential_collectors.append(CollStatsCollector(self, db_name, tags, coll_names=coll_names))
            if self._config.collections_indexes_stats:
                if self._mongo_version_parsed >= Version("3.2"):
                    potential_collectors.append(IndexStatsCollector(self, db_name, tags, coll_names=coll_names))
                else:
                    self.log.debug(
                        "'collections_indexes_stats' is only available starting from mongo 3.2: "
                        "your mongo version is %s",
                        self._mongo_version,
                    )

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

    def _refresh_deployment(self):
        if (
            self.api_client.deployment_type is None  # First run
            or isinstance(
                self.api_client.deployment_type, ReplicaSetDeployment
            )  # Replica set members and state can change
            or isinstance(self.api_client.deployment_type, MongosDeployment)  # Mongos shard map can change
        ):
            deployment_type_before = self.api_client.deployment_type
            self.log.debug("Refreshing deployment type")
            self.api_client.refresh_deployment_type()
            if self.api_client.deployment_type != deployment_type_before:
                self.log.debug(
                    "Deployment type has changed from %s to %s", deployment_type_before, self.api_client.deployment_type
                )
                # database_instance metadata is tied to the deployment type
                # so we need to reset it when the deployment type changes
                # this way new metadata will be emitted
                self._database_instance_emitted.clear()

    @property
    def internal_resource_tags(self):
        '''
        Return the internal resource tags for the database instance.
        '''
        if not self._resolved_hostname:
            return []
        return [f"dd.internal.resource:database_instance:{self._resolved_hostname}"]

    def _get_tags(self, include_deployment_tags=False, include_internal_resource_tags=False):
        tags = deepcopy(self._config.metric_tags)
        if include_deployment_tags:
            tags.extend(self.api_client.deployment_type.deployment_tags)
        if include_internal_resource_tags:
            tags.extend(self.internal_resource_tags)
        return tags

    def check(self, _):
        try:
            self._refresh_metadata()
            self._refresh_deployment()
            self._collect_metrics()

            # DBM
            if self._config.dbm_enabled:
                self._send_database_instance_metadata()
                self._operation_samples.run_job_loop(tags=self._get_tags(include_deployment_tags=True))
                self._operation_metrics.run_job_loop(tags=self._get_tags(include_deployment_tags=True))
        except CRITICAL_FAILURE as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags)
            self._unset_metadata()
            raise e  # Let exception bubble up to global handler and show full error in the logs.
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags)

    def _refresh_metadata(self):
        if self._mongo_version is None:
            self.log.debug('No mongo_version metadata present, refreshing it.')
            self._mongo_version = self.api_client.server_info().get('version', '0.0')
            self._mongo_version_parsed = Version(self._mongo_version.split("-")[0])
            self.set_metadata('version', self._mongo_version)
            self.log.debug('version: %s', self._mongo_version)
        if self._resolved_hostname is None:
            self._resolved_hostname = self._config.reported_database_hostname or self.api_client.hostname
            self.set_metadata('resolved_hostname', self._resolved_hostname)
            self.log.debug('resolved_hostname: %s', self._resolved_hostname)

    def _unset_metadata(self):
        self.log.debug('Due to connection failure we will need to reset the metadata.')
        self._mongo_version = None
        self._resolved_hostname = None

    def _collect_metrics(self):
        deployment = self.api_client.deployment_type
        tags = self._get_tags(include_deployment_tags=True, include_internal_resource_tags=True)

        dbnames = self._get_db_names(tags)
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

    def _get_db_names(self, tags):
        dbnames, database_count = self._database_autodiscovery.get_databases_and_count()
        if database_count:
            self.gauge('mongodb.dbs', database_count, tags=tags)
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

    def _send_database_instance_metadata(self):
        deployment = self.api_client.deployment_type
        if self._resolved_hostname not in self._database_instance_emitted:
            # DO NOT emit with internal resource tags, as the metadata event is used to CREATE the databse instance
            tags = self._get_tags(include_deployment_tags=True, include_internal_resource_tags=False)
            mongodb_instance_metadata = {"cluster_name": self._config.cluster_name} | deployment.instance_metadata
            database_instance = {
                "host": self._resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "mongodb",
                "kind": "mongodb_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': self._mongo_version,
                'integration_version': __version__,
                "tags": tags,
                "timestamp": time.time() * 1000,
                "metadata": {
                    "dbm": self._config.dbm_enabled,
                    "connection_host": self._config.clean_server_name,
                    "instance_metadata": {k: v for k, v in mongodb_instance_metadata.items() if v is not None},
                },
            }
            self._database_instance_emitted[self._resolved_hostname] = database_instance
            self.log.debug("Emitting database instance  metadata, %s", database_instance)
            self.database_monitoring_metadata(json.dumps(database_instance, default=default_json_event_encoding))

    def cancel(self):
        if self._config.dbm_enabled:
            self._operation_samples.cancel()
            self._operation_metrics.cancel()
