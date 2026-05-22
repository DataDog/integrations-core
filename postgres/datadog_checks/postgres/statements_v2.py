# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import copy
import time

import psycopg
from cachetools import TTLCache
from psycopg.rows import dict_row

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.postgres.config_models import InstanceConfig

from .delta_detector import DeltaDetector
from .obfuscation_lookup import ObfuscationLookup, ObfuscationResult
from .statements import (
    PG_STAT_STATEMENTS_COUNT_QUERY,
    PG_STAT_STATEMENTS_COUNT_QUERY_LT_9_4,
    PG_STAT_STATEMENTS_DEALLOC,
    PG_STAT_STATEMENTS_METRICS_COLUMNS,
    PG_STAT_STATEMENTS_TIMING_COLUMNS,
    PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17,
    statements_query,
)
from .util import (
    DatabaseConfigurationError,
    parse_shared_preload_libraries,
    payload_pg_version,
    warning_with_tags,
)
from .version_utils import V9_4, V14

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


LIGHTWEIGHT_SNAPSHOT_QUERY = """
SELECT {cols}
  FROM pg_stat_statements(false) AS pg_stat_statements
  LEFT JOIN pg_roles
         ON pg_stat_statements.userid = pg_roles.oid
  LEFT JOIN pg_database
         ON pg_stat_statements.dbid = pg_database.oid
  WHERE queryid IS NOT NULL
  {filters}
"""

QUERY_TEXT_FETCH = """
SELECT queryid, query
  FROM pg_stat_statements
  WHERE queryid = ANY(%s::bigint[])
"""

DEFAULT_PGSS_MAX = 5000

LIGHTWEIGHT_REQUIRED_COLUMNS = frozenset({'queryid', 'userid', 'dbid', 'calls'})

LIGHTWEIGHT_TAG_COLUMNS = frozenset({'datname', 'rolname'})

LIGHTWEIGHT_DESIRED_COLUMNS = (
    LIGHTWEIGHT_REQUIRED_COLUMNS | LIGHTWEIGHT_TAG_COLUMNS | PG_STAT_STATEMENTS_METRICS_COLUMNS
)


def agent_check_getter(self):
    return self._check


def _output_row_key(row):
    return row['query_signature'], row['datname'], row['rolname']


class PostgresStatementMetricsV2(DBMAsyncJob):
    """Collects statement metrics using change detection and cached obfuscation.

    Each collection cycle:
      1. Query pg_stat_statements(false) for counters only (no query text).
      2. Diff against the previous snapshot to find changed rows.
      3. For changed queryids, look up cached ObfuscationResults; on miss,
         fetch text from PG, obfuscate via FFI, cache, and discard raw text.
      4. Merge derivative rows by (query_signature, datname, rolname) and emit.
    """

    def __init__(self, check, config: InstanceConfig):
        collection_interval = float(config.query_metrics.collection_interval)
        super().__init__(
            check,
            run_sync=config.query_metrics.run_sync,
            enabled=config.query_metrics.enabled,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            min_collection_interval=config.min_collection_interval,
            dbms="postgres",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
        )
        self._check = check
        self._config = config
        self._metrics_collection_interval = collection_interval
        self._pg_stat_statements_max_warning_threshold = config.query_metrics.pg_stat_statements_max_warning_threshold
        self.batch_max_content_size = config.query_metrics.batch_max_content_size
        self._tags_no_db: list[str] | None = None
        self.tags: list[str] | None = None

        self._delta_detector = DeltaDetector(
            metric_columns=PG_STAT_STATEMENTS_METRICS_COLUMNS,
            execution_indicators=frozenset({'calls'}),
        )

        obfuscate_options = config.obfuscator_options.model_dump()
        obfuscate_options['table_names'] = config.obfuscator_options.collect_tables
        obfuscate_options['dollar_quoted_func'] = config.obfuscator_options.keep_dollar_quoted_func
        obfuscate_options['return_json_metadata'] = config.obfuscator_options.collect_metadata
        obfuscate_options_str = to_native_string(json.dumps(obfuscate_options))

        self._obfuscation_lookup = ObfuscationLookup(
            maxsize=DEFAULT_PGSS_MAX,
            obfuscate_options=obfuscate_options_str,
            log_unobfuscated_queries=config.log_unobfuscated_queries,
        )

        self._full_statement_text_cache = TTLCache(
            maxsize=config.query_metrics.full_statement_text_cache_max_size,
            ttl=60 * 60 / config.query_metrics.full_statement_text_samples_per_hour_per_query,
        )
        self._stat_column_cache: list[str] = []

    def _shutdown(self):
        self._check = None
        self._full_statement_text_cache = None
        self._delta_detector = None
        self._obfuscation_lookup = None

    # -- Database helpers ------------------------------------------------

    def _execute_query(self, query, params=(), row_factory=None) -> tuple[list, list]:
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        try:
            with self._check._get_main_db() as conn:
                with conn.cursor(row_factory=row_factory) as cursor:
                    self._log.debug("Executing query [%s] params=%s", query, params)
                    cursor.execute(query, params=params)
                    return cursor.fetchall(), cursor.description
        except psycopg.Error as e:
            self._log.warning("Failed to run query [%s] %s", query, params)
            self._stat_column_cache = []
            raise e

    # -- Column introspection ---------------------------------------------

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_pg_stat_statements_columns(self):
        if self._stat_column_cache:
            return self._stat_column_cache
        query = statements_query(
            cols='*',
            pg_stat_statements_view='pg_stat_statements',
            extra_clauses="LIMIT 0",
        )
        _, description = self._execute_query(query)
        col_names = [desc[0] for desc in description] if description else []
        self._stat_column_cache = col_names
        self._log.debug("pgss columns: %d available", len(col_names))
        return col_names

    # -- pgss housekeeping metrics ----------------------------------------

    @tracked_method(agent_check_getter=agent_check_getter)
    def _emit_pg_stat_statements_metrics(self):
        query = PG_STAT_STATEMENTS_COUNT_QUERY_LT_9_4 if self._check.version < V9_4 else PG_STAT_STATEMENTS_COUNT_QUERY
        try:
            rows, _ = self._execute_query(query)
            count = rows[0][0] if rows else 0
            self._check.gauge(
                "pg_stat_statements.max",
                self._check.pg_settings.get("pg_stat_statements.max", 0),
                tags=self.tags,
                hostname=self._check.reported_hostname,
            )
            self._check.count(
                "pg_stat_statements.count",
                count,
                tags=self.tags,
                hostname=self._check.reported_hostname,
            )
        except psycopg.Error as e:
            self._log.warning("Failed to query for pg_stat_statements count: %s", e)

    def _emit_pg_stat_statements_dealloc(self):
        if self._check.version < V14:
            return
        try:
            rows, _ = self._execute_query(PG_STAT_STATEMENTS_DEALLOC)
            if rows:
                self._check.monotonic_count(
                    "pg_stat_statements.dealloc",
                    rows[0][0],
                    tags=self.tags,
                    hostname=self._check.reported_hostname,
                )
        except psycopg.Error as e:
            self._log.warning("Failed to query for pg_stat_statements_info: %s", e)

    def _emit_pg_stat_statements_max_warning(self):
        pg_stat_statements_max_setting = self._check.pg_settings.get("pg_stat_statements.max")
        pg_stat_statements_max = int(pg_stat_statements_max_setting) if pg_stat_statements_max_setting else 0
        if pg_stat_statements_max > self._pg_stat_statements_max_warning_threshold:
            self._check.record_warning(
                DatabaseConfigurationError.high_pg_stat_statements_max,
                warning_with_tags(
                    "pg_stat_statements.max is set to %d which is higher than the supported "
                    "value of %d. This can have a negative impact on database and collection of "
                    "query metrics performance. Consider lowering the pg_stat_statements.max value to %d. "
                    "Alternatively, you may acknowledge the potential performance impact by increasing the "
                    "query_metrics.pg_stat_statements_max_warning_threshold to equal or greater than %d to "
                    "silence this warning. "
                    "See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                    "troubleshooting#%s for more details",
                    pg_stat_statements_max,
                    self._pg_stat_statements_max_warning_threshold,
                    self._pg_stat_statements_max_warning_threshold,
                    self._pg_stat_statements_max_warning_threshold,
                    DatabaseConfigurationError.high_pg_stat_statements_max.value,
                    host=self._check.reported_hostname,
                    dbname=self._config.dbname,
                    code=DatabaseConfigurationError.high_pg_stat_statements_max.value,
                    value=pg_stat_statements_max,
                    threshold=self._pg_stat_statements_max_warning_threshold,
                ),
            )

    # -- Cache size management --------------------------------------------

    def _sync_cache_sizes(self):
        pgss_max_setting = self._check.pg_settings.get("pg_stat_statements.max")
        pgss_max = int(pgss_max_setting) if pgss_max_setting else DEFAULT_PGSS_MAX
        if self._obfuscation_lookup._maxsize != pgss_max:
            self._obfuscation_lookup._maxsize = pgss_max

    # -- Lightweight snapshot (integer-only, no query text) ---------------

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_lightweight_snapshot(self) -> list[dict]:
        try:
            available_columns = set(self._get_pg_stat_statements_columns())
            missing = LIGHTWEIGHT_REQUIRED_COLUMNS - available_columns
            if missing:
                self._check.warning(
                    warning_with_tags(
                        "Unable to collect statement metrics because required fields are unavailable: %s.",
                        ', '.join(sorted(missing)),
                        host=self._check.reported_hostname,
                        dbname=self._config.dbname,
                    ),
                )
                self._check.count(
                    "dd.postgres.statement_metrics.error",
                    1,
                    tags=self.tags
                    + ["error:database-missing_pg_stat_statements_required_columns"]
                    + self._check._get_debug_tags(),
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                return []

            desired = LIGHTWEIGHT_DESIRED_COLUMNS
            if self._check.pg_settings.get("track_io_timing") != "on":
                desired = desired - PG_STAT_STATEMENTS_TIMING_COLUMNS - PG_STAT_STATEMENTS_TIMING_COLUMNS_LT_17

            query_columns = sorted(available_columns & desired)

            params: tuple = ()
            filters = ""
            if self._config.dbstrict:
                filters = "AND pg_database.datname = %s"
                params = (self._config.dbname,)
            elif self._config.ignore_databases:
                filters = " AND " + " AND ".join(
                    "pg_database.datname NOT ILIKE %s" for _ in self._config.ignore_databases
                )
                params = tuple(self._config.ignore_databases)

            query = LIGHTWEIGHT_SNAPSHOT_QUERY.format(
                cols=', '.join(query_columns),
                filters=filters,
            )
            rows, _ = self._execute_query(query, params=params, row_factory=dict_row)
            return rows

        except psycopg.Error as e:
            self._handle_pgss_error(e)
            return []

    # -- Obfuscation resolution -------------------------------------------

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _resolve_obfuscations(
        self, changed_queryids: set[int], vanished_queryids: set[int]
    ) -> dict[int, ObfuscationResult]:
        self._obfuscation_lookup.evict(vanished_queryids)

        if not changed_queryids:
            return {}

        hits, misses = self._obfuscation_lookup.lookup(changed_queryids)

        self._check.gauge(
            "dd.postgres.statement_metrics.lookup.hits",
            len(hits),
            tags=self.tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )
        self._check.gauge(
            "dd.postgres.statement_metrics.lookup.misses",
            len(misses),
            tags=self.tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )

        if misses:
            raw_texts = self._fetch_query_texts(misses)
            filtered = {
                qid: text
                for qid, text in raw_texts.items()
                if text and text != '<insufficient privilege>' and not text.startswith('/* DDIGNORE */')
            }
            self._log.debug(
                "resolve: fetched=%d filtered=%d for %d misses",
                len(raw_texts),
                len(filtered),
                len(misses),
            )
            populated = self._obfuscation_lookup.populate(filtered)
            hits.update(populated)

        return hits

    def _fetch_query_texts(self, queryids: set[int]) -> dict[int, str]:
        query = QUERY_TEXT_FETCH
        try:
            rows, _ = self._execute_query(query, params=(list(queryids),), row_factory=dict_row)
            return {row['queryid']: row['query'] for row in rows}
        except psycopg.Error as e:
            self._log.warning("Failed to fetch query text for %d queryids: %s", len(queryids), e)
            return {}

    # -- Row assembly -----------------------------------------------------

    def _assemble_rows(self, derivative_rows: list[dict], obfuscations: dict[int, ObfuscationResult]) -> list[dict]:
        assembled: list[dict] = []
        for row in derivative_rows:
            qid = row['queryid']
            obf = obfuscations.get(qid)
            if obf is None:
                continue
            out = dict(row)
            out.pop('dbid', None)
            out.pop('userid', None)
            out['query'] = obf.obfuscated_query
            out['query_signature'] = obf.query_signature
            out['dd_tables'] = obf.tables
            out['dd_commands'] = obf.commands
            out['dd_comments'] = obf.comments
            assembled.append(out)

        return self._merge_by_query_signature(assembled)

    @staticmethod
    def _merge_by_query_signature(rows: list[dict]) -> list[dict]:
        """Merge rows sharing (query_signature, datname, rolname) by summing metric columns."""
        merged: dict[tuple, dict] = {}
        metrics = PG_STAT_STATEMENTS_METRICS_COLUMNS
        for row in rows:
            key = _output_row_key(row)
            if key in merged:
                for col in metrics:
                    if col in row:
                        merged[key][col] = merged[key].get(col, 0) + row[col]
            else:
                merged[key] = row
        return list(merged.values())

    # -- Main collection pipeline -----------------------------------------

    def run_job(self):
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self.collect_per_statement_metrics()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_per_statement_metrics(self):
        try:
            rows = self._collect_metrics_rows()
            if not rows:
                return

            for event in self._rows_to_fqt_events(rows):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

            payload_wrapper = {
                'host': self._check.reported_hostname,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._metrics_collection_interval,
                'tags': self._tags_no_db,
                'cloud_metadata': self._check.cloud_metadata,
                'postgres_version': payload_pg_version(self._check.version),
                'ddagentversion': datadog_agent.get_version(),
                'service': self._config.service,
            }

            payloads = self._get_query_metrics_payloads(payload_wrapper, rows)
            for payload in payloads:
                self._check.database_monitoring_query_metrics(payload)
        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
            return []

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self) -> list[dict]:
        self._emit_pg_stat_statements_metrics()
        self._emit_pg_stat_statements_dealloc()
        self._emit_pg_stat_statements_max_warning()
        self._sync_cache_sizes()

        snapshot_rows = self._load_lightweight_snapshot()
        if not snapshot_rows:
            self._log.debug("collect: no snapshot rows")
            return []

        delta = self._delta_detector.compute(snapshot_rows)

        self._check.gauge(
            "dd.postgres.statement_metrics.delta.derivative_rows",
            len(delta.derivative_rows),
            tags=self.tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )
        self._check.gauge(
            "dd.postgres.statement_metrics.delta.changed_queryids",
            len(delta.changed_queryids),
            tags=self.tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )

        if not delta.derivative_rows:
            return []

        obfuscations = self._resolve_obfuscations(delta.changed_queryids, delta.vanished_queryids)
        rows = self._assemble_rows(delta.derivative_rows, obfuscations)
        self._log.debug(
            "collect: snapshot=%d derivative=%d obfuscated=%d output=%d",
            len(snapshot_rows),
            len(delta.derivative_rows),
            len(obfuscations),
            len(rows),
        )

        self._check.gauge(
            'dd.postgres.queries.query_rows_raw',
            len(rows),
            tags=self.tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )

        return rows

    # -- Output formatting ------------------------------------------------

    def _get_query_metrics_payloads(self, payload_wrapper, rows):
        payloads = []
        max_size = self.batch_max_content_size
        queue = [rows]
        while queue:
            current = queue.pop()
            if not current:
                continue
            payload = copy.deepcopy(payload_wrapper)
            payload["postgres_rows"] = current
            serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            size = len(serialized_payload)
            if size < max_size:
                payloads.append(serialized_payload)
            else:
                if len(current) == 1:
                    self._log.warning(
                        "A single query is too large to send to Datadog. This query will be dropped. size=%d",
                        size,
                    )
                    continue
                mid = len(current) // 2
                queue.append(current[:mid])
                queue.append(current[mid:])
        return payloads

    def _rows_to_fqt_events(self, rows):
        for row in rows:
            query_cache_key = _output_row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = self._tags_no_db + [
                "db:{}".format(row['datname']),
                "rolname:{}".format(row['rolname']),
            ]
            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "postgres",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                'service': self._config.service,
                "db": {
                    "instance": row['datname'],
                    "query_signature": row['query_signature'],
                    "statement": row['query'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row['dd_comments'],
                    },
                },
                "postgres": {
                    "datname": row["datname"],
                    "rolname": row["rolname"],
                },
            }

    # -- Error handling ---------------------------------------------------

    def _handle_pgss_error(self, e: psycopg.Error):
        error_tag = "error:database-{}".format(type(e).__name__)

        if isinstance(e, psycopg.errors.ObjectNotInPrerequisiteState) and 'pg_stat_statements' in str(e):
            error_tag = "error:database-{}-pg_stat_statements_not_loaded".format(type(e).__name__)
            self._record_pg_stat_statements_not_loaded()
        elif isinstance(e, psycopg.errors.UndefinedTable) and 'pg_stat_statements' in str(e):
            spl = self._check.pg_settings.get("shared_preload_libraries", "") or ""
            if spl and "pg_stat_statements" not in parse_shared_preload_libraries(spl):
                error_tag = "error:database-{}-pg_stat_statements_not_loaded".format(type(e).__name__)
                self._record_pg_stat_statements_not_loaded()
            else:
                error_tag = "error:database-{}-pg_stat_statements_not_created".format(type(e).__name__)
                self._check.record_warning(
                    DatabaseConfigurationError.pg_stat_statements_not_created,
                    warning_with_tags(
                        "Unable to collect statement metrics because pg_stat_statements is not created "
                        "in database '%s'. See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                        "troubleshooting#%s for more details",
                        self._config.dbname,
                        DatabaseConfigurationError.pg_stat_statements_not_created.value,
                        host=self._check.reported_hostname,
                        dbname=self._config.dbname,
                        code=DatabaseConfigurationError.pg_stat_statements_not_created.value,
                    ),
                )
        else:
            self._check.warning(
                warning_with_tags(
                    "Unable to collect statement metrics because of an error running queries "
                    "in database '%s'. See https://docs.datadoghq.com/database_monitoring/troubleshooting for "
                    "help: %s",
                    self._config.dbname,
                    str(e),
                    host=self._check.reported_hostname,
                    dbname=self._config.dbname,
                ),
            )

        self._check.count(
            "dd.postgres.statement_metrics.error",
            1,
            tags=self.tags + [error_tag] + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )

    def _record_pg_stat_statements_not_loaded(self):
        code = DatabaseConfigurationError.pg_stat_statements_not_loaded
        self._check.record_warning(
            code,
            warning_with_tags(
                "Unable to collect statement metrics because pg_stat_statements "
                "extension is not loaded in database '%s'. "
                "See https://docs.datadoghq.com/database_monitoring/setup_postgres/"
                "troubleshooting#%s for more details",
                self._config.dbname,
                code.value,
                host=self._check.reported_hostname,
                dbname=self._config.dbname,
                code=code.value,
            ),
        )
