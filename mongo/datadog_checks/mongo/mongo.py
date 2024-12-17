# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import json
import time
from copy import deepcopy

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
    HostInfoCollector,
    IndexStatsCollector,
    ProcessStatsCollector,
    ReplicaCollector,
    ReplicationOpLogCollector,
    ServerStatusCollector,
    ShardedDataDistributionStatsCollector,
    TopCollector,
)
from datadog_checks.mongo.collectors.conn_pool_stats import ConnPoolStatsCollector
from datadog_checks.mongo.collectors.jumbo_stats import JumboStatsCollector
from datadog_checks.mongo.collectors.session_stats import SessionStatsCollector
from datadog_checks.mongo.common import (
    SERVICE_CHECK_NAME,
    HostingType,
    MongosDeployment,
    ReplicaSetDeployment,
    StandaloneDeployment,
)
from datadog_checks.mongo.config import MongoConfig
from datadog_checks.mongo.dbm.operation_samples import MongoOperationSamples
from datadog_checks.mongo.dbm.schemas import MongoSchemas
from datadog_checks.mongo.dbm.slow_operations import MongoSlowOperations
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
        self._config = MongoConfig(self.instance, self.log, self.init_config)

        if 'server' in self.instance:
            self.warning('Option `server` is deprecated and will be removed in a future release. Use `hosts` instead.')

        # Get the list of metrics to collect
        self.metrics_to_collect = self._build_metric_list_to_collect()
        self.collectors = []
        self.last_states_by_server = {}
        self.metrics_last_collection_timestamp = {}

        self.deployment_type = None
        self._mongo_version = None
        self._mongo_modules = None
        self._resolved_hostname = None

        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )  # type: TTLCache

        self.diagnosis.register(self._diagnose_tls)

        # Database autodiscovery
        self._database_autodiscovery = MongoDBDatabaseAutodiscovery(check=self)

        # DBM
        self._operation_samples = MongoOperationSamples(check=self)
        self._slow_operations = MongoSlowOperations(check=self)
        self._schemas = MongoSchemas(check=self)

        self._api = None

    @property
    def api_client(self):
        if self._api is None:
            self._api = MongoApi(self._config, self.log)
        return self._api

    @api_client.setter
    def api_client(self, value):
        self._api = value

    def refresh_collectors(self, deployment_type, all_dbs, tags):
        collect_tcmalloc_metrics = 'tcmalloc' in self._config.additional_metrics
        potential_collectors = [
            ConnPoolStatsCollector(self, tags),
            ReplicationOpLogCollector(self, tags),
            FsyncLockCollector(self, tags),
            ServerStatusCollector(self, self._config.db_name, tags, tcmalloc=collect_tcmalloc_metrics),
            HostInfoCollector(self, tags),
            ProcessStatsCollector(self, tags),
        ]
        if self._config.replica_check:
            potential_collectors.append(ReplicaCollector(self, tags))
        if 'jumbo_chunks' in self._config.additional_metrics:
            potential_collectors.append(JumboStatsCollector(self, tags))
        if 'top' in self._config.additional_metrics:
            potential_collectors.append(TopCollector(self, tags))
        if 'sharded_data_distribution' in self._config.additional_metrics:
            potential_collectors.append(ShardedDataDistributionStatsCollector(self, tags))
        assert self._mongo_version is not None, "No MongoDB version is set, make sure you refreshed the metadata."
        if self._mongo_version_parsed >= Version("3.6"):
            potential_collectors.append(SessionStatsCollector(self, tags))

        dbstats_tag_dbname = self._config.dbstats_tag_dbname
        for db_name in all_dbs:
            # DbStatCollector is always collected on all monitored databases (filtered by db_names config option)
            # For backward compatibility, we keep collecting from all monitored databases
            # regardless of the auto-discovery settings.
            potential_collectors.append(DbStatCollector(self, db_name, dbstats_tag_dbname, tags))

        # When autodiscovery is enabled, we collect collstats and indexstats for all auto-discovered databases
        # Otherwise, we collect collstats and indexstats for the database specified in the configuration
        for db_name in self.databases_monitored:
            # For backward compatibility, coll_names is ONLY applied when autodiscovery is not enabled
            # Otherwise, we collect collstats & indexstats for all auto-discovered databases and authorized collections
            coll_names = None if self._database_autodiscovery.autodiscovery_enabled else self._config.coll_names
            if 'collection' in self._config.additional_metrics:
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
            self.deployment_type is None  # First run
            or isinstance(self.deployment_type, ReplicaSetDeployment)  # Replica set members and state can change
            or isinstance(self.deployment_type, MongosDeployment)  # Mongos shard map can change
        ):
            deployment_type_before = self.deployment_type
            self.log.debug("Refreshing deployment type")
            self.refresh_deployment_type()
            if self.deployment_type != deployment_type_before:
                self.log.debug(
                    "Deployment type has changed from %s to %s", deployment_type_before, self.deployment_type
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
        tags = []
        if self._resolved_hostname:
            tags.append(f"dd.internal.resource:database_instance:{self._resolved_hostname}")
        if self._config.cloud_metadata:
            aws = self._config.cloud_metadata.get('aws')
            if instance_endpoint := aws.get('instance_endpoint'):
                tags.append(f"dd.internal.resource:aws_docdb_instance:{instance_endpoint}")
            if cluster_identifier := aws.get('cluster_identifier'):
                tags.append(f"dd.internal.resource:aws_docdb_cluster:{cluster_identifier}")
        return tags

    def _get_tags(self, include_internal_resource_tags=False):
        tags = deepcopy(self._config.metric_tags)
        tags.extend(self.deployment_type.deployment_tags)
        if include_internal_resource_tags:
            tags.extend(self.internal_resource_tags)
        if isinstance(self.deployment_type, ReplicaSetDeployment):
            tags.extend(self.deployment_type.replset_tags)
        return tags

    def _get_service_check_tags(self):
        tags = deepcopy(self._config.service_check_tags)
        if self._resolved_hostname:
            tags.append(f"database_instance:{self._resolved_hostname}")
        return tags

    def check(self, _):
        try:
            self._refresh_metadata()
            self._refresh_deployment()
            self._collect_metrics()
            self._send_database_instance_metadata()

            # DBM
            if self._config.dbm_enabled:
                self._operation_samples.run_job_loop(tags=self._get_tags(include_internal_resource_tags=True))
                self._slow_operations.run_job_loop(tags=self._get_tags(include_internal_resource_tags=True))
                self._schemas.run_job_loop(tags=self._get_tags(include_internal_resource_tags=True))
        except CRITICAL_FAILURE as e:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags)
            self._unset_metadata()
            raise e  # Let exception bubble up to global handler and show full error in the logs.
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags)

    def _refresh_metadata(self):
        if self._mongo_version is None or self._mongo_modules is None:
            self.log.debug('No mongo_version or mongo_module metadata present, refreshing it.')
            server_info = self.api_client.server_info()
            self._mongo_version = server_info.get('version', '0.0')
            self._mongo_version_parsed = Version(self._mongo_version.split("-")[0])
            self.set_metadata('version', self._mongo_version)
            self.log.debug('version: %s', self._mongo_version)
            self._mongo_modules = server_info.get('modules', [])
            self.set_metadata('modules', ','.join(self._mongo_modules))
            self.log.debug('modules: %s', self._mongo_modules)
        if self._resolved_hostname is None:
            self._resolved_hostname = self._config.reported_database_hostname or self.api_client.hostname
            self.set_metadata('resolved_hostname', self._resolved_hostname)
            self.log.debug('resolved_hostname: %s', self._resolved_hostname)
        if self._config.cluster_name:
            self.set_metadata('cluster_name', self._config.cluster_name)

    def _unset_metadata(self):
        self.log.debug('Due to connection failure we will need to reset the metadata.')
        self._mongo_version = None
        self._resolved_hostname = None

    def _collect_metrics(self):
        deployment = self.deployment_type
        tags = self._get_tags(include_internal_resource_tags=True)

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

    @property
    def databases_monitored(self):
        if self._database_autodiscovery.autodiscovery_enabled:
            return self._database_autodiscovery.databases
        return [self._config.db_name]

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
        deployment = self.deployment_type
        if self._resolved_hostname not in self._database_instance_emitted:
            # DO NOT emit with internal resource tags, as the metadata event is used to CREATE the databse instance
            tags = self._get_tags()
            mongodb_instance_metadata = {
                "cluster_name": self._config.cluster_name,
                "modules": self._mongo_modules,
            } | deployment.instance_metadata
            database_instance = {
                "host": self._resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "mongo",
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
            self._slow_operations.cancel()

    def _get_rs_deployment_from_status_payload(self, repl_set_payload, is_master_payload, cluster_role, hosting_type):
        replset_name = repl_set_payload["set"]
        replset_state = repl_set_payload["myState"]
        hosts = [m['name'] for m in repl_set_payload.get("members", [])]
        replset_me = is_master_payload.get('me')
        replset_tags = is_master_payload.get('tags')
        return ReplicaSetDeployment(
            hosting_type,
            replset_name,
            replset_state,
            hosts,
            replset_me,
            cluster_role=cluster_role,
            replset_tags=replset_tags,
        )

    def refresh_deployment_type(self):
        # getCmdLineOpts is the runtime configuration of the mongo instance. Helpful to know whether the node is
        # a mongos or mongod, if the mongod is in a shard, if it's in a replica set, etc.
        try:
            self.deployment_type = self._get_default_deployment_type()
        except Exception as e:
            self.log.debug(
                "Unable to run `getCmdLineOpts`, got: %s. Treating this as an Alibaba ApsaraDB instance.", str(e)
            )
            try:
                self.deployment_type = self._get_alibaba_deployment_type()
            except Exception as e:
                self.log.debug("Unable to run `shardingState`, so switching to AWS DocumentDB, got error %s", str(e))
                self.deployment_type = self._get_documentdb_deployment_type()

    def _get_default_deployment_type(self):
        options = self.api_client.get_cmdline_opts()
        cluster_role = None
        hosting_type = HostingType.ATLAS if self._is_hosting_type_atlas() else HostingType.SELF_HOSTED
        if 'sharding' in options:
            if 'configDB' in options['sharding']:
                self.log.debug("Detected MongosDeployment. Node is principal.")
                return MongosDeployment(hosting_type=hosting_type, shard_map=self.refresh_shards())
            elif 'clusterRole' in options['sharding']:
                cluster_role = options['sharding']['clusterRole']

        replication_options = options.get('replication', {})
        if 'replSetName' in replication_options or 'replSet' in replication_options:
            repl_set_payload = self.api_client.replset_get_status()
            is_master_payload = self.api_client.is_master()
            replica_set_deployment = self._get_rs_deployment_from_status_payload(
                repl_set_payload,
                is_master_payload,
                cluster_role,
                hosting_type,
            )
            is_principal = replica_set_deployment.is_principal()
            is_principal_log = "" if is_principal else "not "
            self.log.debug("Detected ReplicaSetDeployment. Node is %sprincipal.", is_principal_log)
            return replica_set_deployment

        self.log.debug("Detected StandaloneDeployment. Node is principal.")
        return StandaloneDeployment(hosting_type=hosting_type)

    def _get_alibaba_deployment_type(self):
        hosting_type = HostingType.ALIBABA_APSARADB
        is_master_payload = self.api_client.is_master()
        if is_master_payload.get('msg') == 'isdbgrid':
            return MongosDeployment(hosting_type=hosting_type, shard_map=self.refresh_shards())

        # On alibaba cloud, a mongo node is either a mongos or part of a replica set.
        repl_set_payload = self.api_client.replset_get_status()
        if repl_set_payload.get('configsvr') is True:
            cluster_role = 'configsvr'
        elif self.api_client.sharding_state_is_enabled() is True:
            # Use `shardingState` command to know whether or not the replicaset
            # is a shard or not.
            cluster_role = 'shardsvr'
        else:
            cluster_role = None
        return self._get_rs_deployment_from_status_payload(
            repl_set_payload, is_master_payload, cluster_role, hosting_type
        )

    def _get_documentdb_deployment_type(self):
        """
        Deployment type for AWS DocumentDB.

        We connect to "Instance Based Clusters". In MongoDB terms, these are unsharded replicasets.
        """
        repl_set_payload = self.api_client.replset_get_status()
        is_master_payload = self.api_client.is_master()
        return self._get_rs_deployment_from_status_payload(
            repl_set_payload, is_master_payload, cluster_role=None, hosting_type=HostingType.DOCUMENTDB
        )

    def _is_hosting_type_atlas(self):
        # Atlas deployments have mongodb.net in the internal hostname
        # DO NOT use the connection host because this can be a load balancer or proxy
        # TODO: Is there a better way to detect MongoDB Atlas deployment?
        if self.api_client.hostname and "mongodb.net" in self.api_client.hostname:
            return True
        return False

    def refresh_shards(self):
        try:
            shard_map = self.api_client.get_shard_map()
            self.log.debug('Get shard map: %s', shard_map)
            return shard_map
        except Exception as e:
            self.log.error('Unable to get shard map for mongos: %s', e)
            return {}
