# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Explicit pre-flight diagnostics for the SQL Server integration.

Registered with ``self.diagnosis.register(...)`` in ``SQLServer.__init__`` and
run on-demand when the Agent invokes ``get_diagnoses()``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from datadog_checks.base import is_affirmative
from datadog_checks.sqlserver.connection_errors import SQLConnectionError
from datadog_checks.sqlserver.const import ENGINE_EDITION_SQL_DATABASE, STATIC_INFO_ENGINE_EDITION

CATEGORY_SQLSERVER = "sqlserver"
KEY_PREFIX = "sqlserver-diagnose-"
MIN_SUPPORTED_MAJOR_VERSION = 11
SQLSERVER_2014_MAJOR_VERSION = 12

SQLSERVER_SETUP_DOCS_URL = "https://docs.datadoghq.com/integrations/sql-server/?tab=host#setup"
SQLSERVER_DBM_GRANTS_DOCS_URL = (
    "https://docs.datadoghq.com/database_monitoring/setup_sql_server/selfhosted/"
    "?tab=sqlserver2014#grant-the-agent-access"
)


class SQLServerConfigurationError(Enum):
    """SQL Server diagnostic error codes."""

    connection_failure = "connection-failure"
    sqlserver_version_unsupported = "sqlserver-version-unsupported"
    performance_counters_not_readable = "performance-counters-not-readable"
    missing_view_server_state = "missing-view-server-state"
    missing_connect_any_database = "missing-connect-any-database"
    missing_view_any_definition = "missing-view-any-definition"
    missing_msdb_select = "missing-msdb-select"


DIAGNOSTIC_METADATA = {
    SQLServerConfigurationError.connection_failure: {
        "description": "Verifies that the Agent can connect to the configured SQL Server database.",
        "remediation": "Review the SQL Server host, port, driver, authentication, and TLS settings.",
        "docs_url": SQLSERVER_SETUP_DOCS_URL,
    },
    SQLServerConfigurationError.sqlserver_version_unsupported: {
        "description": "Verifies that SQL Server is a supported version for the integration.",
        "remediation": "Use SQL Server 2012 or newer.",
        "docs_url": SQLSERVER_SETUP_DOCS_URL,
    },
    SQLServerConfigurationError.performance_counters_not_readable: {
        "description": "Verifies read access to sys.dm_os_performance_counters.",
        "remediation": "Grant SELECT on sys.dm_os_performance_counters to the Datadog login.",
        "docs_url": SQLSERVER_SETUP_DOCS_URL,
    },
    SQLServerConfigurationError.missing_view_server_state: {
        "description": (
            "Verifies VIEW SERVER STATE (or VIEW DATABASE STATE on Azure SQL Database) for server state, "
            "query metrics, and query activity collection."
        ),
        "remediation": "Grant VIEW SERVER STATE (or VIEW DATABASE STATE on Azure SQL Database) to the Datadog login.",
        "docs_url": SQLSERVER_SETUP_DOCS_URL,
    },
    SQLServerConfigurationError.missing_connect_any_database: {
        "description": "Verifies CONNECT ANY DATABASE when the check can fan out across databases.",
        "remediation": "Grant CONNECT ANY DATABASE to the Datadog login.",
        "docs_url": SQLSERVER_DBM_GRANTS_DOCS_URL,
    },
    SQLServerConfigurationError.missing_view_any_definition: {
        "description": "Verifies VIEW ANY DEFINITION for DBM metadata and definition-dependent metrics.",
        "remediation": "Grant VIEW ANY DEFINITION to the Datadog login.",
        "docs_url": SQLSERVER_DBM_GRANTS_DOCS_URL,
    },
    SQLServerConfigurationError.missing_msdb_select: {
        "description": "Verifies read access to enabled SQL Server features backed by msdb tables.",
        "remediation": "Create the Datadog user in msdb and grant SELECT on the required msdb tables.",
        "docs_url": SQLSERVER_SETUP_DOCS_URL,
    },
}


def build_remediation(code: SQLServerConfigurationError) -> str:
    """Return remediation text with the relevant Datadog docs URL."""
    metadata = DIAGNOSTIC_METADATA[code]
    return "{} See {}.".format(metadata["remediation"], metadata["docs_url"])


def run_diagnostics(check: Any) -> None:
    """Entry point for ``Diagnosis.register()``; creates a short-lived worker per invocation."""
    SqlserverDiagnose(check)._run()


class SqlserverDiagnose:
    """Explicit pre-flight diagnostics for `datadog-agent diagnose`."""

    def __init__(self, check: Any) -> None:
        self._check = check
        self._failed: set[str] = set()
        self._major_version: int | None = None
        self._engine_edition: int | None = None
        self._is_rds: bool | None = None

    def _run(self) -> None:
        """Open one probe connection and run enabled diagnostics."""
        self._failed = set()
        self._major_version = None
        self._engine_edition = None
        self._is_rds = None

        try:
            with self._check.connection.open_managed_default_connection(KEY_PREFIX):
                with self._check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
                    self._diagnose_connection()
                    self._diagnose_version(cursor)
                    if self._needs_performance_counters():
                        self._diagnose_performance_counters(cursor)
                    if self._needs_view_server_state():
                        self._diagnose_view_server_state(cursor)
                    if self._needs_connect_any_database():
                        self._diagnose_connect_any_database(cursor)
                    if self._needs_view_any_definition():
                        self._diagnose_view_any_definition(cursor)
                    if self._needs_msdb_select():
                        self._detect_rds(cursor)
                        self._diagnose_msdb_select(cursor)
        except SQLConnectionError as e:
            code = SQLServerConfigurationError.connection_failure
            self._fail(
                code,
                diagnosis="Failed to connect to {} as {}: {}".format(self._database_desc(), self._username_desc(), e),
                rawerror=str(e),
            )

    def _diagnose_connection(self) -> None:
        code = SQLServerConfigurationError.connection_failure
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Connected to {} as {}.".format(self._database_desc(), self._username_desc()),
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_version(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.sqlserver_version_unsupported
        try:
            row = _fetchone(
                cursor,
                "SELECT CAST(SERVERPROPERTY('ProductMajorVersion') AS INT), "
                "CAST(SERVERPROPERTY('EngineEdition') AS INT)",
            )
            self._major_version = _to_int(row[0]) if row else None
            self._engine_edition = _to_int(row[1]) if row and len(row) > 1 else None
        except Exception as e:
            self._fail(code, diagnosis="Unable to determine SQL Server version: {}".format(e), rawerror=str(e))
            return

        if self._major_version is None:
            self._fail(code, diagnosis="Unable to determine SQL Server major version.")
            return

        if self._major_version < MIN_SUPPORTED_MAJOR_VERSION:
            self._fail(
                code,
                diagnosis="SQL Server major version {} is below the minimum supported version (11).".format(
                    self._major_version
                ),
            )
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="SQL Server major version {} is supported.".format(self._major_version),
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_performance_counters(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.performance_counters_not_readable
        try:
            _execute_read_probe(cursor, "SELECT TOP 1 object_name FROM sys.dm_os_performance_counters")
        except Exception as e:
            self._fail(
                code,
                diagnosis="Unable to read sys.dm_os_performance_counters: {}".format(e),
                rawerror=str(e),
            )
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="sys.dm_os_performance_counters is readable.",
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_view_server_state(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.missing_view_server_state
        azure = self._is_azure_sql_database()
        permission_label = "VIEW DATABASE STATE" if azure else "VIEW SERVER STATE"
        try:
            if azure:
                if not _has_database_permission(cursor, "VIEW DATABASE STATE"):
                    self._fail(
                        code,
                        diagnosis="The Datadog login does not have VIEW DATABASE STATE on the current database.",
                    )
                    return
            elif not _has_server_permission(cursor, "VIEW SERVER STATE"):
                self._fail(code, diagnosis="The Datadog login does not have VIEW SERVER STATE.")
                return
            _execute_read_probe(cursor, "SELECT TOP 1 session_id FROM sys.dm_exec_sessions")
        except Exception as e:
            self._fail(
                code,
                diagnosis="Unable to validate {} with sys.dm_exec_sessions: {}".format(permission_label, e),
                rawerror=str(e),
            )
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} is granted and sys.dm_exec_sessions is readable.".format(permission_label),
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_connect_any_database(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.missing_connect_any_database
        if self._major_version is not None and self._major_version < SQLSERVER_2014_MAJOR_VERSION:
            self._check.diagnosis.warning(
                name=code.value,
                diagnosis=(
                    "CONNECT ANY DATABASE is unavailable before SQL Server 2014; ensure the Datadog user exists "
                    "in every monitored database."
                ),
                category=CATEGORY_SQLSERVER,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
            )
            return

        try:
            if not _has_server_permission(cursor, "CONNECT ANY DATABASE"):
                self._fail(code, diagnosis="The Datadog login does not have CONNECT ANY DATABASE.")
                return
        except Exception as e:
            self._fail(code, diagnosis="Unable to validate CONNECT ANY DATABASE: {}".format(e), rawerror=str(e))
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="CONNECT ANY DATABASE is granted.",
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_view_any_definition(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.missing_view_any_definition
        try:
            if not _has_server_permission(cursor, "VIEW ANY DEFINITION"):
                self._fail(code, diagnosis="The Datadog login does not have VIEW ANY DEFINITION.")
                return
        except Exception as e:
            self._fail(code, diagnosis="Unable to validate VIEW ANY DEFINITION: {}".format(e), rawerror=str(e))
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="VIEW ANY DEFINITION is granted.",
            category=CATEGORY_SQLSERVER,
        )

    def _diagnose_msdb_select(self, cursor: Any) -> None:
        code = SQLServerConfigurationError.missing_msdb_select
        failures = []
        probes = self._msdb_probe_queries()
        for table, query in probes:
            try:
                _execute_read_probe(cursor, query)
            except Exception as e:
                failures.append("{}: {}".format(table, e))

        if failures:
            self._fail(
                code,
                diagnosis="Unable to read required msdb tables: {}".format("; ".join(failures)),
                rawerror="; ".join(failures),
            )
            return

        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Required msdb tables are readable: {}.".format(", ".join(table for table, _ in probes)),
            category=CATEGORY_SQLSERVER,
        )

    def _needs_performance_counters(self) -> bool:
        return not self._check._config.only_custom_queries

    def _needs_view_server_state(self) -> bool:
        config = self._check._config
        return not config.only_custom_queries or config.dbm_enabled

    def _needs_connect_any_database(self) -> bool:
        return not self._is_azure_sql_database() and (
            self._check._config.dbm_enabled or self._check._config.autodiscovery
        )

    def _needs_view_any_definition(self) -> bool:
        config = self._check._config
        database_metrics = config.database_metrics_config
        if self._is_azure_sql_database():
            return False
        if config.dbm_enabled:
            return True
        if config.only_custom_queries:
            return False
        return database_metrics["ao_metrics"]["enabled"] or database_metrics["master_files_metrics"]["enabled"]

    def _needs_msdb_select(self) -> bool:
        if self._is_azure_sql_database():
            return False
        if self._agent_jobs_enabled():
            return True

        config = self._check._config
        if config.only_custom_queries:
            return False

        database_metrics = config.database_metrics_config
        return (
            database_metrics["db_backup_metrics"]["enabled"]
            or database_metrics["primary_log_shipping_metrics"]["enabled"]
            or database_metrics["secondary_log_shipping_metrics"]["enabled"]
        )

    def _msdb_probe_queries(self) -> list[tuple[str, str]]:
        config = self._check._config
        database_metrics = config.database_metrics_config
        probes = []
        if not config.only_custom_queries:
            if database_metrics["db_backup_metrics"]["enabled"]:
                probes.append(("msdb.dbo.backupset", "SELECT TOP 1 1 FROM msdb.dbo.backupset"))
            if database_metrics["primary_log_shipping_metrics"]["enabled"]:
                probes.append(
                    (
                        "msdb.dbo.log_shipping_monitor_primary",
                        "SELECT TOP 1 1 FROM msdb.dbo.log_shipping_monitor_primary",
                    )
                )
            if database_metrics["secondary_log_shipping_metrics"]["enabled"]:
                probes.append(
                    (
                        "msdb.dbo.log_shipping_monitor_secondary",
                        "SELECT TOP 1 1 FROM msdb.dbo.log_shipping_monitor_secondary",
                    )
                )
        if self._agent_jobs_enabled():
            probes.extend(
                [
                    ("msdb.dbo.sysjobs", "SELECT TOP 1 1 FROM msdb.dbo.sysjobs"),
                    ("msdb.dbo.sysjobhistory", "SELECT TOP 1 1 FROM msdb.dbo.sysjobhistory"),
                    ("msdb.dbo.sysjobactivity", "SELECT TOP 1 1 FROM msdb.dbo.sysjobactivity"),
                ]
            )
            if not self._is_rds:
                probes.append(("msdb.dbo.syssessions", "SELECT TOP 1 1 FROM msdb.dbo.syssessions"))
        return probes

    def _agent_jobs_enabled(self) -> bool:
        config = self._check._config
        return config.dbm_enabled and is_affirmative(config.agent_jobs_config.get('enabled', False))

    def _is_azure_sql_database(self) -> bool:
        engine_edition = self._engine_edition or self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        return engine_edition == ENGINE_EDITION_SQL_DATABASE

    def _detect_rds(self, cursor: Any) -> None:
        try:
            row = _fetchone(cursor, "SELECT name FROM sys.databases WHERE name = 'rdsadmin'")
        except Exception:
            self._is_rds = False
            return
        self._is_rds = bool(row)

    def _fail(self, code: SQLServerConfigurationError, diagnosis: str, rawerror: str | None = None) -> None:
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis=diagnosis,
            category=CATEGORY_SQLSERVER,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
            rawerror=rawerror,
        )
        self._failed.add(code.value)

    def _database_desc(self) -> str:
        connection = self._check.connection
        database = self._check.instance.get('database', connection.DEFAULT_DATABASE)
        return "{} (database={})".format(connection.get_host_with_port(), database)

    def _username_desc(self) -> str:
        return self._check.instance.get('username') or "configured authentication"


def _has_server_permission(cursor: Any, permission: str) -> bool:
    row = _fetchone(cursor, "SELECT HAS_PERMS_BY_NAME(NULL, NULL, ?)", (permission,))
    return bool(row and row[0] == 1)


def _has_database_permission(cursor: Any, permission: str) -> bool:
    # NULL securable targets the current database. Passing DB_NAME() instead would
    # be parsed by HAS_PERMS_BY_NAME as a multipart identifier, which returns 0
    # for Azure SQL databases whose names contain a dot.
    row = _fetchone(cursor, "SELECT HAS_PERMS_BY_NAME(NULL, 'DATABASE', ?)", (permission,))
    return bool(row and row[0] == 1)


def _fetchone(cursor: Any, query: str, params: tuple[Any, ...] | None = None) -> Any:
    if params is None:
        cursor.execute(query)
    else:
        cursor.execute(query, params)
    return cursor.fetchone()


def _execute_read_probe(cursor: Any, query: str) -> None:
    cursor.execute(query)
    cursor.fetchall()


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
