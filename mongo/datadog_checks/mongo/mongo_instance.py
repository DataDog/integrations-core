# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
import time
from copy import deepcopy

from cachetools import TTLCache
from packaging.version import Version

from datadog_checks.base.config import is_affirmative
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.mongo.__about__ import __version__
from datadog_checks.mongo.api import CRITICAL_FAILURE, MongoApi
from datadog_checks.mongo.collectors.coll_stats import CollStatsCollector
from datadog_checks.mongo.collectors.conn_pool_stats import ConnPoolStatsCollector
from datadog_checks.mongo.collectors.custom_queries import CustomQueriesCollector
from datadog_checks.mongo.collectors.db_stat import DbStatCollector
from datadog_checks.mongo.collectors.fsynclock import FsyncLockCollector
from datadog_checks.mongo.collectors.host_info import HostInfoCollector
from datadog_checks.mongo.collectors.index_stats import IndexStatsCollector
from datadog_checks.mongo.collectors.jumbo_stats import JumboStatsCollector
from datadog_checks.mongo.collectors.process_stats import ProcessStatsCollector
from datadog_checks.mongo.collectors.replica import ReplicaCollector
from datadog_checks.mongo.collectors.replication_info import ReplicationOpLogCollector
from datadog_checks.mongo.collectors.server_status import ServerStatusCollector
from datadog_checks.mongo.collectors.session_stats import SessionStatsCollector
from datadog_checks.mongo.collectors.sharded_data_distribution_stats import ShardedDataDistributionStatsCollector
from datadog_checks.mongo.collectors.top import TopCollector
from datadog_checks.mongo.common import HostingType, MongosDeployment, ReplicaSetDeployment, StandaloneDeployment
from datadog_checks.mongo.discovery import MongoDBDatabaseAutodiscovery

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


class MongoInstance:
    def __init__(self, check, connection_host, connection_options, reported_database_hostname=None):
        self._check = check
        self._config = check._config
        self._log = check.log
        self.connection_host = connection_host
        self.connection_options = connection_options
        self.reported_database_hostname = reported_database_hostname

        self._api_client = None

        self.deployment_type = None
        self.resolved_hostname = None

        self.mongo_version = None
        self.mongo_modules = None

        self._database_autodiscovery = MongoDBDatabaseAutodiscovery(mongo_instance=self)

        self._collectors = []

        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=self._config.database_instance_collection_interval,
        )

    @property
    def api_client(self):
        if self._api_client is None:
            self._api_client = MongoApi(self.connection_host, self.connection_options, self._check.log)
        return self._api_client

    @api_client.setter
    def api_client(self, value):
        self._api_client = value

    def refresh(self):
        self._refresh_metadata()
        self._refresh_deployment()
        if self._config.dbm_enabled:
            self.send_database_instance_metadata()
        self.collect_metrics()

    def _refresh_metadata(self):
        if self.mongo_version is None or self.mongo_modules is None:
            self._log.debug('No mongo_version or mongo_module metadata present, refreshing it.')
            server_info = self.api_client.server_info()
            self.mongo_version = server_info.get('version', '0.0')
            self.mongo_version_parsed = Version(self.mongo_version.split("-")[0])
            self._log.debug('version: %s', self.mongo_version)
            self.mongo_modules = server_info.get('modules', [])
            self._log.debug('modules: %s', self.mongo_modules)
            self._check.set_metadata('version', self.mongo_version)
            self._check.set_metadata('modules', ','.join(self.mongo_modules))
            self._check.set_metadata('cluster_name', self._config.cluster_name)
        if self.resolved_hostname is None:
            self.resolved_hostname = self.reported_database_hostname or self.api_client.hostname

    def _refresh_deployment(self):
        if (
            self.deployment_type is None  # First run
            or isinstance(self.deployment_type, ReplicaSetDeployment)  # Replica set members and state can change
            or isinstance(self.deployment_type, MongosDeployment)  # Mongos shard map can change
        ):
            deployment_type_before = self.deployment_type
            self._log.debug("Refreshing deployment type")
            self.refresh_deployment_type()
            if self.deployment_type != deployment_type_before:
                self._log.debug(
                    "Deployment type has changed from %s to %s", deployment_type_before, self.deployment_type
                )
                # database_instance metadata is tied to the deployment type
                # so we need to reset it when the deployment type changes
                # this way new metadata will be emitted
                self._database_instance_emitted.clear()

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
            self._log.debug(
                "Unable to run `getCmdLineOpts`, got: %s. Treating this as an Alibaba ApsaraDB instance.", str(e)
            )
            try:
                self.deployment_type = self._get_alibaba_deployment_type()
            except Exception as e:
                self._log.debug("Unable to run `shardingState`, so switching to AWS DocumentDB, got error %s", str(e))
                self.deployment_type = self._get_documentdb_deployment_type()

    def _get_default_deployment_type(self):
        options = self.api_client.get_cmdline_opts()
        cluster_role = None
        hosting_type = HostingType.ATLAS if self._is_hosting_type_atlas() else HostingType.SELF_HOSTED
        if 'sharding' in options:
            if 'configDB' in options['sharding']:
                self._log.debug("Detected MongosDeployment. Node is principal.")
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
            self._log.debug("Detected ReplicaSetDeployment. Node is %sprincipal.", is_principal_log)
            return replica_set_deployment

        self._log.debug("Detected StandaloneDeployment. Node is principal.")
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
            self._log.debug('Get shard map: %s', shard_map)
            return shard_map
        except Exception as e:
            self._log.error('Unable to get shard map for mongos: %s', e)
            return {}

    @property
    def internal_resource_tags(self):
        '''
        Return the internal resource tags for the database instance.
        '''
        resolved_hostname = self.reported_database_hostname or self.api_client.hostname
        return [f"dd.internal.resource:database_instance:{resolved_hostname}"]

    def get_tags(self, include_internal_resource_tags=False):
        tags = deepcopy(self._config.metric_tags)
        tags.extend(self.deployment_type.deployment_tags)
        if include_internal_resource_tags:
            tags.extend(self.internal_resource_tags)
        if isinstance(self.deployment_type, ReplicaSetDeployment):
            tags.extend(self.deployment_type.replset_tags)
        return tags

    def send_database_instance_metadata(self):
        deployment = self.deployment_type
        if self.resolved_hostname not in self._database_instance_emitted:
            # DO NOT emit with internal resource tags, as the metadata event is used to CREATE the databse instance
            tags = self.get_tags()
            mongodb_instance_metadata = {
                "cluster_name": self._config.cluster_name,
                "modules": self.mongo_modules,
            } | deployment.instance_metadata
            database_instance = {
                "host": self.resolved_hostname,
                "agent_version": datadog_agent.get_version(),
                "dbms": "mongo",
                "kind": "mongodb_instance",
                "collection_interval": self._config.database_instance_collection_interval,
                'dbms_version': self.mongo_version,
                'integration_version': __version__,
                "tags": tags,
                "timestamp": time.time() * 1000,
                "metadata": {
                    "dbm": self._config.dbm_enabled,
                    "connection_host": ','.join(self.connection_host),
                    "instance_metadata": {k: v for k, v in mongodb_instance_metadata.items() if v is not None},
                },
            }
            self._database_instance_emitted[self.resolved_hostname] = database_instance
            self._log.debug("Emitting database instance  metadata, %s", database_instance)
            self._check.database_monitoring_metadata(json.dumps(database_instance, default=default_json_event_encoding))

    def _get_db_names(self, tags):
        dbnames, database_count = self._database_autodiscovery.get_databases_and_count()
        if database_count:
            self._check.gauge('mongodb.dbs', database_count, tags=tags)
        return dbnames

    @property
    def databases_monitored(self):
        if self._database_autodiscovery.autodiscovery_enabled:
            return self._database_autodiscovery.databases
        return [self._config.db_name]

    def _refresh_collectors(self, deployment_type, all_dbs, tags):
        collect_tcmalloc_metrics = 'tcmalloc' in self._config.additional_metrics
        potential_collectors = [
            ConnPoolStatsCollector(self._check, tags),
            ReplicationOpLogCollector(self._check, tags),
            FsyncLockCollector(self._check, tags),
            ServerStatusCollector(self._check, self._config.db_name, tags, tcmalloc=collect_tcmalloc_metrics),
            HostInfoCollector(self._check, tags),
            ProcessStatsCollector(self._check, tags),
        ]
        if self._config.replica_check:
            potential_collectors.append(ReplicaCollector(self._check, tags, deployment_type))
        if 'jumbo_chunks' in self._config.additional_metrics:
            potential_collectors.append(JumboStatsCollector(self._check, tags))
        if 'top' in self._config.additional_metrics:
            potential_collectors.append(TopCollector(self._check, tags))
        if 'sharded_data_distribution' in self._config.additional_metrics:
            potential_collectors.append(ShardedDataDistributionStatsCollector(self._check, tags))
        assert self.mongo_version is not None, "No MongoDB version is set, make sure you refreshed the metadata."
        if self.mongo_version_parsed >= Version("3.6"):
            potential_collectors.append(SessionStatsCollector(self._check, tags))

        dbstats_tag_dbname = self._config.dbstats_tag_dbname
        for db_name in all_dbs:
            # DbStatCollector is always collected on all monitored databases (filtered by db_names config option)
            # For backward compatibility, we keep collecting from all monitored databases
            # regardless of the auto-discovery settings.
            potential_collectors.append(DbStatCollector(self._check, db_name, dbstats_tag_dbname, tags))

        # When autodiscovery is enabled, we collect collstats and indexstats for all auto-discovered databases
        # Otherwise, we collect collstats and indexstats for the database specified in the configuration
        for db_name in self.databases_monitored:
            # For backward compatibility, coll_names is ONLY applied when autodiscovery is not enabled
            # Otherwise, we collect collstats & indexstats for all auto-discovered databases and authorized collections
            coll_names = None if self._database_autodiscovery.autodiscovery_enabled else self._config.coll_names
            if 'collection' in self._config.additional_metrics:
                potential_collectors.append(CollStatsCollector(self._check, db_name, tags, coll_names=coll_names))
            if self._config.collections_indexes_stats:
                if self.mongo_version_parsed >= Version("3.2"):
                    potential_collectors.append(IndexStatsCollector(self._check, db_name, tags, coll_names=coll_names))
                else:
                    self._log.debug(
                        "'collections_indexes_stats' is only available starting from mongo 3.2: "
                        "your mongo version is %s",
                        self.mongo_version,
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
                self._log.debug(
                    "{} custom queries defined in the configuration won't be run because the mongod node is a "
                    "secondary and the queries don't specify 'run_on_secondary: true' in the configuration. "
                    "Custom queries are only run on mongos, primaries, or standalone by default to prevent "
                    "duplicated information."
                )

        potential_collectors.append(CustomQueriesCollector(self._check, self._config.db_name, tags, queries))

        self._collectors = [coll for coll in potential_collectors if coll.compatible_with(deployment_type)]

    def collect_metrics(self):
        deployment = self.deployment_type
        tags = self.get_tags(include_internal_resource_tags=True)

        dbnames = self._get_db_names(tags)
        self._refresh_collectors(deployment, dbnames, tags)
        for collector in self._collectors:
            try:
                collector.collect(self.api_client)
            except CRITICAL_FAILURE as e:
                self._log.info(
                    "Unable to collect logs from collector %s. Some metrics will be missing.", collector, exc_info=True
                )
                raise e  # Critical failures must bubble up to trigger a CRITICAL service check.
            except Exception:
                self._log.info(
                    "Unable to collect logs from collector %s. Some metrics will be missing.", collector, exc_info=True
                )
