# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from string import Template
from time import time

import clickhouse_connect
from clickhouse_connect.driver import httputil

from datadog_checks.base import AgentCheck
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.db import QueryManager
from datadog_checks.base.utils.db.utils import TagManager, default_json_event_encoding, resolve_db_host
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
from .utils import ErrorSanitizer

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


# Not user-configurable; controls how often database_instance metadata is emitted.
DATABASE_INSTANCE_COLLECTION_INTERVAL = 300

_VIEW_REFRESHES_QUERY = """\
SELECT
    database,
    view,
    status,
    exception,
    toInt64(toUnixTimestamp(last_success_time)) AS last_refresh_time,
    toInt64(toUnixTimestamp(next_refresh_time)) AS next_refresh_time,
    toInt64(written_rows) AS written_rows,
    toInt64(written_bytes) AS written_bytes
FROM {view_refreshes_table}
"""

_VIEW_REFRESH_STATUS_MAP = {
    'Scheduled': AgentCheck.OK,
    'Running': AgentCheck.OK,
    'WaitingForDependencies': AgentCheck.WARNING,
    'Disabled': AgentCheck.UNKNOWN,
    'Error': AgentCheck.CRITICAL,
}


class ClickhouseCheck(DatabaseCheck):
    __NAMESPACE__ = 'clickhouse'
    SERVICE_CHECK_CONNECT = 'can_connect'
    SERVICE_CHECK_VIEW_REFRESH = 'view.refresh'

    def __init__(self, name, init_config, instances):
        super(ClickhouseCheck, self).__init__(name, init_config, instances)

        config, validation_result = build_config(self)
        self._config = config
        self._validation_result = validation_result

        self.health = ClickhouseHealth(self)

        for warning in validation_result.warnings:
            self.log.warning(warning)

        self._resolved_hostname = None
        self._database_identifier = None
        self._agent_hostname = None
        self._dbms_version = None
        self._database_instance_last_emitted = 0

        self.tag_manager = TagManager()
        self.tag_manager.set_tags_from_list(self._config.tags, replace=True)
        self._add_core_tags()

        self._view_refreshes_unsupported_logged = False
        self._view_refreshes_permission_logged = False
        self._view_refreshes_skip = False

        self._error_sanitizer = ErrorSanitizer(self._config.password)
        self.check_initializations.append(self.validate_config)
        self.check_initializations.append(advanced_queries.warm_cache)
        self._submit_config_health_event()
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

        self._init_dbm_components()

    def _init_dbm_components(self):
        if self._config.dbm and self._config.query_metrics.enabled:
            self.statement_metrics = ClickhouseStatementMetrics(self, self._config.query_metrics)
        else:
            self.statement_metrics = None

        if self._config.dbm and self._config.query_samples.enabled:
            self.statement_samples = ClickhouseStatementSamples(self, self._config.query_samples)
        else:
            self.statement_samples = None

        if self._config.dbm and self._config.query_completions.enabled:
            self.query_completions = ClickhouseQueryCompletions(self, self._config.query_completions)
        else:
            self.query_completions = None

        if self._config.dbm and self._config.query_errors.enabled:
            self.query_errors = ClickhouseQueryErrors(self, self._config.query_errors)
        else:
            self.query_errors = None

        if self._config.dbm and self._config.collect_schemas and self._config.collect_schemas.enabled:
            self.metadata = ClickhouseMetadata(self)
        else:
            self.metadata = None

        if self._config.dbm and self._config.schema_metrics and self._config.schema_metrics.enabled:
            self.table_metrics = ClickhouseTableMetrics(self, self._config.schema_metrics)
        else:
            self.table_metrics = None

        if self._config.dbm and self._config.parts_and_merges.enabled:
            self.parts_and_merges = ClickhousePartsAndMerges(self, self._config.parts_and_merges)
        else:
            self.parts_and_merges = None

    @property
    def tags(self) -> list[str]:
        return list(self.tag_manager.get_tags())

    def _add_core_tags(self):
        self.tag_manager.set_tag("server", self._config.server, replace=True)
        self.tag_manager.set_tag("port", str(self._config.port), replace=True)
        self.tag_manager.set_tag("db", self._config.db, replace=True)
        self.tag_manager.set_tag("database_hostname", self.reported_hostname, replace=True)
        self.tag_manager.set_tag("database_instance", self.database_identifier, replace=True)

    def validate_config(self):
        from datadog_checks.base import ConfigurationError

        if not self._validation_result.valid:
            for error in self._validation_result.errors:
                self.log.error(str(error))
            if self._validation_result.errors:
                raise ConfigurationError(str(self._validation_result.errors[0]))

    def _submit_config_health_event(self):
        try:
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
            self.log.debug("Failed to submit config health event: %s", e)

    def _send_database_instance_metadata(self):
        current_time = time()
        if current_time - self._database_instance_last_emitted >= DATABASE_INSTANCE_COLLECTION_INTERVAL:
            try:
                version_result = list(self.execute_query_raw('SELECT version()'))[0][0]
                self._dbms_version = version_result
            except Exception as e:
                self.log.debug("Unable to fetch version for metadata: %s", e)
                self._dbms_version = "unknown"

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
        self._server_version = self.select_version()
        if self._query_manager is None or self._query_manager_version != self._server_version:
            self._query_manager = self._build_query_manager()
            self._query_manager_version = self._server_version
        self._query_manager.execute()
        self.set_version_metadata(self._server_version)
        self._send_database_instance_metadata()

        if self.statement_metrics:
            self.statement_metrics.run_job_loop(self.tags)
        if self.statement_samples:
            self.statement_samples.run_job_loop(self.tags)
        if self.query_completions:
            self.query_completions.run_job_loop(self.tags)
        if self.query_errors:
            self.query_errors.run_job_loop(self.tags)
        if self.metadata:
            self.metadata.run_job_loop(self.tags)
        if self.table_metrics:
            self.table_metrics.run_job_loop(self.tags)
        if self.parts_and_merges:
            self.parts_and_merges.run_job_loop(self.tags)
        if self._config.dbm:
            self._collect_view_refresh_metrics()

    def get_queries(self) -> list[dict]:
        query_list = []

        if self._config.use_legacy_queries:
            query_list.extend(
                [
                    queries.SystemMetrics,
                    queries.SystemEventsToDeprecate,
                    queries.SystemEvents,
                    queries.SystemAsynchronousMetrics,
                    queries.SystemParts,
                    queries.SystemReplicas,
                    queries.SystemDictionaries,
                ]
            )

        if self._config.use_advanced_queries:
            query_list.extend(
                [
                    advanced_queries.SystemMetrics,
                    advanced_queries.SystemEvents,
                    advanced_queries.SystemAsynchronousMetrics,
                ]
            )
            if self.version_ge('21.3'):
                query_list.append(advanced_queries.SystemErrors)

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
    def agent_hostname(self):
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def database_identifier(self) -> str:
        if self._database_identifier is None:
            template = Template(self._config.database_identifier.template)
            tag_dict = {}
            tags = self.tags.copy()
            tags.sort()
            for t in tags:
                if ':' in t:
                    key, value = t.split(':', 1)
                    if key in tag_dict:
                        tag_dict[key] += f",{value}"
                    else:
                        tag_dict[key] = value
            tag_dict['server'] = str(self._config.server)
            tag_dict['port'] = str(self._config.port)
            tag_dict['db'] = str(self._config.db)
            self._database_identifier = template.safe_substitute(**tag_dict)
        return self._database_identifier

    @property
    def dbms(self) -> str:
        return "clickhouse"

    @property
    def dbms_version(self) -> str:
        if self._dbms_version is None:
            return "unknown"
        return self._dbms_version

    @property
    def cloud_metadata(self) -> dict:
        return {}

    @property
    def is_single_endpoint_mode(self):
        return self._config.single_endpoint_mode

    def get_system_table(self, table_name):
        """Return the system table reference, using clusterAllReplicas in single_endpoint_mode."""
        if self._config.single_endpoint_mode:
            return f"clusterAllReplicas('default', system.{table_name})"
        return f"system.{table_name}"

    def _collect_view_refresh_metrics(self) -> None:
        if self._view_refreshes_skip:
            return
        try:
            rows = self.execute_query_raw(
                _VIEW_REFRESHES_QUERY.format(view_refreshes_table=self.get_system_table('view_refreshes'))
            )
        except Exception as e:
            self._handle_view_refreshes_error(e)
            return

        base_tags = list(self.tags)
        seen: set[tuple[str, str]] = set()
        for database, view_name, status, exception, last_time, next_time, written_rows, written_bytes in rows:
            if (database, view_name) in seen:
                continue
            seen.add((database, view_name))
            view_tags = base_tags + [f'db:{database}', f'view:{view_name}']
            sc_status = _VIEW_REFRESH_STATUS_MAP.get(status, AgentCheck.UNKNOWN)
            sc_msg = (exception or '').split('\n')[0] or status
            self.service_check(self.SERVICE_CHECK_VIEW_REFRESH, sc_status, tags=view_tags, message=sc_msg)
            self.gauge('view.refresh.last_time', int(last_time or 0), tags=view_tags)
            self.gauge('view.refresh.next_time', int(next_time or 0), tags=view_tags)
            self.gauge('view.refresh.rows', int(written_rows or 0), tags=view_tags)
            self.gauge('view.refresh.bytes', int(written_bytes or 0), tags=view_tags)

    def _handle_view_refreshes_error(self, e: Exception) -> None:
        lowered = str(e).lower()
        if 'unknown table' in lowered or 'unknowntable' in lowered or 'unknown_table' in lowered:
            if not self._view_refreshes_unsupported_logged:
                self.log.info(
                    "system.view_refreshes not present (ClickHouse < 24.3); refresh status will not be populated."
                )
                self._view_refreshes_unsupported_logged = True
            self._view_refreshes_skip = True
        elif 'not enough privileges' in lowered or 'access_denied' in lowered:
            if not self._view_refreshes_permission_logged:
                self.log.warning(
                    "Agent user lacks SELECT on system.view_refreshes; refresh status will not be populated. "
                    "Grant with: GRANT SELECT ON system.view_refreshes TO <agent_user>"
                )
                self._view_refreshes_permission_logged = True
            self._view_refreshes_skip = True
        else:
            self.log.exception("Unexpected error querying system.view_refreshes")

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
        try:
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
                # https://clickhouse.com/docs/integrations/language-clients/python/advanced-usage#managing-clickhouse-session-ids
                autogenerate_session_id=False,
                settings={},
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
        if self.statement_metrics:
            self.statement_metrics.cancel()
        if self.statement_samples:
            self.statement_samples.cancel()
        if self.query_completions:
            self.query_completions.cancel()
        if self.query_errors:
            self.query_errors.cancel()
        if self.metadata:
            self.metadata.cancel()
        if self.table_metrics:
            self.table_metrics.cancel()
        if self.parts_and_merges:
            self.parts_and_merges.cancel()

        if self.statement_metrics and self.statement_metrics._job_loop_future:
            self.statement_metrics._job_loop_future.result()
        if self.statement_samples and self.statement_samples._job_loop_future:
            self.statement_samples._job_loop_future.result()
        if self.query_completions and self.query_completions._job_loop_future:
            self.query_completions._job_loop_future.result()
        if self.query_errors and self.query_errors._job_loop_future:
            self.query_errors._job_loop_future.result()
        if self.metadata and self.metadata._job_loop_future:
            self.metadata._job_loop_future.result()
        if self.table_metrics and self.table_metrics._job_loop_future:
            self.table_metrics._job_loop_future.result()
        if self.parts_and_merges and self.parts_and_merges._job_loop_future:
            self.parts_and_merges._job_loop_future.result()

        if self._client:
            try:
                self._client.close()
            except Exception as e:
                self.log.debug("Error closing main client: %s", e)
            self._client = None

        self._pool_manager = None

    def version_lt(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is less than the compared version, otherwise False.
        """
        # The `latest` version should always be greater than any other
        if version == 'latest':
            return True

        return utils.parse_version(self._server_version) < utils.parse_version(version)

    def version_ge(self, version: str) -> bool:
        """
        Returns True if the current ClickHouse server version is greater than the compared version, otherwise False.
        """
        # The `latest` version should always be less than any other
        if version == 'latest':
            return False

        return utils.parse_version(self._server_version) >= utils.parse_version(version)
