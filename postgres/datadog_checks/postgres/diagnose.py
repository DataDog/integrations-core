# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Explicit pre-flight diagnostics for the Postgres integration.

Registered with ``self.diagnosis.register(...)`` in ``PostgreSql.__init__`` and run
on-demand when the agent invokes ``get_diagnoses()`` (triggered by the user via
``datadog-agent diagnose``). Each diagnostic opens its own short-lived
connection so a poisoned diagnostic session does not evict the persistent pool.

Caveats:
    - Diagnostics can only run after ``PostgreSql.__init__`` succeeds. Errors
      that keep the check from constructing (invalid instance config, Pydantic
      validation failures) surface via ``log.error`` and the initialization
      health event instead.
"""

import psycopg

from datadog_checks.postgres.connection_pool import TokenAwareConnection

from .util import (
    DIAGNOSTIC_METADATA,
    DatabaseConfigurationError,
    build_remediation,
)
from .version_utils import V9_6, VersionUtils

CATEGORY_CONNECTION = "connection"
CATEGORY_SERVER_CONFIG = "server-config"
CATEGORY_PRIVILEGES = "privileges"
CATEGORY_DBM = "dbm"

# Recommended minimum track_activity_query_size. Default Postgres value is 1024, which
# silently truncates queries and breaks explain plan collection.
RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE = 4096


class PostgresDiagnose:
    """Explicit pre-flight diagnostics for `datadog-agent diagnose`."""

    def __init__(self, check):
        self._check = check

    # -- registration ---------------------------------------------------------

    def register(self):
        """Register diagnostic entry points with the check's Diagnosis object.

        A single orchestrator per category keeps the output tidy: if one category
        fails catastrophically, the others still report.
        """
        d = self._check.diagnosis
        d.register(
            self._run_connection_and_server_diagnostics,
            self._run_dbm_diagnostics,
        )

    # -- orchestrators --------------------------------------------------------

    def _run_connection_and_server_diagnostics(self):
        """Open a connection and run every diagnostic that doesn't depend on DBM."""
        conn = self._open_probe_connection(self._check._config.dbname)
        if conn is None:
            return
        try:
            self._diagnose_version(conn)
            self._diagnose_shared_preload_libraries(conn)
            self._diagnose_track_activity_query_size(conn)
            self._diagnose_track_io_timing(conn)
            self._diagnose_pg_stat_statements_max(conn)
            self._diagnose_pg_monitor_role(conn)
            self._diagnose_pg_stat_activity_access(conn)
        finally:
            _safe_close(conn)

    def _run_dbm_diagnostics(self):
        """Run DBM-only pre-flight checks against the main dbname."""
        if not self._check._config.dbm:
            return
        conn = self._open_probe_connection(self._check._config.dbname)
        if conn is None:
            return
        try:
            self._diagnose_datadog_schema(conn)
            self._diagnose_pg_stat_statements_extension(conn)
            self._diagnose_pg_stat_statements_readable(conn)
            self._diagnose_explain_function(conn)
        finally:
            _safe_close(conn)

    # -- diagnostics ----------------------------------------------------------

    def _open_probe_connection(self, dbname):
        """Open a short-lived diagnostic connection. Records the connection diagnosis.

        Returns the open connection on success, or None on failure.
        """
        conn_args = self._check.build_connection_args()
        kwargs = conn_args.as_kwargs(dbname=dbname)
        token_provider = self._check.db_pool.token_provider
        if token_provider:
            kwargs["token_provider"] = token_provider
        host_desc = self._host_desc()
        username = self._check._config.username
        try:
            conn = TokenAwareConnection.connect(**kwargs)
        except psycopg.Error as e:
            code = DatabaseConfigurationError.connection_failure
            self._check.diagnosis.fail(
                name=code.value,
                diagnosis="Failed to connect to {host} (dbname={db}) as {user}: {err}".format(
                    host=host_desc, db=dbname, user=username, err=e
                ),
                category=CATEGORY_CONNECTION,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
                rawerror=str(e),
            )
            return None
        self._check.diagnosis.success(
            name=DatabaseConfigurationError.connection_failure.value,
            diagnosis="Connected to {host} (dbname={db}) as {user}".format(host=host_desc, db=dbname, user=username),
            category=CATEGORY_CONNECTION,
        )
        return conn

    def _diagnose_version(self, conn):
        code = DatabaseConfigurationError.postgres_version_unsupported
        try:
            raw_version = _fetchone(conn, "SHOW SERVER_VERSION")[0]
            version = VersionUtils.parse_version(raw_version)
        except Exception as e:
            self._check.diagnosis.fail(
                name=code.value,
                diagnosis="Unable to determine Postgres version: {}".format(e),
                category=CATEGORY_SERVER_CONFIG,
                rawerror=str(e),
            )
            return
        if version < V9_6:
            self._check.diagnosis.fail(
                name=code.value,
                diagnosis="Postgres version {} is below the minimum supported version (9.6).".format(raw_version),
                category=CATEGORY_SERVER_CONFIG,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Postgres version {} is supported.".format(raw_version),
            category=CATEGORY_SERVER_CONFIG,
        )

    def _diagnose_shared_preload_libraries(self, conn):
        code = DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements
        libs, read_ok = _show(conn, "shared_preload_libraries")
        if not read_ok:
            # shared_preload_libraries is GUC_SUPERUSER_ONLY: its pg_settings row is hidden from
            # users who are not members of pg_monitor. Don't silently drop the diagnostic --
            # surface a WARNING that points at the likely root cause.
            self._check.diagnosis.warning(
                name=code.value,
                diagnosis=(
                    "Could not read shared_preload_libraries; this setting is restricted to "
                    "pg_monitor members. Grant pg_monitor to the datadog user so this "
                    "diagnostic can run."
                ),
                category=CATEGORY_SERVER_CONFIG,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(DatabaseConfigurationError.missing_pg_monitor_role),
            )
            return
        entries = [part.strip() for part in libs.split(",") if part.strip()]
        if "pg_stat_statements" in entries:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="shared_preload_libraries contains pg_stat_statements.",
                category=CATEGORY_SERVER_CONFIG,
            )
            return
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis=(
                "shared_preload_libraries = '{}' does not contain pg_stat_statements; DBM query metrics "
                "will not be collected until the server is restarted with it loaded."
            ).format(libs),
            category=CATEGORY_SERVER_CONFIG,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_track_activity_query_size(self, conn):
        code = DatabaseConfigurationError.track_activity_query_size_too_small
        raw, read_ok = _show(conn, "track_activity_query_size")
        if not read_ok:
            return
        try:
            size = int(raw)
        except (TypeError, ValueError):
            return
        if size >= RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="track_activity_query_size = {} (>= {}).".format(size, RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE),
                category=CATEGORY_SERVER_CONFIG,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "track_activity_query_size = {} is below the recommended {}; long queries will be "
                "truncated and may not be explainable."
            ).format(size, RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE),
            category=CATEGORY_SERVER_CONFIG,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_track_io_timing(self, conn):
        code = DatabaseConfigurationError.track_io_timing_disabled
        raw, read_ok = _show(conn, "track_io_timing")
        if not read_ok:
            return
        if raw == "on":
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="track_io_timing is on.",
                category=CATEGORY_SERVER_CONFIG,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis="track_io_timing = {}; I/O timing columns will not be collected.".format(raw),
            category=CATEGORY_SERVER_CONFIG,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_stat_statements_max(self, conn):
        code = DatabaseConfigurationError.high_pg_stat_statements_max
        raw, read_ok = _show(conn, "pg_stat_statements.max")
        if not read_ok:
            # Not configured, extension not loaded, or restricted from the datadog user
            # -- the shared_preload_libraries / pg_monitor diagnostics report the root cause.
            return
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return
        threshold = self._check._config.query_metrics.pg_stat_statements_max_warning_threshold
        if value <= threshold:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="pg_stat_statements.max = {} (<= threshold {}).".format(value, threshold),
                category=CATEGORY_SERVER_CONFIG,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "pg_stat_statements.max = {} exceeds the threshold of {}; the collection query may run slowly."
            ).format(value, threshold),
            category=CATEGORY_SERVER_CONFIG,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_monitor_role(self, conn):
        # pg_monitor only exists on PG >= 10.
        code = DatabaseConfigurationError.missing_pg_monitor_role
        row = _fetchone(
            conn,
            "SELECT 1 FROM pg_roles WHERE rolname = 'pg_monitor'",
        )
        if row is None:
            # PG < 10 has no pg_monitor role — the version diagnostic handles unsupported versions.
            return
        has_role = _fetchone(
            conn,
            "SELECT pg_has_role(current_user, 'pg_monitor', 'MEMBER')",
        )
        if has_role and has_role[0]:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="Current user is a member of pg_monitor.",
                category=CATEGORY_PRIVILEGES,
            )
            return
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis=(
                "The datadog user is not a member of pg_monitor; other users' activity and statement "
                "metrics will be invisible."
            ),
            category=CATEGORY_PRIVILEGES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_stat_activity_access(self, conn):
        code = DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity
        view = self._check._config.pg_stat_activity_view
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM {} WHERE query = %s".format(_safe_identifier(view)),
                    ('<insufficient privilege>',),
                )
                masked = cursor.fetchone()[0]
        except psycopg.Error as e:
            self._check.diagnosis.fail(
                name=DatabaseConfigurationError.undefined_activity_view.value,
                diagnosis="Unable to query {}: {}".format(view, e),
                category=CATEGORY_PRIVILEGES,
                description=DIAGNOSTIC_METADATA[DatabaseConfigurationError.undefined_activity_view]["description"],
                remediation=build_remediation(DatabaseConfigurationError.undefined_activity_view),
                rawerror=str(e),
            )
            return
        if masked:
            self._check.diagnosis.warning(
                name=code.value,
                diagnosis=(
                    "{} rows in {} are masked as '<insufficient privilege>'; activity samples will miss "
                    "other users' queries."
                ).format(masked, view),
                category=CATEGORY_PRIVILEGES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} is readable with full query visibility.".format(view),
            category=CATEGORY_PRIVILEGES,
        )

    def _diagnose_datadog_schema(self, conn):
        code = DatabaseConfigurationError.missing_datadog_schema
        row = _fetchone(
            conn,
            "SELECT 1 FROM pg_namespace WHERE nspname = 'datadog'",
        )
        if row:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="`datadog` schema exists in {}.".format(self._check._config.dbname),
                category=CATEGORY_DBM,
            )
            return
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis="`datadog` schema is missing in {}; DBM setup is incomplete.".format(self._check._config.dbname),
            category=CATEGORY_DBM,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_stat_statements_extension(self, conn):
        created = DatabaseConfigurationError.pg_stat_statements_not_created
        row = _fetchone(
            conn,
            "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'",
        )
        if row:
            self._check.diagnosis.success(
                name=created.value,
                diagnosis="pg_stat_statements extension is installed in {}.".format(self._check._config.dbname),
                category=CATEGORY_DBM,
            )
            return
        self._check.diagnosis.fail(
            name=created.value,
            diagnosis="pg_stat_statements extension is not installed in {}.".format(self._check._config.dbname),
            category=CATEGORY_DBM,
            description=DIAGNOSTIC_METADATA[created]["description"],
            remediation=build_remediation(created),
        )

    def _diagnose_pg_stat_statements_readable(self, conn):
        code = DatabaseConfigurationError.pg_stat_statements_not_readable
        view = self._check._config.pg_stat_statements_view
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM {} LIMIT 1".format(_safe_identifier(view)))
                cursor.fetchall()
        except psycopg.errors.UndefinedTable as e:
            # Extension is not CREATEd — the extension diagnostic reports this; don't double up.
            self._check.log.debug("pg_stat_statements not readable (not created): %s", e)
            return
        except psycopg.errors.ObjectNotInPrerequisiteState as e:
            # shared_preload_libraries missing — the shared_preload_libraries diagnostic reports this.
            self._check.log.debug("pg_stat_statements not readable (not loaded): %s", e)
            return
        except psycopg.Error as e:
            self._check.diagnosis.fail(
                name=code.value,
                diagnosis="Unable to SELECT from {} in {}: {}".format(view, self._check._config.dbname, e),
                category=CATEGORY_DBM,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
                rawerror=str(e),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} is readable in {}.".format(view, self._check._config.dbname),
            category=CATEGORY_DBM,
        )

    def _diagnose_explain_function(self, conn):
        code = DatabaseConfigurationError.undefined_explain_function
        explain_function = self._check._config.query_samples.explain_function
        schema, name = _split_function(explain_function)
        row = _fetchone(
            conn,
            (
                "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = %s AND p.proname = %s"
            ),
            (schema, name),
        )
        if row:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="{} exists in {}.".format(explain_function, self._check._config.dbname),
                category=CATEGORY_DBM,
            )
            return
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis="{} is not defined in {}; execution plans cannot be collected.".format(
                explain_function, self._check._config.dbname
            ),
            category=CATEGORY_DBM,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    # -- helpers --------------------------------------------------------------

    def _host_desc(self):
        host = self._check._config.host or "localhost"
        port = self._check._config.port
        return "{}:{}".format(host, port) if port else host


def _fetchone(conn, sql, params=None):
    """Run a single-row query, swallowing psycopg errors and returning None on failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params) if params is not None else cursor.execute(sql)
            return cursor.fetchone()
    except psycopg.Error:
        return None


def _show(conn, setting):
    """Look up a GUC in pg_settings.

    Returns (value, read_ok):
      - (value, True)  -- row returned, setting visible
      - (None,  False) -- no row (undefined GUC, or hidden from non-pg_monitor users for
                          ``GUC_SUPERUSER_ONLY`` settings like ``shared_preload_libraries``)
    """
    row = _fetchone(conn, "SELECT setting FROM pg_settings WHERE name = %s", (setting,))
    if not row:
        return None, False
    return row[0], True


def _safe_close(conn):
    try:
        conn.close()
    except Exception:
        pass


def _safe_identifier(name):
    """Return a quoted schema-qualified identifier, or pass through an empty-arg function call.

    The view/function name comes from user config; we only accept either:
      - a [schema.]identifier of word chars (e.g. ``pg_stat_activity``, ``datadog.pg_stat_statements``)
      - the same with a trailing ``()`` for function-call form (e.g. ``datadog.pg_stat_activity()``)
    to avoid SQL injection via `{}`.format.
    """
    if not name:
        raise ValueError("identifier is empty")
    is_call = name.endswith("()")
    bare = name[:-2] if is_call else name
    parts = bare.split(".")
    if len(parts) > 2:
        raise ValueError("identifier has too many dots: {!r}".format(name))
    for part in parts:
        if not part or not all(c.isalnum() or c == "_" for c in part):
            raise ValueError("invalid identifier: {!r}".format(name))
    quoted = ".".join('"{}"'.format(part) for part in parts)
    return quoted + "()" if is_call else quoted


def _split_function(name):
    """Split a possibly schema-qualified function name into (schema, name).

    Defaults the schema to ``public`` when unqualified, matching Postgres' behavior.
    """
    if not name:
        return "public", ""
    parts = name.split(".", 1)
    if len(parts) == 1:
        return "public", parts[0]
    return parts[0], parts[1]
