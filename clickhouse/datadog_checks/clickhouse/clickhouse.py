# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time

import clickhouse_connect
from clickhouse_connect.driver import httputil

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.base.utils.db.utils import default_json_event_encoding, resolve_db_host
from datadog_checks.base.utils.serialization import json

from . import advanced_queries, queries, utils
from .__about__ import __version__
from .config import build_config, sanitize
from .health import ClickhouseHealth, ClickhouseHealthEvent, HealthEvent, HealthStatus
from .metadata import ClickhouseMetadata
from .parts_and_merges import ClickhousePartsAndMerges
from .query_completions import ClickhouseQueryCompletions
from .query_errors import ClickhouseQueryErrors
from .statement_samples import ClickhouseStatementSamples
from .statements import ClickhouseStatementMetrics
from .table_metrics import ClickhouseTableMetrics
from .utils import (
    CLOUD_MODE_QUERY,
    CLUSTER_MACRO_QUERY,
    CLUSTER_NAME_QUERY,
    CLUSTER_TAG,
    CONNECT_NODE_QUERY,
    DBM_BLOCKED_REASON_MISSING_GRANTS,
    HOSTING_TYPE_TAG,
    SHARED_MERGE_TREE_QUERY,
    DbmCollectionStatus,
    ErrorSanitizer,
    HostingType,
    ProbeError,
    ProbeErrorKind,
    TopologyProbe,
    classify_probe_error,
    cluster_all_replicas,
    cluster_aware_query,
    cluster_nodes_query,
)

# Database instance collection interval in seconds (not user-configurable)
DATABASE_INSTANCE_COLLECTION_INTERVAL = 300

MISSING_GRANTS_HEALTH_COOLDOWN = 60 * 60


class ClickhouseCheck(DatabaseCheck):
    DBMS = 'clickhouse'

    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        # Build typed configuration
        config, validation_result = build_config(self)
        self._config = config
        self._validation_result = validation_result

        # Initialize health event handler for DBM
        self.health = ClickhouseHealth(self)

        # Log validation warnings (errors will be raised in validate_config)
        for warning in validation_result.warnings:
            self.log.warning(warning)

        # DBM-related properties (computed lazily)
        self._resolved_hostname = None
        self._database_hostname = None
        self._dbms_version = None
        self._cluster_name = None
        self._cluster_name_resolved = False
        self._hosting_type = None
        self._probe_errors: dict[str, ProbeError] = {}
        self._topology: dict = {}
        self._topology_refreshed_at = 0
        self._dbm_collection: dict = {}
        self._dbm_blocked = False

        # Track last emission time for database instance metadata (rate limiting)
        self._database_instance_last_emitted = 0

        self.tag_manager.set_tags_from_list(self._config.tags, replace=True)
        self._add_core_tags()

        self._error_sanitizer = ErrorSanitizer(self._config.password)
        self.check_initializations.append(self.validate_config)
        self.check_initializations.append(advanced_queries.warm_cache)

        # Submit health event with config validation result
        # Tags are now available so health events will include them
        self._submit_config_health_event()

        # We'll connect on the first check run
        self._client = None

        # Cache query manager per server version to avoid recompiling on every check run
        self._query_manager: QueryManager | None = None
        self._query_manager_version: str | None = None
        self._query_manager_cluster: str | None = None

        # Shared HTTP connection pool for all ClickHouse clients (main + DBM jobs).
        # TLS settings must be baked in here: when pool_mgr is provided to get_client(),
        # clickhouse-connect assigns it immediately and skips its own TLS pool creation,
        # so verify=False would be silently ignored if the pool was created without it.
        self._pool_manager = httputil.get_pool_manager(
            maxsize=8,
            num_pools=4,
            verify=self._config.verify,
            ca_cert=self._config.tls_ca_cert,
        )

        self.statement_metrics: ClickhouseStatementMetrics | None = None
        self.statement_samples: ClickhouseStatementSamples | None = None
        self.query_completions: ClickhouseQueryCompletions | None = None
        self.query_errors: ClickhouseQueryErrors | None = None
        self.table_metrics: ClickhouseTableMetrics | None = None
        self.metadata: ClickhouseMetadata | None = None
        self.parts_and_merges: ClickhousePartsAndMerges | None = None
        self._register_async_jobs()

    def _register_async_jobs(self):
        """Build and register the async jobs enabled by this check's configuration."""
        if not self._config.dbm:
            return

        # Query metrics (from system.query_log)
        if self._config.query_metrics.enabled:
            self.statement_metrics = self.register_async_job(
                ClickhouseStatementMetrics(self, self._config.query_metrics)
            )

        # Query samples (from system.processes) and pending async inserts (system.asynchronous_inserts)
        if self._config.query_samples.enabled or self._config.collect_pending_async_inserts.enabled:
            self.statement_samples = self.register_async_job(
                ClickhouseStatementSamples(self, self._config.query_samples, self._config.collect_pending_async_inserts)
            )

        # Completed queries and async insert flushes (from system.query_log and system.asynchronous_insert_log)
        if self._config.query_completions.enabled or self._config.collect_async_inserts.enabled:
            self.query_completions = self.register_async_job(
                ClickhouseQueryCompletions(self, self._config.query_completions, self._config.collect_async_inserts)
            )

        # Failed queries (from system.query_log)
        if self._config.query_errors.enabled:
            self.query_errors = self.register_async_job(ClickhouseQueryErrors(self, self._config.query_errors))

        # Schema metrics (from system.tables and system.view_refreshes)
        if self._config.schema_metrics.enabled:
            self.table_metrics = self.register_async_job(ClickhouseTableMetrics(self, self._config.schema_metrics))

        # Schema collection (from system.tables and system.columns)
        if self._config.collect_schemas.enabled:
            self.metadata = self.register_async_job(ClickhouseMetadata(self))

        # Parts and merges (from system.parts, merges, mutations, replication_queue)
        if self._config.parts_and_merges.enabled:
            self.parts_and_merges = self.register_async_job(
                ClickhousePartsAndMerges(self, self._config.parts_and_merges)
            )

    def _add_core_tags(self):
        """
        Add tags that should be attached to every metric/event.
        These are core identification tags for the ClickHouse instance.
        """
        self.tag_manager.set_tag("server", self._config.server, replace=True)
        self.tag_manager.set_tag("port", str(self._config.port), replace=True)
        self.tag_manager.set_tag("db", self._config.db, replace=True)
        self.tag_manager.set_tag("database_hostname", self.database_hostname, replace=True)
        self.tag_manager.set_tag("database_instance", self.database_identifier, replace=True)

    def validate_config(self):
        """
        Validate the configuration and raise an error if invalid.
        This is called during check initialization.
        """
        from datadog_checks.base import ConfigurationError

        if not self._validation_result.valid:
            for error in self._validation_result.errors:
                self.log.error(str(error))
            if self._validation_result.errors:
                raise ConfigurationError(str(self._validation_result.errors[0]))

    def _submit_config_health_event(self):
        """
        Submit a health event with the configuration validation result.

        This event reports the initialization status to DBM, including:
        - Configuration errors (if any)
        - Configuration warnings (if any)
        - DBM feature enablement status

        Uses a 6-hour cooldown to avoid spamming health events.
        """
        try:
            # Determine health status based on validation result
            if not self._validation_result.valid:
                status = HealthStatus.ERROR
            elif self._validation_result.warnings:
                status = HealthStatus.WARNING
            else:
                status = HealthStatus.OK

            self.health.submit_health_event(
                name=HealthEvent.INITIALIZATION,
                status=status,
                cooldown_time=60 * 60 * 6,  # 6 hours
                data={
                    "errors": [str(error) for error in self._validation_result.errors],
                    "warnings": self._validation_result.warnings,
                    "initialized_at": self._validation_result.created_at,
                    "config": sanitize(self._config),
                    "instance": sanitize(self.instance),
                    "features": self._validation_result.features,
                },
            )
        except Exception as e:
            # Health event submission should not break the check initialization
            self.log.debug("Failed to submit config health event: %s", e)

    def _send_database_instance_metadata(self):
        """Send database instance metadata to the metadata intake."""
        current_time = time()
        if current_time - self._database_instance_last_emitted >= DATABASE_INSTANCE_COLLECTION_INTERVAL:
            # Get tags without db: prefix for metadata
            tags_no_db = [t for t in self.tags if not t.startswith('db:')]
            self._refresh_topology()

            metadata = {
                "dbm": self._config.dbm,
                "connection_host": self._config.server,
                "hosting_type": self.hosting_type,
                "single_endpoint_mode": self.is_single_endpoint_mode,
                **self._topology,
                "dbm_collection": self._dbm_collection,
            }

            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.database_hostname,
                "agent_version": self.agent_version,
                "ddagenthostname": self.agent_hostname,
                "dbms": self.dbms,
                "kind": "database_instance",
                "collection_interval": DATABASE_INSTANCE_COLLECTION_INTERVAL,
                "dbms_version": self.dbms_version,
                "integration_version": __version__,
                "tags": tags_no_db,
                "timestamp": current_time * 1000,
                "metadata": metadata,
            }

            self._database_instance_last_emitted = current_time
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def check(self, _):
        self.connect()
        self._dbms_version = self.select_version()
        self._refresh_topology()

        # Must run before the query manager is built and before the DBM jobs are handed
        # self.tags below, since both snapshot the tag list.
        if self.cluster_name:
            self.tag_manager.set_tag(CLUSTER_TAG, self.cluster_name, replace=True)
        self.tag_manager.set_tag(HOSTING_TYPE_TAG, self.hosting_type, replace=True)

        fanout_cluster = self.fanout_cluster_name
        if (
            self._query_manager is None
            or self._query_manager_version != self.dbms_version
            or self._query_manager_cluster != fanout_cluster
        ):
            self._query_manager = self._build_query_manager()
            self._query_manager_version = self.dbms_version
            self._query_manager_cluster = fanout_cluster
        self._query_manager.execute()
        self.set_version_metadata(self.dbms_version)

        # Send database instance metadata
        self._send_database_instance_metadata()

        if self._dbm_blocked:
            self._report_dbm_blocked()
            return
        self.run_async_jobs(self.tags)

    def _refresh_topology(self):
        """Re-read the cluster topology and decide whether DBM may run, at most once per collection interval.

        While DBM is blocked, the cached cluster name and hosting type are dropped first, so adding the
        missing grants takes effect without an Agent restart.
        """
        now = time()
        if now - self._topology_refreshed_at < DATABASE_INSTANCE_COLLECTION_INTERVAL:
            return
        if self._dbm_blocked:
            self._cluster_name_resolved = False
            self._hosting_type = None
            self._probe_errors.clear()

        self._topology_refreshed_at = now
        self._topology = self._cluster_topology_metadata()
        self._dbm_collection = self._evaluate_dbm_collection(self._topology, now)

        blocked = self._dbm_collection['status'] == DbmCollectionStatus.BLOCKED
        if blocked and not self._dbm_blocked:
            self.log.warning(
                'Pausing Database Monitoring, topology probes were denied: %s',
                {
                    probe: self._error_sanitizer.clean(self._error_sanitizer.scrub(error.message))
                    for probe, error in sorted(self._probe_errors.items())
                    if error.kind == ProbeErrorKind.DENIED
                },
            )
        elif self._dbm_blocked and not blocked:
            self.log.info('Resuming Database Monitoring, the ClickHouse topology is readable again')
            self.health.submit_health_event(
                name=ClickhouseHealthEvent.MISSING_GRANTS,
                status=HealthStatus.OK,
                data={'blocked': False},
            )
        self._dbm_blocked = blocked

    def _evaluate_dbm_collection(self, topology: dict, checked_at: float) -> dict:
        """The `dbm_collection` record for the database_instance payload.

        DBM is blocked only when a topology field this instance needs is missing and a probe that would
        have supplied it was denied. Any other failure behind a missing field is reported as degraded.
        """
        error_kinds = {
            self._probe_errors[probe].kind
            for probe in self._probes_behind_missing_topology(topology)
            if probe in self._probe_errors
        }
        if self._config.dbm and ProbeErrorKind.DENIED in error_kinds:
            status = DbmCollectionStatus.BLOCKED
        elif error_kinds:
            status = DbmCollectionStatus.DEGRADED
        else:
            status = DbmCollectionStatus.ACTIVE

        collection: dict = {'status': status}
        if status == DbmCollectionStatus.BLOCKED:
            collection['reason'] = DBM_BLOCKED_REASON_MISSING_GRANTS
        missing_grants = self._missing_grants()
        if missing_grants:
            collection['missing_grants'] = missing_grants
        if self._probe_errors:
            collection['probe_errors'] = {probe: error.kind for probe, error in sorted(self._probe_errors.items())}
        collection['checked_at'] = int(checked_at * 1000)
        return collection

    def _probes_behind_missing_topology(self, topology: dict) -> tuple[str, ...]:
        """The probes that would have supplied the topology fields this instance needs but does not have."""
        hosting_type = self.hosting_type
        if hosting_type == HostingType.UNKNOWN:
            return (TopologyProbe.CLOUD_MODE, TopologyProbe.SHARED_MERGE_TREE)
        if hosting_type == HostingType.CLOUD:
            return () if topology.get('nodes') else (TopologyProbe.NODES,)
        if not self.is_single_endpoint_mode:
            return () if topology.get('connect_node') else (TopologyProbe.CONNECT_NODE,)
        if not topology.get('cluster_name'):
            return (TopologyProbe.CLUSTER_MACRO, TopologyProbe.CLUSTER_NAME)
        return () if topology.get('nodes') else (TopologyProbe.NODES,)

    def _missing_grants(self) -> list[str]:
        return sorted({grant for error in self._probe_errors.values() for grant in error.grants})

    def _report_dbm_blocked(self):
        """Surface the paused DBM collection on every blocked run, since check warnings are cleared after each run."""
        missing_grants = self._missing_grants()
        username = self._config.username or 'default'
        remediation = [f'GRANT {grant} TO {username};' for grant in missing_grants]
        self.warning(
            "Database Monitoring is paused for %s: the Agent user '%s' is missing grants needed to read the "
            "ClickHouse cluster topology. Run:\n%s\n"
            "Collection resumes within 5 minutes of the grants being added. No Agent restart is needed.\n"
            "code=missing-topology-grants",
            self.database_identifier,
            username,
            '\n'.join(f'  {statement}' for statement in remediation),
        )
        self.health.submit_health_event(
            name=ClickhouseHealthEvent.MISSING_GRANTS,
            status=HealthStatus.WARNING,
            cooldown_time=MISSING_GRANTS_HEALTH_COOLDOWN,
            cooldown_values=missing_grants,
            data={
                'blocked': True,
                'missing_grants': missing_grants,
                'probe_errors': self._dbm_collection.get('probe_errors', {}),
                'hosting_type': self.hosting_type,
                'single_endpoint_mode': self.is_single_endpoint_mode,
                'remediation': remediation,
            },
        )

    def get_queries(self) -> list[dict]:
        query_list = []
        cluster = self.fanout_cluster_name if self._config.single_endpoint_mode else None

        def pick(query: dict) -> dict:
            """In single endpoint mode, read all replicas and tag each row per node."""
            return cluster_aware_query(query, cluster) if cluster else query

        if self._config.use_legacy_queries:
            query_list.extend(
                [
                    pick(queries.SystemMetrics),
                    pick(queries.SystemEventsToDeprecate),
                    pick(queries.SystemEvents),
                    pick(queries.SystemAsynchronousMetrics),
                    queries.SystemParts,
                    queries.SystemReplicas,
                    queries.SystemDictionaries,
                ]
            )

        if self._config.use_advanced_queries:
            query_list.extend(
                [
                    pick(advanced_queries.SystemMetrics),
                    pick(advanced_queries.SystemEvents),
                    pick(advanced_queries.SystemAsynchronousMetrics),
                ]
            )
            if self.version_ge('21.3'):
                query_list.append(pick(advanced_queries.SystemErrors))

        return query_list

    def _build_query_manager(self) -> QueryManager:
        query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=self.get_queries(),
            tags=self.tags,
            error_handler=self._error_sanitizer.clean,
        )
        query_manager.compile_queries()

        return query_manager

    def select_version(self) -> str:
        return self._client.command('SELECT version()', use_database=False)

    @AgentCheck.metadata_entrypoint
    def set_version_metadata(self, version: str):
        # The version comes in like `19.15.2.2` though sometimes there is no patch part
        version_parts = dict(zip(('year', 'major', 'minor', 'patch'), version.split('.')))

        self.set_metadata('version', version, scheme='parts', final_scheme='calver', part_map=version_parts)

    def execute_query_raw(self, query):
        return self._client.query(query).result_rows

    def _get_debug_tags(self):
        """Return debug tags for metrics"""
        return ['server:{}'.format(self._config.server)]

    @property
    def reported_hostname(self) -> str | None:
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = resolve_db_host(self._config.server)
        return self._resolved_hostname

    @property
    def database_hostname(self) -> str:
        if self._database_hostname is None:
            self._database_hostname = resolve_db_host(self._config.server)
        return self._database_hostname

    @property
    def cluster_name(self) -> str | None:
        """The cluster this instance belongs to, or None when it cannot be determined.

        Requires a live client, so this resolves on the first check run rather than at
        init. The "not found" outcome is cached too: a deployment without a cluster
        should not re-query on every run. The cache is only dropped while DBM is blocked
        on a missing grant.
        """
        if not self._cluster_name_resolved:
            self._cluster_name = self._resolve_cluster_name()
            self._cluster_name_resolved = True
        return self._cluster_name

    def _resolve_cluster_name(self) -> str | None:
        for probe, query in (
            (TopologyProbe.CLUSTER_MACRO, CLUSTER_MACRO_QUERY),
            (TopologyProbe.CLUSTER_NAME, CLUSTER_NAME_QUERY),
        ):
            rows = self._run_probe(probe, query)
            if rows and rows[0] and rows[0][0]:
                return str(rows[0][0])
        # Deliberately no 'default' fallback: an absent tag is better than a wrong one.
        self.log.debug('No ClickHouse cluster name found; %s tag will not be emitted', CLUSTER_TAG)
        return None

    @property
    def fanout_cluster_name(self) -> str | None:
        """The cluster to fan out over with clusterAllReplicas, or None when there is none to use.

        'default' is only guessed when the deployment is not known to be self-hosted, since Cloud
        always uses that name. A self-hosted cluster is named arbitrarily, so None is returned
        instead and callers fall back to the local system table.
        """
        if self.cluster_name:
            return self.cluster_name
        return None if self.hosting_type == HostingType.SELF_HOSTED else 'default'

    def _cluster_topology_metadata(self) -> dict:
        """The cluster node inventory, for the database_instance payload.

        Keys are omitted rather than reported empty, so a failed query never claims a cluster has
        no nodes.
        """
        metadata = {}
        if self.cluster_name:
            metadata["cluster_name"] = self.cluster_name
        connect_node = self._resolve_connect_node()
        if connect_node:
            metadata["connect_node"] = connect_node
        nodes = self._resolve_cluster_nodes(connect_node)
        if nodes:
            metadata["nodes"] = nodes
        return metadata

    def _run_probe(self, probe: str, query: str) -> list | None:
        """Run a topology probe and record why it failed, returning None when it did."""
        self._probe_errors.pop(probe, None)
        try:
            return self.execute_query_raw(query)
        except Exception as e:
            self._probe_errors[probe] = classify_probe_error(probe, e)
            self.log.debug('Topology probe %s failed with %r: %s', probe, query, e)
            return None

    def _resolve_connect_node(self) -> str | None:
        """The name of the node serving this connection, or None when it cannot be read."""
        rows = self._run_probe(TopologyProbe.CONNECT_NODE, CONNECT_NODE_QUERY)
        return str(rows[0][0]) if rows and rows[0] and rows[0][0] else None

    def _resolve_cluster_nodes(self, connect_node: str | None) -> list[str]:
        """Sorted, de-duplicated cluster node names, or an empty list when they cannot be determined.

        A point-in-time observation rather than a steady-state count: replicas are replaced
        make-before-break, so old and new both answer while the old one drains.
        """
        cluster = self.fanout_cluster_name
        if not cluster:
            self._probe_errors.pop(TopologyProbe.NODES, None)
            return [connect_node] if connect_node else []
        rows = self._run_probe(TopologyProbe.NODES, cluster_nodes_query(cluster))
        if rows is None:
            return []
        return sorted({str(row[0]) for row in rows if row and row[0]})

    @property
    def hosting_type(self) -> str:
        """Whether this instance is ClickHouse Cloud or self-hosted, cached unless DBM is blocked on a grant."""
        if self._hosting_type is None:
            self._hosting_type = self._resolve_hosting_type()
        return self._hosting_type

    def _resolve_hosting_type(self) -> str:
        """Combine two independent Cloud signals; both must agree to report cloud, either can veto it."""
        cloud_mode = self._probe_cloud_mode()
        shared_merge_tree = self._probe_shared_merge_tree()
        self.log.debug('Hosting type signals: cloud_mode=%s, shared_merge_tree=%s', cloud_mode, shared_merge_tree)

        if cloud_mode is False or shared_merge_tree is False:
            return HostingType.SELF_HOSTED
        if cloud_mode and shared_merge_tree:
            return HostingType.CLOUD
        return HostingType.UNKNOWN

    def _probe_cloud_mode(self) -> bool | None:
        """Whether the server reports cloud_mode enabled, or None when the probe failed."""
        rows = self._run_probe(TopologyProbe.CLOUD_MODE, CLOUD_MODE_QUERY)
        if rows is None:
            return None
        if not rows or not rows[0]:
            return False
        return str(rows[0][0]) not in ('', '0')

    def _probe_shared_merge_tree(self) -> bool | None:
        """Whether the Cloud-only SharedMergeTree engine exists, or None when the probe failed."""
        rows = self._run_probe(TopologyProbe.SHARED_MERGE_TREE, SHARED_MERGE_TREE_QUERY)
        if rows is None:
            return None
        return bool(rows and rows[0] and int(rows[0][0]) > 0)

    @property
    def database_identifier_template(self) -> str:
        return self._config.database_identifier.template

    @property
    def database_identifier_params(self) -> dict:
        return {
            "server": str(self._config.server),
            "port": str(self._config.port),
            "db": str(self._config.db),
        }

    @property
    def dbms_version(self) -> str:
        """Get the ClickHouse server version."""
        if self._dbms_version is None:
            return "unknown"
        return self._dbms_version

    @property
    def cloud_metadata(self) -> dict:
        """Get cloud provider metadata if available."""
        # TODO: Populate with cloud metadata when available (e.g., ClickHouse Cloud)
        return {}

    @property
    def is_single_endpoint_mode(self):
        """
        Returns True if single endpoint mode is enabled.

        When True, DBM components should use clusterAllReplicas() to query system tables
        across all nodes in the cluster, since replicas are abstracted behind a single
        endpoint (e.g., load balancer or managed service like ClickHouse Cloud).
        """
        return self._config.single_endpoint_mode

    def get_system_table(self, table_name):
        """
        Get the appropriate system table reference based on deployment type.

        For single endpoint mode: Returns clusterAllReplicas(<cluster>, system.<table>)
        For direct connection: Returns system.<table>

        A single endpoint mode instance whose cluster cannot be determined also reads the local
        table, since there is no cluster name to fan out over.

        Args:
            table_name: The system table name (e.g., 'query_log', 'processes')

        Returns:
            str: The table reference to use in SQL queries

        Example:
            >>> self.get_system_table('query_log')
            "clusterAllReplicas('default', system.query_log)"  # Single endpoint mode
            >>> self.get_system_table('query_log')
            "system.query_log"  # Direct connection
        """
        if self._config.single_endpoint_mode:
            cluster = self.fanout_cluster_name
            if cluster:
                return cluster_all_replicas(cluster, table_name)
        return f"system.{table_name}"

    def ping_clickhouse(self):
        return self._client.ping()

    def connect(self):
        if self.instance.get('user'):
            self._log_deprecation('_config_renamed', 'user', 'username')
        if self._client is not None:
            self.log.debug('Clickhouse client already exists. Pinging Clickhouse Server.')
            try:
                if self.ping_clickhouse():
                    self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self.tags)
                    return
                else:
                    self.log.debug('Clickhouse connection ping failed. Attempting to reconnect')
                    self._client = None
            except Exception as e:
                self.log.debug('Unexpected ping response from Clickhouse', exc_info=e)
                self.log.debug('Attempting to reconnect')
                self._client = None

        try:
            # Convert compression None to False for get_client
            compress = self._config.compression if self._config.compression else False
            client = clickhouse_connect.get_client(
                # https://clickhouse.com/docs/integrations/python#connection-arguments
                host=self._config.server,
                port=self._config.port,
                username=self._config.username,
                password=self._config.password,
                database=self._config.db,
                connect_timeout=self._config.connect_timeout,
                send_receive_timeout=self._config.read_timeout,
                secure=self._config.tls_verify,
                ca_cert=self._config.tls_ca_cert,
                verify=self._config.verify,
                client_name=f'datadog-{self.check_id}',
                compress=compress,
                # https://clickhouse.com/docs/integrations/language-clients/python/driver-api#multi-threaded-applications
                autogenerate_session_id=False,
                # https://clickhouse.com/docs/integrations/python#settings-argument
                settings={},
                # Use shared connection pool for efficiency
                pool_mgr=self._pool_manager,
            )
        except Exception as e:
            error = 'Unable to connect to ClickHouse: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=error, tags=self.tags)
            raise type(e)(error) from None
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self.tags)
            self._client = client

    def create_dbm_client(self):
        """
        Create a ClickHouse client for DBM async jobs.

        Each DBM job gets its own client for isolation, but all clients share
        the same HTTP connection pool for efficiency.

        See: https://clickhouse.com/docs/integrations/language-clients/python/advanced-usage#customizing-the-http-connection-pool
        """
        try:
            # Convert compression None to False for get_client
            compress = self._config.compression if self._config.compression else False
            client = clickhouse_connect.get_client(
                host=self._config.server,
                port=self._config.port,
                username=self._config.username,
                password=self._config.password,
                database=self._config.db,
                secure=self._config.tls_verify,
                connect_timeout=self._config.connect_timeout,
                send_receive_timeout=self._config.read_timeout,
                client_name=f'datadog-dbm-{self.check_id}',
                compress=compress,
                ca_cert=self._config.tls_ca_cert,
                verify=self._config.verify,
                # Disable session IDs for multi-threaded safety
                # See: https://clickhouse.com/docs/integrations/language-clients/python/advanced-usage#managing-clickhouse-session-ids
                autogenerate_session_id=False,
                settings={},
                # Use shared connection pool for efficiency
                pool_mgr=self._pool_manager,
            )
            return client
        except Exception as e:
            error = 'Unable to create DBM client: {}'.format(
                self._error_sanitizer.clean(self._error_sanitizer.scrub(str(e)))
            )
            self.log.warning(error)
            raise

    def shutdown(self) -> None:
        """Close the main client and release the shared connection pool."""
        self._query_manager = None
        self.health = None
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                self.log.debug("Error closing main client: %s", e)
            self._client = None

        # urllib3 pool connections are closed automatically once idle, so dropping the manager is
        # enough. The jobs' dedicated clients share it, and they are shut down before this runs.
        self._pool_manager = None

    def version_lt(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is less than the compared version, otherwise False.
        """
        # The `latest` version should always be greater than any other
        if version == 'latest':
            return True

        return utils.parse_version(self.dbms_version) < utils.parse_version(version)

    def version_ge(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is greater than the compared version, otherwise False.
        """
        # The `latest` version should always be less than any other
        if version == 'latest':
            return False

        return utils.parse_version(self.dbms_version) >= utils.parse_version(version)
