# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Explicit pre-flight diagnostics for the MySQL integration.

Registered with ``self.diagnosis.register(...)`` in ``MySql.__init__`` and run
on-demand when the agent invokes ``get_diagnoses()`` (triggered by the user via
``datadog-agent diagnose``). The worker opens one short-lived connection per
invocation and probes each documented setup requirement -- connection,
version, GRANTs, performance_schema state, DBM helper objects -- emitting
FAIL/WARNING/SUCCESS rows with remediation pointing at the exact GRANT/CREATE/SET.

Probes are ordered so a cascade-skip set (``self._failed``) can suppress
derivative FAILs that would dog-pile on a single root cause (e.g. once
``performance_schema=OFF`` FAILs, every downstream consumer/instrument/procedure
probe returns early instead of layering on a stack of "you also need X" failures
that won't matter until ``performance_schema`` is enabled and the server is
restarted).
"""

from __future__ import annotations

from contextlib import closing
from enum import Enum
from typing import Any

import pymysql

from .util import DatabaseConfigurationError, connect_with_session_variables
from .version_utils import parse_version

CATEGORY_MYSQL = "mysql"

SETUP_DOCS_URL = "https://docs.datadoghq.com/database_monitoring/setup_mysql/selfhosted/"
TROUBLESHOOTING_DOCS_URL = "https://docs.datadoghq.com/database_monitoring/setup_mysql/troubleshooting/"

MIN_MYSQL_VERSION = (5, 6, 0)
MIN_MARIADB_VERSION = (10, 5, 0)
RECOMMENDED_DIGEST_LENGTH = 4096
RECOMMENDED_SQL_TEXT_LENGTH = 4096

# pymysql error codes we react to.
ER_ACCESS_DENIED = 1045
ER_HOST_NOT_PRIVILEGED = 1130
ER_USER_LIMIT_REACHED = 1226
ER_TABLEACCESS_DENIED = 1142
ER_SPECIFIC_ACCESS_DENIED = 1227
ER_PROCACCESS_DENIED = 1370
ER_SP_DOES_NOT_EXIST = 1305
ER_NO_SUCH_TABLE = 1146
ER_BAD_DB_ERROR = 1049
CR_CONN_HOST_ERROR = 2003
CR_CONNECTION_ERROR = 2002


class MySqlDiagnoseCode(Enum):
    """Diagnose-only error codes for MySQL. Codes that also fire from runtime
    `record_warning` paths live in `util.DatabaseConfigurationError` and are
    reused here so `agent status` and `agent diagnose` report the same code."""

    connection_failure = "connection-failure"
    mysql_version_unsupported = "mysql-version-unsupported"
    missing_grant_process = "missing-grant-process"
    missing_grant_performance_schema_select = "missing-grant-performance-schema-select"
    missing_grant_replication_client = "missing-grant-replication-client"
    missing_grant_innodb_index_stats = "missing-grant-innodb-index-stats"
    missing_grant_schema_select = "missing-grant-schema-select"
    missing_datadog_schema = "missing-datadog-schema"
    missing_execute_on_datadog = "missing-execute-on-datadog"
    enable_events_statements_procedure_missing = "enable-events-statements-procedure-missing"
    performance_schema_digest_too_small = "performance-schema-digest-too-small"
    performance_schema_sql_text_too_small = "performance-schema-sql-text-too-small"


# Inline metadata: description (what the probe checks) + remediation (how to fix it) + docs anchor.
# Kept self-contained here (vs. util.py) because none of these new codes are emitted from runtime paths.
DIAGNOSTIC_METADATA: dict[Any, dict[str, str]] = {
    MySqlDiagnoseCode.connection_failure: {
        "description": "Verifies the Agent can open a MySQL connection with the configured credentials.",
        "remediation": "Verify host/port (or unix socket), user, password, and TLS settings.",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.mysql_version_unsupported: {
        "description": "Verifies the MySQL/MariaDB server version is supported by the integration.",
        "remediation": "Upgrade MySQL to 5.6+ or MariaDB to 10.5+.",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_grant_process: {
        "description": "Verifies the datadog user has PROCESS so it can see other sessions' queries.",
        "remediation": "GRANT PROCESS ON *.* TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_grant_performance_schema_select: {
        "description": "Verifies SELECT on performance_schema.* tables backing DBM and replication.",
        "remediation": "GRANT SELECT ON performance_schema.* TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_grant_replication_client: {
        "description": "Verifies REPLICATION CLIENT so SHOW REPLICA STATUS / SHOW SLAVE STATUS works.",
        "remediation": "GRANT REPLICATION CLIENT ON *.* TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_grant_innodb_index_stats: {
        "description": "Verifies SELECT on mysql.innodb_index_stats for index metrics collection.",
        "remediation": "GRANT SELECT ON mysql.innodb_index_stats TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_grant_schema_select: {
        "description": "Verifies the datadog user can read schemas for schema-collection metadata.",
        "remediation": "GRANT SELECT ON *.* TO datadog@'%'; (or per-database GRANTs covering monitored schemas).",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_datadog_schema: {
        "description": "Verifies the `datadog` schema exists for DBM helper procedures.",
        "remediation": "CREATE SCHEMA IF NOT EXISTS datadog; GRANT EXECUTE ON datadog.* TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.missing_execute_on_datadog: {
        "description": "Verifies the datadog user has EXECUTE on procedures in the `datadog` schema.",
        "remediation": "GRANT EXECUTE ON datadog.* TO datadog@'%';",
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.enable_events_statements_procedure_missing: {
        "description": (
            "Verifies the optional `datadog.enable_events_statements_consumers` procedure exists "
            "so the Agent can enable required consumers at runtime."
        ),
        "remediation": (
            "Create `datadog.enable_events_statements_consumers` per the setup docs, or enable the "
            "events_statements_* consumers manually in performance_schema.setup_consumers."
        ),
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.performance_schema_digest_too_small: {
        "description": "Verifies max_digest_length and performance_schema_max_digest_length are at least 4096.",
        "remediation": (
            "Set max_digest_length=4096 and performance_schema_max_digest_length=4096 in my.cnf and restart."
        ),
        "docs_url": SETUP_DOCS_URL,
    },
    MySqlDiagnoseCode.performance_schema_sql_text_too_small: {
        "description": "Verifies performance_schema_max_sql_text_length is at least 4096 (MySQL 5.7+).",
        "remediation": "Set performance_schema_max_sql_text_length=4096 in my.cnf and restart.",
        "docs_url": SETUP_DOCS_URL,
    },
    DatabaseConfigurationError.performance_schema_not_enabled: {
        "description": "Verifies performance_schema is ON, required by every DBM sub-feature.",
        "remediation": "Set performance_schema=ON in my.cnf and restart MySQL.",
        "docs_url": TROUBLESHOOTING_DOCS_URL,
    },
    DatabaseConfigurationError.events_statements_consumer_missing: {
        "description": (
            "Verifies at least one `events_statements_*` consumer is enabled in "
            "performance_schema.setup_consumers, required for query metrics and samples."
        ),
        "remediation": (
            "UPDATE performance_schema.setup_consumers SET enabled='YES' WHERE name LIKE 'events_statements_%'; "
            "or grant EXECUTE on `datadog.enable_events_statements_consumers` and let the Agent enable them."
        ),
        "docs_url": TROUBLESHOOTING_DOCS_URL,
    },
    DatabaseConfigurationError.events_waits_current_not_enabled: {
        "description": "Verifies the `events_waits_current` consumer is enabled for query activity collection.",
        "remediation": (
            "UPDATE performance_schema.setup_consumers SET enabled='YES' WHERE name='events_waits_current';"
        ),
        "docs_url": TROUBLESHOOTING_DOCS_URL,
    },
    DatabaseConfigurationError.events_statements_time_instrumentation_not_enabled: {
        "description": "Verifies statement instruments have TIMED=YES so durations are recorded.",
        "remediation": ("UPDATE performance_schema.setup_instruments SET timed='YES' WHERE name LIKE 'statement/%';"),
        "docs_url": TROUBLESHOOTING_DOCS_URL,
    },
    DatabaseConfigurationError.explain_plan_fq_procedure_missing: {
        "description": "Verifies the `datadog.explain_statement` procedure exists for execution-plan collection.",
        "remediation": (
            "Create `datadog.explain_statement` (and grant EXECUTE on it to the datadog user) per the setup docs."
        ),
        "docs_url": SETUP_DOCS_URL,
    },
}


def build_remediation(code: Any) -> str:
    """Return the remediation string with the relevant docs URL appended."""
    meta = DIAGNOSTIC_METADATA.get(code, {})
    base = meta.get("remediation", "")
    url = meta.get("docs_url", SETUP_DOCS_URL)
    anchor = code.value if isinstance(code, DatabaseConfigurationError) else ""
    suffix = "{}#{}".format(url, anchor) if anchor and url == TROUBLESHOOTING_DOCS_URL else url
    return "{} See {}.".format(base, suffix) if base else "See {}.".format(suffix)


def run_diagnostics(check: Any) -> None:
    """Entry point for ``Diagnosis.register()``; creates a short-lived worker per invocation."""
    MySqlDiagnose(check)._run()


class MySqlDiagnose:
    """Pre-flight diagnostics for the MySQL integration."""

    def __init__(self, check: Any) -> None:
        self._check = check
        self._failed: set[str] = set()
        self._version: tuple[int, int, int] | None = None
        self._is_mariadb: bool = False

    # -- orchestrator ---------------------------------------------------------

    def _run(self) -> None:
        """Open one probe connection and run every enabled diagnostic."""
        self._failed = set()
        self._version = None
        self._is_mariadb = False

        db = self._open_probe_connection()
        if db is None:
            return
        try:
            self._diagnose_version(db)
            self._diagnose_process_grant(db)
            self._diagnose_performance_schema_select(db)
            if self._needs_replication_probes():
                self._diagnose_replication_client_grant(db)
            if self._needs_performance_schema():
                self._diagnose_performance_schema_enabled(db)
            if self._is_dbm_enabled():
                self._run_dbm_probes(db)
            if self._needs_index_metrics_probes():
                self._diagnose_innodb_index_stats_grant(db)
            if self._needs_schema_collection_probes():
                self._diagnose_information_schema_select(db)
        finally:
            try:
                db.close()
            except Exception:
                pass

    def _run_dbm_probes(self, db: Any) -> None:
        """Cluster-level DBM probes -- consumer state, instrument timing, helper objects."""
        config = self._check._config
        query_samples_enabled = config.statement_samples_config.get("enabled", True)
        query_metrics_enabled = config.statement_metrics_config.get("enabled", True)
        query_activity_enabled = config.activity_config.get("enabled", True)

        # Don't pile failures on top of an OFF performance_schema -- every consumer/instrument
        # probe below would just point at a switch the user already needs to flip.
        if DatabaseConfigurationError.performance_schema_not_enabled.value in self._failed:
            return

        if query_samples_enabled or query_metrics_enabled:
            self._diagnose_events_statements_consumer(db)
            self._diagnose_statement_time_instrumentation(db)
        if query_activity_enabled:
            self._diagnose_events_waits_current_consumer(db)
        if query_metrics_enabled:
            self._diagnose_digest_length(db)
        if query_samples_enabled and not self._is_mariadb and self._mysql_ge((5, 7, 0)):
            self._diagnose_sql_text_length(db)
        if query_samples_enabled:
            datadog_schema_present = self._diagnose_datadog_schema(db)
            if datadog_schema_present:
                self._diagnose_explain_procedure(db)
                self._diagnose_enable_consumers_procedure(db)

    # -- gating helpers -------------------------------------------------------

    def _is_dbm_enabled(self) -> bool:
        return bool(self._check._config.dbm_enabled)

    def _needs_replication_probes(self) -> bool:
        return bool(self._check._config.replication_enabled)

    def _needs_performance_schema(self) -> bool:
        config = self._check._config
        if config.dbm_enabled:
            return True
        return bool(config.options.get("extra_performance_metrics"))

    def _needs_index_metrics_probes(self) -> bool:
        return bool(self._check._config.index_config.get("enabled", False))

    def _needs_schema_collection_probes(self) -> bool:
        return bool(self._check._config.schemas_config.get("enabled", False))

    # -- probes ---------------------------------------------------------------

    def _open_probe_connection(self) -> Any:
        code = MySqlDiagnoseCode.connection_failure
        try:
            connect_args = self._check._get_connection_args()
            db = connect_with_session_variables(**connect_args)
        except pymysql.err.OperationalError as e:
            self._fail(
                code,
                diagnosis="Failed to connect to {host} as {user}: {err}".format(
                    host=self._host_desc(), user=self._user_desc(), err=_describe_operational_error(e)
                ),
                rawerror=str(e),
            )
            return None
        except Exception as e:
            self._fail(
                code,
                diagnosis="Failed to connect to {host} as {user}: {err}".format(
                    host=self._host_desc(), user=self._user_desc(), err=e
                ),
                rawerror=str(e),
            )
            return None
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Connected to {host} as {user}.".format(host=self._host_desc(), user=self._user_desc()),
            category=self._category,
        )
        return db

    def _diagnose_version(self, db: Any) -> None:
        code = MySqlDiagnoseCode.mysql_version_unsupported
        raw, version_comment = _select_version(db)
        if not raw:
            self._fail(code, diagnosis="Unable to determine MySQL version.")
            return
        version_info = parse_version(raw, version_comment)
        self._is_mariadb = version_info.flavor == "MariaDB"
        parsed = _parse_version_tuple(version_info.version)
        if parsed is None:
            self._fail(code, diagnosis="Unable to parse MySQL version {!r}.".format(raw))
            return
        self._version = parsed
        if self._is_mariadb:
            minimum = MIN_MARIADB_VERSION
            label = "MariaDB"
        else:
            minimum = MIN_MYSQL_VERSION
            label = version_info.flavor or "MySQL"
        if parsed < minimum:
            self._fail(
                code,
                diagnosis="{} version {} is below the minimum supported version {}.".format(
                    label, _format_version(parsed), _format_version(minimum)
                ),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} version {} is supported.".format(label, _format_version(parsed)),
            category=self._category,
        )

    def _diagnose_process_grant(self, db: Any) -> None:
        code = MySqlDiagnoseCode.missing_grant_process
        try:
            _execute_read_probe(db, "SELECT 1 FROM information_schema.PROCESSLIST LIMIT 1")
        except pymysql.err.OperationalError as e:
            if _pymysql_errno(e) in (ER_SPECIFIC_ACCESS_DENIED, ER_TABLEACCESS_DENIED):
                self._fail(
                    code,
                    diagnosis="The datadog user lacks PROCESS: {}".format(e),
                    rawerror=str(e),
                )
                return
            # Anything else (e.g. server gone, lock timeout) is not a PROCESS problem -- skip.
            self._check.log.debug("PROCESS grant probe failed with non-permission error: %s", e)
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="PROCESS is granted.",
            category=self._category,
        )

    def _diagnose_performance_schema_select(self, db: Any) -> None:
        code = MySqlDiagnoseCode.missing_grant_performance_schema_select
        try:
            _execute_read_probe(db, "SELECT 1 FROM performance_schema.setup_consumers LIMIT 1")
        except pymysql.err.OperationalError as e:
            errno = _pymysql_errno(e)
            if errno in (ER_TABLEACCESS_DENIED, ER_SPECIFIC_ACCESS_DENIED):
                self._fail(
                    code,
                    diagnosis="The datadog user lacks SELECT on performance_schema.*: {}".format(e),
                    rawerror=str(e),
                )
                return
            if errno == ER_NO_SUCH_TABLE:
                # performance_schema not compiled in / disabled; covered by the perf-schema probe.
                self._check.log.debug("performance_schema not available: %s", e)
                return
            self._check.log.debug("performance_schema SELECT probe failed: %s", e)
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="SELECT on performance_schema.* is granted.",
            category=self._category,
        )

    def _diagnose_performance_schema_enabled(self, db: Any) -> None:
        code = DatabaseConfigurationError.performance_schema_not_enabled
        value = _show_variable(db, "performance_schema")
        if value is None:
            self._check.log.debug("performance_schema variable not present")
            return
        if value.upper() == "ON":
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="performance_schema is ON.",
                category=self._category,
            )
            return
        self._fail(
            code,
            diagnosis="performance_schema is {}; DBM features require it to be ON.".format(value),
        )

    def _diagnose_replication_client_grant(self, db: Any) -> None:
        code = MySqlDiagnoseCode.missing_grant_replication_client
        # Use the version-appropriate keyword: SHOW REPLICA STATUS (8.0+ / MariaDB 10.5+) falls back
        # to SHOW SLAVE STATUS. Both raise 1227 when REPLICATION CLIENT is missing.
        queries = ["SHOW REPLICA STATUS"]
        if self._is_mariadb or not self._mysql_ge((8, 0, 22)):
            queries.append("SHOW SLAVE STATUS")
        last_err: Exception | None = None
        for query in queries:
            try:
                _execute_read_probe(db, query)
            except pymysql.err.OperationalError as e:
                last_err = e
                if _pymysql_errno(e) in (ER_SPECIFIC_ACCESS_DENIED, ER_TABLEACCESS_DENIED):
                    self._fail(
                        code,
                        diagnosis="The datadog user lacks REPLICATION CLIENT: {}".format(e),
                        rawerror=str(e),
                    )
                    return
                # Syntax error on a flavor that doesn't support this keyword -- try the fallback.
                continue
            except Exception as e:
                last_err = e
                continue
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="REPLICATION CLIENT is granted.",
                category=self._category,
            )
            return
        if last_err is not None:
            self._check.log.debug("REPLICATION CLIENT probe inconclusive: %s", last_err)

    def _diagnose_events_statements_consumer(self, db: Any) -> None:
        code = DatabaseConfigurationError.events_statements_consumer_missing
        try:
            rows = _fetchall(
                db,
                "SELECT name, enabled FROM performance_schema.setup_consumers WHERE name LIKE 'events_statements_%'",
            )
        except pymysql.err.OperationalError as e:
            self._check.log.debug("events_statements consumer probe failed: %s", e)
            return
        enabled = [name for name, value in rows if _is_yes(value)]
        if enabled:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="events_statements consumers enabled: {}.".format(", ".join(enabled)),
                category=self._category,
            )
            return
        self._fail(
            code,
            diagnosis=(
                "No events_statements_* consumers are enabled in performance_schema.setup_consumers; "
                "query metrics and samples cannot be collected."
            ),
        )

    def _diagnose_events_waits_current_consumer(self, db: Any) -> None:
        code = DatabaseConfigurationError.events_waits_current_not_enabled
        try:
            rows = _fetchall(
                db,
                "SELECT enabled FROM performance_schema.setup_consumers WHERE name='events_waits_current'",
            )
        except pymysql.err.OperationalError as e:
            self._check.log.debug("events_waits_current probe failed: %s", e)
            return
        if rows and _is_yes(rows[0][0]):
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="events_waits_current is enabled.",
                category=self._category,
            )
            return
        self._fail(
            code,
            diagnosis="events_waits_current is not enabled; query activity wait events cannot be collected.",
        )

    def _diagnose_statement_time_instrumentation(self, db: Any) -> None:
        code = DatabaseConfigurationError.events_statements_time_instrumentation_not_enabled
        try:
            rows = _fetchall(
                db,
                "SELECT COUNT(*) FROM performance_schema.setup_instruments "
                "WHERE name LIKE 'statement/%%' AND timed='YES'",
            )
        except pymysql.err.OperationalError as e:
            self._check.log.debug("statement instrument timing probe failed: %s", e)
            return
        count = rows[0][0] if rows and rows[0] else 0
        if count and int(count) > 0:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="Statement instruments are TIMED.",
                category=self._category,
            )
            return
        self._fail(
            code,
            diagnosis="No `statement/%` instruments have TIMED=YES; statement durations cannot be recorded.",
        )

    def _diagnose_digest_length(self, db: Any) -> None:
        code = MySqlDiagnoseCode.performance_schema_digest_too_small
        max_digest = _to_int(_show_variable(db, "max_digest_length"))
        ps_max_digest = _to_int(_show_variable(db, "performance_schema_max_digest_length"))
        too_small = [
            ("max_digest_length", max_digest),
            ("performance_schema_max_digest_length", ps_max_digest),
        ]
        too_small = [(n, v) for n, v in too_small if v is not None and v < RECOMMENDED_DIGEST_LENGTH]
        if not too_small:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="max_digest_length and performance_schema_max_digest_length are >= {}.".format(
                    RECOMMENDED_DIGEST_LENGTH
                ),
                category=self._category,
            )
            return
        meta = DIAGNOSTIC_METADATA[code]
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis="{} below {}; queries longer than that will be truncated.".format(
                ", ".join("{}={}".format(n, v) for n, v in too_small), RECOMMENDED_DIGEST_LENGTH
            ),
            category=self._category,
            description=meta["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_sql_text_length(self, db: Any) -> None:
        code = MySqlDiagnoseCode.performance_schema_sql_text_too_small
        value = _to_int(_show_variable(db, "performance_schema_max_sql_text_length"))
        if value is None:
            return
        if value >= RECOMMENDED_SQL_TEXT_LENGTH:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="performance_schema_max_sql_text_length = {} (>= {}).".format(
                    value, RECOMMENDED_SQL_TEXT_LENGTH
                ),
                category=self._category,
            )
            return
        meta = DIAGNOSTIC_METADATA[code]
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "performance_schema_max_sql_text_length = {} is below {}; sample query text will be truncated."
            ).format(value, RECOMMENDED_SQL_TEXT_LENGTH),
            category=self._category,
            description=meta["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_datadog_schema(self, db: Any) -> bool:
        """Return True when the schema exists. Caller chains the procedure probes off this."""
        code = MySqlDiagnoseCode.missing_datadog_schema
        try:
            rows = _fetchall(
                db,
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='datadog'",
            )
        except pymysql.err.OperationalError as e:
            self._check.log.debug("datadog schema probe failed: %s", e)
            return False
        if rows:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="`datadog` schema exists.",
                category=self._category,
            )
            return True
        self._fail(
            code,
            diagnosis="`datadog` schema is missing; DBM helper procedures cannot be created or called.",
        )
        return False

    def _diagnose_explain_procedure(self, db: Any) -> None:
        fq_code = DatabaseConfigurationError.explain_plan_fq_procedure_missing
        exec_code = MySqlDiagnoseCode.missing_execute_on_datadog
        explain_procedure = self._check._config.statement_samples_config.get(
            "fully_qualified_explain_procedure", "datadog.explain_statement"
        )
        try:
            with closing(db.cursor()) as cursor:
                cursor.execute("CALL {}(%s)".format(explain_procedure), ("SELECT 1",))
                cursor.fetchall()
                # Some procedures return multiple result sets; drain them so the connection stays clean.
                while cursor.nextset():
                    pass
        except pymysql.err.OperationalError as e:
            errno = _pymysql_errno(e)
            if errno == ER_SP_DOES_NOT_EXIST:
                self._fail(
                    fq_code,
                    diagnosis="Procedure {} does not exist: {}".format(explain_procedure, e),
                    rawerror=str(e),
                )
                return
            if errno == ER_PROCACCESS_DENIED:
                # The procedure exists -- it's an EXECUTE problem.
                self._check.diagnosis.success(
                    name=fq_code.value,
                    diagnosis="Procedure {} exists.".format(explain_procedure),
                    category=self._category,
                )
                self._fail(
                    exec_code,
                    diagnosis="The datadog user lacks EXECUTE on {}: {}".format(explain_procedure, e),
                    rawerror=str(e),
                )
                return
            self._check.log.debug("explain procedure probe failed: %s", e)
            return
        except pymysql.err.ProgrammingError as e:
            self._check.log.debug("explain procedure probe parse error: %s", e)
            return
        self._check.diagnosis.success(
            name=fq_code.value,
            diagnosis="{} is callable.".format(explain_procedure),
            category=self._category,
        )
        self._check.diagnosis.success(
            name=exec_code.value,
            diagnosis="EXECUTE on datadog.* is granted.",
            category=self._category,
        )

    def _diagnose_enable_consumers_procedure(self, db: Any) -> None:
        code = MySqlDiagnoseCode.enable_events_statements_procedure_missing
        procedure = self._check._config.statement_samples_config.get(
            "events_statements_enable_procedure", "datadog.enable_events_statements_consumers"
        )
        try:
            rows = _fetchall(
                db,
                "SELECT 1 FROM information_schema.ROUTINES "
                "WHERE ROUTINE_SCHEMA=%s AND ROUTINE_NAME=%s AND ROUTINE_TYPE='PROCEDURE'",
                _split_procedure(procedure),
            )
        except pymysql.err.OperationalError as e:
            self._check.log.debug("enable_events_statements_consumers probe failed: %s", e)
            return
        if rows:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="{} exists; the Agent can enable required consumers at runtime.".format(procedure),
                category=self._category,
            )
            return
        meta = DIAGNOSTIC_METADATA[code]
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "{} does not exist; the Agent cannot enable required consumers at runtime and they must "
                "be enabled manually in performance_schema.setup_consumers."
            ).format(procedure),
            category=self._category,
            description=meta["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_innodb_index_stats_grant(self, db: Any) -> None:
        code = MySqlDiagnoseCode.missing_grant_innodb_index_stats
        try:
            _execute_read_probe(db, "SELECT 1 FROM mysql.innodb_index_stats LIMIT 1")
        except pymysql.err.OperationalError as e:
            errno = _pymysql_errno(e)
            if errno in (ER_TABLEACCESS_DENIED, ER_SPECIFIC_ACCESS_DENIED):
                self._fail(
                    code,
                    diagnosis="The datadog user lacks SELECT on mysql.innodb_index_stats: {}".format(e),
                    rawerror=str(e),
                )
                return
            if errno == ER_NO_SUCH_TABLE:
                # Older flavors / MariaDB that don't have this table -- nothing to do.
                return
            self._check.log.debug("innodb_index_stats probe failed: %s", e)
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="SELECT on mysql.innodb_index_stats is granted.",
            category=self._category,
        )

    def _diagnose_information_schema_select(self, db: Any) -> None:
        code = MySqlDiagnoseCode.missing_grant_schema_select
        meta = DIAGNOSTIC_METADATA[code]
        try:
            schemas = {
                row[0]
                for row in _fetchall(db, "SHOW DATABASES")
                if row and row[0] not in ("information_schema", "performance_schema", "mysql", "sys")
            }
            readable_rows = _fetchall(
                db,
                "SELECT DISTINCT table_schema FROM information_schema.TABLES "
                "WHERE table_schema NOT IN ('information_schema','performance_schema','mysql','sys')",
            )
            readable = {row[0] for row in readable_rows if row}
        except pymysql.err.OperationalError as e:
            self._check.log.debug("information_schema SELECT probe failed: %s", e)
            return
        missing = sorted(schemas - readable)
        if not missing:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="The datadog user can read every visible non-system schema ({}).".format(len(schemas)),
                category=self._category,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "The datadog user can SHOW but cannot SELECT from {} schema(s): {}; schema collection "
                "will be partial for those."
            ).format(len(missing), ", ".join(missing)),
            category=self._category,
            description=meta["description"],
            remediation=build_remediation(code),
        )

    # -- helpers --------------------------------------------------------------

    def _fail(self, code: Any, diagnosis: str, rawerror: str | None = None) -> None:
        meta = DIAGNOSTIC_METADATA.get(code, {})
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis=diagnosis,
            category=self._category,
            description=meta.get("description"),
            remediation=build_remediation(code),
            rawerror=rawerror,
        )
        self._failed.add(code.value)

    @property
    def _category(self) -> str:
        try:
            identifier = self._check.database_identifier
        except Exception:
            identifier = self._host_desc()
        if len(identifier) > 27:
            identifier = "{}...{}".format(identifier[:12], identifier[-12:])
        return "instance={}".format(identifier)

    def _host_desc(self) -> str:
        config = self._check._config
        if config.defaults_file:
            return "defaults_file={}".format(config.defaults_file)
        if config.mysql_sock:
            return "socket={}".format(config.mysql_sock)
        host = config.host or "localhost"
        return "{}:{}".format(host, config.port) if config.port else host

    def _user_desc(self) -> str:
        return self._check._config.user or "configured authentication"

    def _mysql_ge(self, minimum: tuple[int, int, int]) -> bool:
        return self._version is not None and self._version >= minimum


def _select_version(db: Any) -> tuple[str, str]:
    """Return (raw_version, version_comment). Both empty on failure."""
    try:
        with closing(db.cursor()) as cursor:
            cursor.execute("SELECT VERSION(), @@version_comment")
            row = cursor.fetchone()
    except pymysql.err.OperationalError:
        return "", ""
    if not row:
        return "", ""
    return row[0] or "", row[1] or ""


def _show_variable(db: Any, name: str) -> str | None:
    try:
        with closing(db.cursor()) as cursor:
            cursor.execute("SHOW GLOBAL VARIABLES LIKE %s", (name,))
            row = cursor.fetchone()
    except pymysql.err.OperationalError:
        return None
    if not row:
        return None
    return row[1]


def _fetchall(db: Any, sql: str, params: tuple[Any, ...] | None = None) -> list[Any]:
    with closing(db.cursor()) as cursor:
        if params is None:
            cursor.execute(sql)
        else:
            cursor.execute(sql, params)
        return list(cursor.fetchall())


def _execute_read_probe(db: Any, sql: str) -> None:
    with closing(db.cursor()) as cursor:
        cursor.execute(sql)
        cursor.fetchall()


def _pymysql_errno(e: Exception) -> int | None:
    args = getattr(e, "args", None)
    if args and isinstance(args[0], int):
        return args[0]
    return None


def _describe_operational_error(e: pymysql.err.OperationalError) -> str:
    errno = _pymysql_errno(e)
    if errno == ER_ACCESS_DENIED:
        return "access denied (check username/password): {}".format(e)
    if errno == CR_CONN_HOST_ERROR:
        return "host unreachable: {}".format(e)
    if errno == CR_CONNECTION_ERROR:
        return "socket unreachable: {}".format(e)
    if errno == ER_HOST_NOT_PRIVILEGED:
        return "host not allowed to connect: {}".format(e)
    if errno == ER_USER_LIMIT_REACHED:
        return "user connection limit reached: {}".format(e)
    if errno == ER_BAD_DB_ERROR:
        return "unknown database: {}".format(e)
    return str(e)


def _parse_version_tuple(version: str) -> tuple[int, int, int] | None:
    if not version:
        return None
    parts = version.split(".")
    if len(parts) < 2:
        return None
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch_token = parts[2] if len(parts) >= 3 else "0"
        patch = int("".join(ch for ch in patch_token if ch.isdigit()) or "0")
    except ValueError:
        return None
    return (major, minor, patch)


def _format_version(version: tuple[int, int, int]) -> str:
    return "{}.{}.{}".format(*version)


def _is_yes(value: Any) -> bool:
    if value is None:
        return False
    return str(value).strip().upper() == "YES"


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _split_procedure(name: str) -> tuple[str, str]:
    """Split a `[schema.]name` procedure reference into (schema, name)."""
    if "." in name:
        schema, proc = name.split(".", 1)
        return schema, proc
    return "datadog", name
