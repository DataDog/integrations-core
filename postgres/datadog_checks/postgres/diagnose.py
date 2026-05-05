# (C) Datadog, Inc. 2026-present
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

from .util import (
    DIAGNOSTIC_METADATA,
    DatabaseConfigurationError,
    build_description,
    build_remediation,
    parse_shared_preload_libraries,
)
from .version_utils import V9_6, VersionUtils

CATEGORY_POSTGRES = "postgres"

# Recommended minimum track_activity_query_size. Default Postgres value is 1024, which
# silently truncates queries and breaks explain plan collection.
RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE = 4096


class PostgresDiagnose:
    """Explicit pre-flight diagnostics for `datadog-agent diagnose`."""

    def __init__(self, check):
        self._check = check
        # Codes that have FAIL'd in the current explicit run. Used for cascade skipping so we
        # don't emit downstream-effect FAILs with nonsensical remediations (e.g. "CREATE EXTENSION"
        # when shared_preload_libraries is empty). Reset at the top of the first orchestrator.
        self._failed = set()

    # -- registration ---------------------------------------------------------

    def register(self):
        """Register the diagnostic entry point with the check's Diagnosis object.

        Idempotent: re-invoking `register` on the same Diagnosis object is a no-op.
        ``Diagnosis.register`` extends an internal list, so without this guard a
        repeated call would stack the entry point and produce N× the diagnostics.
        """
        d = self._check.diagnosis
        if getattr(d, '_postgres_diagnostics_registered', False):
            return
        d._postgres_diagnostics_registered = True
        d.register(self._run)

    # -- orchestrator ---------------------------------------------------------

    def _run(self):
        """Single entry point: open one probe connection and run every diagnostic.

        A single orchestrator means a single `connection-failure` row per run
        for the main DB (vs. one per orchestrator when the dbname matches).
        Feature-specific probes are gated on the subfeatures that actually
        consume each dependency: a query-activity-only setup (``dbm: true``
        with query_metrics/query_samples disabled) should not be flagged
        unhealthy for a missing pg_stat_statements or explain function it
        will never call.

        Per-database probing runs whenever the running check connects to
        databases beyond the main one -- either because autodiscovery is on
        (relation/function/count metrics fan out across discovered DBs) or
        because DBM+query_samples needs the datadog schema and explain
        function on each sampled DB. For autodiscovery without DBM the loop
        body is empty: validating connectivity is the work, and
        ``_open_probe_connection`` records that diagnostic on its own.

        ``_diagnose_config_validation`` always runs, even when the probe
        connection cannot be opened -- it only reads in-memory state from
        ``build_config``.
        """
        self._failed = set()
        main_conn = self._open_probe_connection(self._check._config.dbname)
        try:
            if main_conn is not None:
                self._diagnose_version(main_conn)
                self._diagnose_pg_monitor_role(main_conn)
                self._diagnose_pg_stat_database_access(main_conn)
                if self._uses_pg_stat_activity():
                    self._diagnose_pg_stat_activity_access(main_conn)
                if self._check._config.dbm:
                    self._run_main_dbm_probes(main_conn)
                if self._needs_per_database_probing():
                    self._run_per_database_probes(main_conn)
        finally:
            if main_conn is not None:
                _safe_close(main_conn)
            self._diagnose_config_validation()

    def _run_main_dbm_probes(self, conn):
        """Cluster-level DBM probes that only need the main connection."""
        query_metrics = self._check._config.query_metrics.enabled
        query_samples = self._check._config.query_samples.enabled
        # track_activity_query_size backs pg_stat_activity's query column, used by
        # both query_samples (for explain) and query_activity.
        if query_samples or self._check._config.query_activity.enabled:
            self._diagnose_track_activity_query_size(conn)
        # Cluster-level GUCs -- run once on the main connection. Keep SPL first so the
        # pg_stat_statements extension/readable probes can cascade-skip off the global FAIL.
        if query_metrics:
            self._diagnose_shared_preload_libraries(conn)
            self._diagnose_track_io_timing(conn)
            self._diagnose_pg_stat_statements_max(conn)
            failed = set()
            self._diagnose_pg_stat_statements_extension(conn, self._check._config.dbname, failed)
            self._diagnose_pg_stat_statements_readable(conn, self._check._config.dbname, failed)

    def _needs_per_database_probing(self):
        """True when the running check fans out connections across multiple DBs."""
        return self._needs_autodiscovery_connectivity_probing() or self._needs_query_sample_setup_probing()

    def _needs_autodiscovery_connectivity_probing(self):
        """True when runtime autodiscovery opens per-database connections."""
        config = self._check._config
        return config.database_autodiscovery.enabled and self._check.autodiscovery is not None

    def _needs_query_sample_setup_probing(self):
        """True when DBM query samples can explain statements from multiple databases."""
        config = self._check._config
        return config.dbm and config.query_samples.enabled

    def _run_per_database_probes(self, main_conn):
        """Run per-database probes along the same fan-out paths as runtime collection."""
        if self._needs_autodiscovery_connectivity_probing():
            self._run_autodiscovery_connectivity_probes(main_conn)
        if self._needs_query_sample_setup_probing():
            self._run_query_sample_setup_probes(main_conn)

    def _run_autodiscovery_connectivity_probes(self, main_conn):
        """Validate connectivity to databases selected by runtime autodiscovery."""
        dbnames = self._get_autodiscovered_probe_databases()
        if dbnames is None:
            dbnames = self._get_pg_database_probe_databases(main_conn)
        for dbname in dbnames:
            probe_conn = self._probe_connection_for_db(main_conn, dbname)
            if probe_conn is not None and probe_conn is not main_conn:
                _safe_close(probe_conn)

    def _run_query_sample_setup_probes(self, main_conn):
        """Validate DBM query-sample prerequisites in every database samples can reference."""
        for dbname in self._get_query_sample_probe_databases(main_conn):
            probe_conn = self._probe_connection_for_db(main_conn, dbname)
            if probe_conn is None:
                continue
            try:
                failed = set()
                explain_schema, _ = _split_function(self._check._config.query_samples.explain_function)
                schemas = ["datadog", "public"]
                if explain_schema and explain_schema not in schemas:
                    schemas.append(explain_schema)
                self._diagnose_datadog_schema(probe_conn, dbname, failed)
                for schema in schemas:
                    self._diagnose_schema_usage(probe_conn, dbname, schema, failed)
                self._diagnose_explain_function(probe_conn, dbname, failed)
            finally:
                if probe_conn is not main_conn:
                    _safe_close(probe_conn)

    def _probe_connection_for_db(self, main_conn, dbname):
        """Return the main probe connection or open one for another database."""
        return main_conn if dbname == self._check._config.dbname else self._open_probe_connection(dbname)

    # -- diagnostics ----------------------------------------------------------

    def _fail(self, code, diagnosis, category, description=None, remediation=None, rawerror=None, failed_codes=None):
        """Emit a FAIL and record the code so dependent diagnostics can cascade-skip."""
        self._check.diagnosis.fail(
            name=code.value,
            diagnosis=diagnosis,
            category=category,
            description=description,
            remediation=remediation,
            rawerror=rawerror,
        )
        if failed_codes is None:
            failed_codes = self._failed
        failed_codes.add(code.value)

    def _open_probe_connection(self, dbname):
        """Open a short-lived diagnostic connection. Records the connection diagnosis.

        Returns the open connection on success, or None on failure.
        """
        host_desc = self._host_desc()
        username = self._check._config.username
        conn = None
        try:
            conn = self._check._new_connection(dbname)
        except psycopg.Error as e:
            if conn is not None:
                _safe_close(conn)
            code = DatabaseConfigurationError.connection_failure
            self._fail(
                code,
                diagnosis="Failed to connect to {host} (dbname={db}) as {user}: {err}".format(
                    host=host_desc, db=dbname, user=username, err=e
                ),
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
                rawerror=str(e),
            )
            return None
        self._check.diagnosis.success(
            name=DatabaseConfigurationError.connection_failure.value,
            diagnosis="Connected to {host} (dbname={db}) as {user}".format(host=host_desc, db=dbname, user=username),
            category=CATEGORY_POSTGRES,
        )
        return conn

    def _diagnose_version(self, conn):
        code = DatabaseConfigurationError.postgres_version_unsupported
        try:
            raw_version = _fetchone(conn, "SHOW SERVER_VERSION")[0]
            version = VersionUtils.parse_version(raw_version)
        except Exception as e:
            self._fail(
                code,
                diagnosis="Unable to determine Postgres version: {}".format(e),
                category=CATEGORY_POSTGRES,
                rawerror=str(e),
            )
            return
        if version < V9_6:
            self._fail(
                code,
                diagnosis="Postgres version {} is below the minimum supported version (9.6).".format(raw_version),
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="Postgres version {} is supported.".format(raw_version),
            category=CATEGORY_POSTGRES,
        )

    def _diagnose_shared_preload_libraries(self, conn):
        code = DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements
        libs, read_ok = _get_pg_setting(conn, "shared_preload_libraries")
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
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(DatabaseConfigurationError.missing_pg_monitor_role),
            )
            return
        if "pg_stat_statements" in parse_shared_preload_libraries(libs):
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="shared_preload_libraries contains pg_stat_statements.",
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            code,
            diagnosis=(
                "shared_preload_libraries = '{}' does not contain pg_stat_statements; DBM query metrics "
                "will not be collected until the server is restarted with it loaded."
            ).format(libs),
            category=CATEGORY_POSTGRES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_track_activity_query_size(self, conn):
        code = DatabaseConfigurationError.track_activity_query_size_too_small
        raw, read_ok = _get_pg_setting(conn, "track_activity_query_size")
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
                category=CATEGORY_POSTGRES,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "track_activity_query_size = {} is below the recommended {}; long queries will be "
                "truncated and may not be explainable."
            ).format(size, RECOMMENDED_TRACK_ACTIVITY_QUERY_SIZE),
            category=CATEGORY_POSTGRES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_track_io_timing(self, conn):
        code = DatabaseConfigurationError.track_io_timing_disabled
        raw, read_ok = _get_pg_setting(conn, "track_io_timing")
        if not read_ok:
            return
        if raw == "on":
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="track_io_timing is on.",
                category=CATEGORY_POSTGRES,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis="track_io_timing = {}; I/O timing columns will not be collected.".format(raw),
            category=CATEGORY_POSTGRES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_stat_statements_max(self, conn):
        code = DatabaseConfigurationError.high_pg_stat_statements_max
        raw, read_ok = _get_pg_setting(conn, "pg_stat_statements.max")
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
                category=CATEGORY_POSTGRES,
            )
            return
        self._check.diagnosis.warning(
            name=code.value,
            diagnosis=(
                "pg_stat_statements.max = {} exceeds the threshold of {}; the collection query may run slowly."
            ).format(value, threshold),
            category=CATEGORY_POSTGRES,
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
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            code,
            diagnosis=("The datadog user is not a member of pg_monitor; other users' activity rows will be masked."),
            category=CATEGORY_POSTGRES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
        )

    def _diagnose_pg_stat_activity_access(self, conn):
        code = DatabaseConfigurationError.insufficient_privilege_on_pg_stat_activity
        if DatabaseConfigurationError.missing_pg_monitor_role.value in self._failed:
            # Without pg_monitor, rows are masked -- the pg_monitor FAIL is the actionable item.
            return
        view = self._check._config.pg_stat_activity_view
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT count(*) FROM {} WHERE query = %s".format(_safe_identifier(view)),
                    ('<insufficient privilege>',),
                )
                masked = cursor.fetchone()[0]
        except psycopg.Error as e:
            self._fail(
                DatabaseConfigurationError.undefined_activity_view,
                diagnosis="Unable to query {}: {}".format(view, e),
                category=CATEGORY_POSTGRES,
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
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} is readable with full query visibility.".format(view),
            category=CATEGORY_POSTGRES,
        )

    def _diagnose_pg_stat_database_access(self, conn):
        """Verify the datadog user can SELECT from pg_stat_database.

        ``pg_stat_database`` backs the deadlock, conflict, and connection metrics queried on
        every check run, regardless of feature flags. ``pg_monitor`` grants this transitively,
        but a direct ``GRANT SELECT`` is also a valid (narrower) setup -- so probe the actual
        SELECT instead of inferring from role membership.
        """
        code = DatabaseConfigurationError.pg_stat_database_not_readable
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_stat_database LIMIT 1")
                cursor.fetchall()
        except psycopg.Error as e:
            self._fail(
                code,
                diagnosis="Unable to SELECT from pg_stat_database: {}".format(e),
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=build_remediation(code),
                rawerror=str(e),
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="pg_stat_database is readable.",
            category=CATEGORY_POSTGRES,
        )

    def _diagnose_datadog_schema(self, conn, dbname=None, failed=None):
        code = DatabaseConfigurationError.missing_datadog_schema
        dbname = dbname or self._check._config.dbname
        failed = self._failed if failed is None else failed
        schema, _ = _split_function(self._check._config.query_samples.explain_function)
        # Only run when the user has explicitly qualified the function with `datadog.`.
        # For any other schema -- or an unqualified name resolved via search_path --
        # `_diagnose_explain_function` validates the function directly, which implicitly
        # proves its schema exists.
        if schema != "datadog":
            return
        if _schema_exists(conn, "datadog"):
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="`datadog` schema exists in {}.".format(dbname),
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            code,
            diagnosis="`datadog` schema is missing in {}; DBM setup is incomplete.".format(dbname),
            category=CATEGORY_POSTGRES,
            description=DIAGNOSTIC_METADATA[code]["description"],
            remediation=build_remediation(code),
            failed_codes=failed,
        )

    def _diagnose_schema_usage(self, conn, dbname, schema, failed):
        """Verify the datadog user has USAGE on `schema` in `dbname`.

        Catalog joins (used by ``_diagnose_explain_function``) succeed even when USAGE is denied,
        so the runtime ``SELECT datadog.explain_statement(...)`` can still fail with
        ``permission denied for schema <schema>``. Probe USAGE explicitly per-database to surface
        the missing GRANT before the customer hits it in production.
        """
        code = DatabaseConfigurationError.missing_schema_usage_grant
        if schema == "datadog":
            explain_schema, _ = _split_function(self._check._config.query_samples.explain_function)
            if not _schema_exists(conn, schema):
                if (
                    explain_schema == "datadog"
                    and DatabaseConfigurationError.missing_datadog_schema.value not in failed
                ):
                    self._diagnose_datadog_schema(conn, dbname, failed)
                return
            if explain_schema == "datadog" and DatabaseConfigurationError.missing_datadog_schema.value in failed:
                return
        row = _fetchone(
            conn,
            "SELECT has_schema_privilege(current_user, %s, 'USAGE')",
            (schema,),
        )
        # `has_schema_privilege` returns NULL for a nonexistent schema; treat that as a FAIL too,
        # since the schema-existence probe will already point at the root cause.
        if row and row[0]:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="datadog has USAGE on schema `{}` in {}.".format(schema, dbname),
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            code,
            diagnosis="datadog is missing USAGE on schema `{}` in {}.".format(schema, dbname),
            category=CATEGORY_POSTGRES,
            description=build_description(code, schema=schema),
            remediation=build_remediation(code, schema=schema),
            failed_codes=failed,
        )
        failed.add(_schema_usage_failed_key(schema))

    def _diagnose_pg_stat_statements_extension(self, conn, dbname=None, failed=None):
        created = DatabaseConfigurationError.pg_stat_statements_not_created
        spl = DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements
        dbname = dbname or self._check._config.dbname
        failed = self._failed if failed is None else failed
        # SPL is cluster-level, so the global FAIL is recorded in `self._failed`.
        if spl.value in self._failed:
            # `CREATE EXTENSION` requires SPL -- emitting this FAIL would just point the user at
            # a command that will fail until they fix SPL and restart.
            return
        row = _get_extension_schema(conn, "pg_stat_statements")
        if row:
            self._check.diagnosis.success(
                name=created.value,
                diagnosis="pg_stat_statements extension is installed in schema `{}` in {}.".format(row, dbname),
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            created,
            diagnosis="pg_stat_statements extension is not installed in {}.".format(dbname),
            category=CATEGORY_POSTGRES,
            description=build_description(created, dbname=dbname),
            remediation=build_remediation(created, dbname=dbname),
            failed_codes=failed,
        )

    def _diagnose_pg_stat_statements_readable(self, conn, dbname=None, failed=None):
        code = DatabaseConfigurationError.pg_stat_statements_not_readable
        spl = DatabaseConfigurationError.shared_preload_libraries_missing_pg_stat_statements
        created = DatabaseConfigurationError.pg_stat_statements_not_created
        dbname = dbname or self._check._config.dbname
        failed = self._failed if failed is None else failed
        # SPL is cluster-level (self._failed); extension creation is per-DB (the per-DB `failed`).
        if spl.value in self._failed or created.value in failed:
            # No extension means no view to read; root cause already reported.
            return
        view = self._check._config.pg_stat_statements_view
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM {} LIMIT 1".format(_safe_identifier(view)))
                cursor.fetchall()
        except psycopg.errors.ObjectNotInPrerequisiteState as e:
            # Fallback: SPL diagnostic didn't fire -- don't double up.
            self._check.log.debug("pg_stat_statements not readable (not loaded): %s", e)
            return
        except psycopg.Error as e:
            extension_schema = _get_extension_schema(conn, "pg_stat_statements")
            diagnosis = "Unable to SELECT from {} in {}: {}".format(view, dbname, e)
            remediation = build_remediation(code)
            if "." not in view and extension_schema:
                diagnosis = (
                    "pg_stat_statements extension is installed in schema `{schema}` in {db}, but `{view}` "
                    "is not resolvable from the current search_path: {err}"
                ).format(schema=extension_schema, db=dbname, view=view, err=e)
                remediation = (
                    "Set `pg_stat_statements_view: {schema}.{view}` in the Postgres integration configuration "
                    "or add `{schema}` to the datadog user's search_path. {base}"
                ).format(schema=extension_schema, view=view, base=remediation)
            self._fail(
                code,
                diagnosis=diagnosis,
                category=CATEGORY_POSTGRES,
                description=DIAGNOSTIC_METADATA[code]["description"],
                remediation=remediation,
                rawerror=str(e),
                failed_codes=failed,
            )
            return
        self._check.diagnosis.success(
            name=code.value,
            diagnosis="{} is readable in {}.".format(view, dbname),
            category=CATEGORY_POSTGRES,
        )

    def _diagnose_explain_function(self, conn, dbname=None, failed=None):
        code = DatabaseConfigurationError.undefined_explain_function
        dbname = dbname or self._check._config.dbname
        failed = self._failed if failed is None else failed
        explain_function = self._check._config.query_samples.explain_function
        schema, _ = _split_function(explain_function)
        if schema == "datadog" and not _schema_exists(conn, schema):
            if DatabaseConfigurationError.missing_datadog_schema.value not in failed:
                self._diagnose_datadog_schema(conn, dbname, failed)
            return
        if schema and _schema_usage_failed_key(schema) in failed:
            # The validation call would only duplicate the missing GRANT failure for this function's schema.
            return

        try:
            with conn.cursor() as cursor:
                # Strip a trailing "()" from config — _safe_identifier re-appends it,
                # but we supply our own argument list, so "foo()(%s)" would be a syntax error.
                fn_name = explain_function[:-2] if explain_function.endswith("()") else explain_function
                cursor.execute(
                    "SELECT {}(%s)".format(_safe_identifier(fn_name)),
                    ("SELECT * FROM pg_stat_activity",),
                )
                row = cursor.fetchone()
        except (ValueError, psycopg.Error) as e:
            self._fail(
                code,
                diagnosis="{} cannot be executed in {}; execution plans cannot be collected: {}".format(
                    explain_function, dbname, e
                ),
                category=CATEGORY_POSTGRES,
                description=build_description(code, explain_function=explain_function),
                remediation=build_remediation(code, explain_function=explain_function),
                rawerror=str(e),
                failed_codes=failed,
            )
            return

        if _explain_result_has_plan(row):
            self._check.diagnosis.success(
                name=code.value,
                diagnosis="{} executed successfully in {}.".format(explain_function, dbname),
                category=CATEGORY_POSTGRES,
            )
            return
        self._fail(
            code,
            diagnosis="{} did not return an execution plan in {}; execution plans cannot be collected.".format(
                explain_function, dbname
            ),
            category=CATEGORY_POSTGRES,
            description=build_description(code, explain_function=explain_function),
            remediation=build_remediation(code, explain_function=explain_function),
            failed_codes=failed,
        )

    def _diagnose_config_validation(self):
        """Report the check's config-validation state to `agent diagnose`.

        Reads ``self._check._validation_result`` populated by ``build_config`` during
        ``__init__``. That same object also feeds the ``dbm-health`` event, but the
        user-facing strings emitted here must NOT mention the event or any other
        downstream surface -- this diagnostic stands on its own as a postgres
        config-validation probe.
        """
        code = DatabaseConfigurationError.config_validation
        vr = getattr(self._check, "_validation_result", None)
        if vr is None:
            self._check.diagnosis.warning(
                name=code.value,
                diagnosis="Postgres config validation did not complete (check initialization failed).",
                category=CATEGORY_POSTGRES,
            )
            return

        errors = list(vr.errors or [])
        warnings = list(vr.warnings or [])
        features = list(vr.features or [])
        diagnosis_line = "Postgres config validation: {} error(s), {} warning(s).".format(len(errors), len(warnings))

        if not errors and not warnings:
            self._check.diagnosis.success(
                name=code.value,
                diagnosis=diagnosis_line,
                category=CATEGORY_POSTGRES,
            )
            return

        body_lines = []
        if errors:
            body_lines.append("Errors:")
            body_lines.extend("  - {}".format(err) for err in errors)
        if warnings:
            body_lines.append("Warnings:")
            body_lines.extend("  - {}".format(w) for w in warnings)
        if features:
            enabled = [f["key"].value for f in features if f.get("enabled")]
            disabled = [f["key"].value for f in features if not f.get("enabled")]
            body_lines.append("Features enabled: {}".format(", ".join(enabled) or "none"))
            body_lines.append("Features disabled: {}".format(", ".join(disabled) or "none"))
        description = "\n".join(body_lines)

        remediation = (
            "Resolve the errors and warnings listed above by editing the Postgres integration configuration "
            "for this instance, then restart the agent."
        )

        method = self._check.diagnosis.fail if errors else self._check.diagnosis.warning
        method(
            name=code.value,
            diagnosis=diagnosis_line,
            category=CATEGORY_POSTGRES,
            description=description,
            remediation=remediation,
        )

    # -- helpers --------------------------------------------------------------

    def _host_desc(self):
        host = self._check._config.host or "localhost"
        port = self._check._config.port
        return "{}:{}".format(host, port) if port else host

    def _uses_pg_stat_activity(self):
        config = self._check._config
        return config.collect_activity_metrics or (
            config.dbm and (config.query_samples.enabled or config.query_activity.enabled)
        )

    def _get_query_sample_probe_databases(self, conn):
        # dbstrict only applies to query-sample pg_stat_activity filters. Runtime autodiscovery
        # still opens the databases it selected, and that connectivity is probed separately.
        if self._check._config.dbstrict:
            return [self._check._config.dbname]

        # Query samples read pg_stat_activity from the main DB and later explain each sampled row
        # by its datname. That runtime path applies dbstrict/ignore_databases, not autodiscovery
        # include/exclude, so enumerate pg_database for DBM setup probes.
        return self._get_pg_database_probe_databases(conn)

    def _get_autodiscovered_probe_databases(self):
        if self._check._config.database_autodiscovery.enabled and self._check.autodiscovery is not None:
            try:
                dbs = self._check.autodiscovery.get_items()
            except Exception as e:
                self._check.log.debug(
                    "diagnose: autodiscovery.get_items() failed; falling back to pg_database enumeration: %s", e
                )
                return None
            return dbs
        return None

    def _get_pg_database_probe_databases(self, conn):
        sql = "SELECT datname FROM pg_catalog.pg_database WHERE datistemplate = false AND datallowconn"
        params = ()
        if self._check._config.ignore_databases:
            sql += " AND " + " AND ".join("datname NOT ILIKE %s" for _ in self._check._config.ignore_databases)
            params = tuple(self._check._config.ignore_databases)

        rows = _fetchall(conn, sql, params if params else None)
        if not rows:
            return [self._check._config.dbname]

        dbnames = []
        seen = set()
        for row in rows:
            if not row or not row[0] or row[0] in seen:
                continue
            dbnames.append(row[0])
            seen.add(row[0])
        return dbnames or [self._check._config.dbname]


def _fetchone(conn, sql, params=None):
    """Run a single-row query, swallowing psycopg errors and returning None on failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params) if params is not None else cursor.execute(sql)
            return cursor.fetchone()
    except psycopg.Error:
        return None


def _fetchall(conn, sql, params=None):
    """Run a query, swallowing psycopg errors and returning None on failure."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params) if params is not None else cursor.execute(sql)
            return cursor.fetchall()
    except psycopg.Error:
        return None


def _get_pg_setting(conn, setting):
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


def _schema_exists(conn, schema):
    """Return whether a schema exists in the current database."""
    row = _fetchone(conn, "SELECT 1 FROM pg_namespace WHERE nspname = %s", (schema,))
    return bool(row)


def _get_extension_schema(conn, extension_name):
    """Return the schema an extension is installed into, or None when absent."""
    row = _fetchone(
        conn,
        """
        SELECT n.nspname
        FROM pg_extension e
        JOIN pg_namespace n ON n.oid = e.extnamespace
        WHERE e.extname = %s
        """,
        (extension_name,),
    )
    if not row:
        return None
    return row[0]


def _schema_usage_failed_key(schema):
    return "{}:{}".format(DatabaseConfigurationError.missing_schema_usage_grant.value, schema)


def _explain_result_has_plan(row):
    return bool(row and len(row) >= 1 and row[0] and len(row[0]) >= 1)


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

    Returns ``(None, name)`` for unqualified names -- Postgres resolves those via
    ``search_path`` at call time, so the schema cannot be determined statically.
    Callers must follow that resolution rather than defaulting to ``public``.
    """
    if not name:
        return None, ""
    parts = name.split(".", 1)
    if len(parts) == 1:
        return None, parts[0]
    return parts[0], parts[1]
