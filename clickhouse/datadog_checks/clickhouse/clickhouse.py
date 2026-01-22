# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time

import clickhouse_connect
from cachetools import TTLCache
from clickhouse_connect.driver import httputil

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.base.utils.db.utils import TagManager, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from . import queries
from .__about__ import __version__
from .completed_query_samples import ClickhouseCompletedQuerySamples
from .config import build_config
from .statement_activity import ClickhouseStatementActivity
from .statements import ClickhouseStatementMetrics
from .utils import ErrorSanitizer

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


# Database instance collection interval in seconds (not user-configurable)
DATABASE_INSTANCE_COLLECTION_INTERVAL = 300


class ClickhouseCheck(DatabaseCheck):
    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        # Build typed configuration
        config, validation_result = build_config(self)
        self._config = config
        self._validation_result = validation_result

        # Log validation warnings (errors will be raised in validate_config)
        for warning in validation_result.warnings:
            self.log.warning(warning)

        # DBM-related properties (computed lazily)
        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None
        self._dbms_version = None

        # _database_instance_emitted: limit the collection and transmission of the database instance metadata
        self._database_instance_emitted = TTLCache(
            maxsize=1,
            ttl=DATABASE_INSTANCE_COLLECTION_INTERVAL,
        )

        # Initialize TagManager for tag management (similar to MySQL)
        self.tag_manager = TagManager()
        self.tag_manager.set_tags_from_list(self._config.tags, replace=True)
        self._add_core_tags()

        self._error_sanitizer = ErrorSanitizer(self._config.password)
        self.check_initializations.append(self.validate_config)

        # We'll connect on the first check run
        self._client = None

        # Shared HTTP connection pool for all ClickHouse clients (main + DBM jobs)
        # This reduces connection overhead while maintaining client isolation
        # See: https://clickhouse.com/docs/integrations/language-clients/python/advanced-usage#customizing-the-http-connection-pool
        self._pool_manager = httputil.get_pool_manager(maxsize=8, num_pools=4)

        self._query_manager = QueryManager(
            self,
            self.execute_query_raw,
            queries=[
                queries.SystemMetrics,
                queries.SystemEventsToDeprecate,
                queries.SystemEvents,
                queries.SystemAsynchronousMetrics,
                queries.SystemParts,
                queries.SystemReplicas,
                queries.SystemDictionaries,
            ],
            tags=self.tags,
            error_handler=self._error_sanitizer.clean,
        )
        self.check_initializations.append(self._query_manager.compile_queries)

        # Initialize DBM components if enabled
        self._init_dbm_components()

    def _init_dbm_components(self):
        """Initialize DBM components based on typed configuration."""
        # Initialize query metrics (from system.query_log - analogous to pg_stat_statements)
        if self._config.dbm and self._config.query_metrics.enabled:
            self.statement_metrics = ClickhouseStatementMetrics(self, self._config.query_metrics)
        else:
            self.statement_metrics = None

        # Initialize query activity (from system.processes - analogous to pg_stat_activity)
        if self._config.dbm and self._config.query_activity.enabled:
            self.statement_activity = ClickhouseStatementActivity(self, self._config.query_activity)
        else:
            self.statement_activity = None

        # Initialize completed query samples (from system.query_log - completed queries)
        if self._config.dbm and self._config.completed_query_samples.enabled:
            self.completed_query_samples = ClickhouseCompletedQuerySamples(self, self._config.completed_query_samples)
        else:
            self.completed_query_samples = None

    @property
    def tags(self) -> list[str]:
        """Return the current list of tags from the TagManager."""
        return list(self.tag_manager.get_tags())

    def _add_core_tags(self):
        """
        Add tags that should be attached to every metric/event.
        These are core identification tags for the ClickHouse instance.
        """
        self.tag_manager.set_tag("server", self._config.server, replace=True)
        self.tag_manager.set_tag("port", str(self._config.port), replace=True)
        self.tag_manager.set_tag("db", self._config.db, replace=True)
        self.tag_manager.set_tag("database_hostname", self.reported_hostname, replace=True)
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

    def _send_database_instance_metadata(self):
        """Send database instance metadata to the metadata intake."""
        if self.database_identifier not in self._database_instance_emitted:
            # Get the version for the metadata (and cache it)
            try:
                version_result = list(self.execute_query_raw('SELECT version()'))[0][0]
                self._dbms_version = version_result
            except Exception as e:
                self.log.debug("Unable to fetch version for metadata: %s", e)
                self._dbms_version = "unknown"

            # Get tags without db: prefix for metadata
            tags_no_db = [t for t in self.tags if not t.startswith('db:')]

            event = {
                "host": self.reported_hostname,
                "port": self._config.port,
                "database_instance": self.database_identifier,
                "database_hostname": self.reported_hostname,
                "agent_version": datadog_agent.get_version(),
                "ddagenthostname": self.agent_hostname,
                "dbms": "clickhouse",
                "kind": "database_instance",
                "collection_interval": DATABASE_INSTANCE_COLLECTION_INTERVAL,
                "dbms_version": self._dbms_version,
                "integration_version": __version__,
                "tags": tags_no_db,
                "timestamp": time() * 1000,
                "metadata": {
                    "dbm": self._config.dbm,
                    "connection_host": self._config.server,
                },
            }

            self._database_instance_emitted[self.database_identifier] = event
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

    def check(self, _):
        self.connect()
        self._query_manager.execute()
        self.collect_version()

        # Send database instance metadata
        self._send_database_instance_metadata()

        # Run query metrics collection if DBM is enabled (from system.query_log)
        if self.statement_metrics:
            self.statement_metrics.run_job_loop(self.tags)

        # Run query activity collection if DBM is enabled (from system.processes)
        if self.statement_activity:
            self.statement_activity.run_job_loop(self.tags)

        # Run completed query samples if DBM is enabled (from system.query_log)
        if self.completed_query_samples:
            self.completed_query_samples.run_job_loop(self.tags)

    @AgentCheck.metadata_entrypoint
    def collect_version(self):
        version = list(self.execute_query_raw('SELECT version()'))[0][0]

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
        """
        Get the hostname to be reported in metrics and events.
        """
        if self._resolved_hostname is None:
            self._resolved_hostname = self._config.server
        return self._resolved_hostname

    @property
    def agent_hostname(self):
        """Get the agent hostname."""
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def database_identifier(self) -> str:
        """
        Get a unique identifier for this database instance.
        """
        if self._database_identifier is None:
            # Create a unique identifier based on server, port, and database name
            self._database_identifier = "{}:{}:{}".format(self._config.server, self._config.port, self._config.db)
        return self._database_identifier

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

    def cancel(self):
        """
        Cancel DBM async jobs and clean up connections.
        This is called when the check is being shut down.
        """
        self.log.debug("Cancelling ClickHouse check and cleaning up connections")

        # Cancel DBM async jobs
        if self.statement_metrics:
            self.statement_metrics.cancel()
        if self.statement_activity:
            self.statement_activity.cancel()
        if self.completed_query_samples:
            self.completed_query_samples.cancel()

        # Wait for job loops to finish
        if self.statement_metrics and self.statement_metrics._job_loop_future:
            self.statement_metrics._job_loop_future.result()
        if self.statement_activity and self.statement_activity._job_loop_future:
            self.statement_activity._job_loop_future.result()
        if self.completed_query_samples and self.completed_query_samples._job_loop_future:
            self.completed_query_samples._job_loop_future.result()

        # Close main client
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                self.log.debug("Error closing main client: %s", e)
            self._client = None

        # Clear the shared pool manager
        # Note: urllib3 pool connections are automatically closed when idle
        self._pool_manager = None
