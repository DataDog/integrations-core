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
from .health import ClickhouseHealth, HealthEvent, HealthStatus
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
    HOSTING_TYPE_TAG,
    SHARED_MERGE_TREE_QUERY,
    ErrorSanitizer,
    HostingType,
    cluster_aware_query,
)

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


# Database instance collection interval in seconds (not user-configurable)
DATABASE_INSTANCE_COLLECTION_INTERVAL = 300


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

            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.database_hostname,
                "agent_version": datadog_agent.get_version(),
                "ddagenthostname": self.agent_hostname,
                "dbms": self.dbms,
                "kind": "database_instance",
                "collection_interval": DATABASE_INSTANCE_COLLECTION_INTERVAL,
                "dbms_version": self.dbms_version,
                "integration_version": __version__,
                "tags": tags_no_db,
                "timestamp": current_time * 1000,
                "metadata": {
                    "dbm": self._config.dbm,
                    "connection_host": self._config.server,
                },
            }

            self._database_instance_last_emitted = current_time
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def check(self, _):
        self.connect()
        self._dbms_version = self.select_version()

        # The Agent cancels from another thread, and teardown is deferred until this returns so it
        # cannot close the client from under us. Each remaining stage queries, so gate them on the
        # cancellation rather than working through them all against a check that is going away.
        if self.is_cancelled:
            self.log.debug("Check cancelled, skipping the rest of the run")
            return

        # Must run before the query manager is built and before the DBM jobs are handed
        # self.tags below, since both snapshot the tag list.
        if self.cluster_name:
            self.tag_manager.set_tag(CLUSTER_TAG, self.cluster_name, replace=True)
        self.tag_manager.set_tag(HOSTING_TYPE_TAG, self.hosting_type, replace=True)

        if self.is_cancelled:
            self.log.debug("Check cancelled, skipping the rest of the run")
            return

        if self._query_manager is None or self._query_manager_version != self.dbms_version:
            self._query_manager = self._build_query_manager()
            self._query_manager_version = self.dbms_version
        self._query_manager.execute()
        self.set_version_metadata(self.dbms_version)

        # Send database instance metadata
        self._send_database_instance_metadata()

        self.run_async_jobs(self.tags)

    def get_queries(self) -> list[dict]:
        query_list = []
        single = self._config.single_endpoint_mode

        def pick(query: dict) -> dict:
            """In single endpoint mode, read all replicas and tag each row per node."""
            return cluster_aware_query(query) if single else query

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
        should not re-query on every run.
        """
        if not self._cluster_name_resolved:
            self._cluster_name = self._resolve_cluster_name()
            self._cluster_name_resolved = True
        return self._cluster_name

    def _resolve_cluster_name(self) -> str | None:
        for query in (CLUSTER_MACRO_QUERY, CLUSTER_NAME_QUERY):
            try:
                rows = self.execute_query_raw(query)
            except Exception as e:
                self.log.debug('Unable to resolve cluster name with %r: %s', query, e)
                continue
            if rows and rows[0] and rows[0][0]:
                return str(rows[0][0])
        # Deliberately no 'default' fallback: an absent tag is better than a wrong one.
        self.log.debug('No ClickHouse cluster name found; %s tag will not be emitted', CLUSTER_TAG)
        return None

    @property
    def hosting_type(self) -> str:
        """Whether this instance is ClickHouse Cloud or self-hosted, cached after the first check run."""
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
        try:
            rows = self.execute_query_raw(CLOUD_MODE_QUERY)
            if not rows or not rows[0]:
                return False
            return str(rows[0][0]) not in ('', '0')
        except Exception as e:
            self.log.debug('Unable to read the cloud_mode setting: %s', e)
            return None

    def _probe_shared_merge_tree(self) -> bool | None:
        """Whether the Cloud-only SharedMergeTree engine exists, or None when the probe failed."""
        try:
            rows = self.execute_query_raw(SHARED_MERGE_TREE_QUERY)
            return bool(rows and rows[0] and int(rows[0][0]) > 0)
        except Exception as e:
            self.log.debug('Unable to check for the SharedMergeTree engine: %s', e)
            return None

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

        For single endpoint mode: Returns clusterAllReplicas('default', system.<table>)
        For direct connection: Returns system.<table>

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
            # Single endpoint mode: Use clusterAllReplicas to query all nodes
            # The cluster name is 'default' for ClickHouse Cloud and most setups
            return f"clusterAllReplicas('default', system.{table_name})"
        else:
            # Direct connection: Query the local system table directly
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
