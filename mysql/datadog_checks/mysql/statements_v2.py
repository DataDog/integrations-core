# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import annotations

import time
from contextlib import closing
from operator import attrgetter
from typing import Any

import pymysql
from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor

from .delta_detector import DeltaDetector, DeltaKey
from .obfuscation_lookup import ObfuscationLookup, ObfuscationResult, obfuscate_statement
from .statements import INTERNAL_COLUMNS, METRICS_COLUMNS, PREPARED_STATEMENT_SOURCE
from .util import DatabaseConfigurationError, ManagedAuthConnectionMixin, get_list_chunks, warning_with_tags

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

Row = dict[str, Any]

# Ordered projection of the cumulative counters, derived from METRICS_COLUMNS so the snapshot and
# the delta computation can never drift apart.
SNAPSHOT_METRIC_COLUMNS = tuple(sorted(METRICS_COLUMNS))

# The digest table is bounded by performance_schema_digests_size, so a plain scan is cheap. Rows
# with a NULL digest are the single overflow bucket, which aggregates every statement that did not
# fit in the table and therefore has no resolvable text.
DIGEST_SNAPSHOT_QUERY = """\
    SELECT `schema_name`,
           `digest`,
           {metric_columns},
           `last_seen`
    FROM performance_schema.events_statements_summary_by_digest
    WHERE `digest` IS NOT NULL
    ORDER BY `count_star` DESC
    LIMIT 10000
    """.format(metric_columns=',\n           '.join('`{}`'.format(col) for col in SNAPSHOT_METRIC_COLUMNS))

# The table is indexed on (SCHEMA_NAME, DIGEST), so filtering on the digest alone cannot use the
# index and scans instead. Acceptable because this only runs for digests missing from the
# obfuscation cache, which is empty once at startup and then only sees genuinely new statements.
DIGEST_TEXT_QUERY = """\
    SELECT `digest`,
           MIN(`digest_text`) AS `digest_text`
    FROM performance_schema.events_statements_summary_by_digest
    WHERE `digest` IN ({placeholders})
    GROUP BY `digest`
    """

# Every prepared statement object has a row in `performance_schema.prepared_statements_instances`.
# MySQL documents `object_instance_begin` as the table's primary key:
# https://dev.mysql.com/doc/refman/8.4/en/performance-schema-prepared-statements-instances-table.html
PREPARED_STATEMENTS_QUERY = """\
    SELECT  `object_instance_begin` AS `_dd_statement_id`,
            `owner_object_schema` AS `schema_name`,
            NULL AS `digest`,
            `sql_text` AS `digest_text`,
            `count_execute` AS `count_star`,
            `sum_timer_execute` AS `sum_timer_wait`,
            `sum_lock_time` AS `sum_lock_time`,
            `sum_errors` AS `sum_errors`,
            `sum_rows_affected` AS `sum_rows_affected`,
            `sum_rows_sent` AS `sum_rows_sent`,
            `sum_rows_examined` AS `sum_rows_examined`,
            `sum_select_scan` AS `sum_select_scan`,
            `sum_select_full_join` AS `sum_select_full_join`,
            `sum_no_index_used` AS `sum_no_index_used`,
            `sum_no_good_index_used` AS `sum_no_good_index_used`,
            `sum_sort_rows` AS `sum_sort_rows`,
            `sum_sort_merge_passes` AS `sum_sort_merge_passes`,
            `sum_sort_range` AS `sum_sort_range`,
            `sum_sort_scan` AS `sum_sort_scan`,
            `sum_created_tmp_tables` AS `sum_created_tmp_tables`,
            `sum_created_tmp_disk_tables` AS `sum_created_tmp_disk_tables`,
            `sum_select_full_range_join` AS `sum_select_full_range_join`,
            `sum_select_range` AS `sum_select_range`,
            `sum_select_range_check` AS `sum_select_range_check`,
            NOW() AS `last_seen`
    FROM performance_schema.prepared_statements_instances
    WHERE (`sql_text` NOT LIKE 'EXPLAIN %' OR `sql_text` IS NULL)
    """

STATEMENT_COUNT_QUERY = "SELECT count(*) AS count from performance_schema.events_statements_summary_by_digest"

# Fallback when performance_schema_digests_size is unreadable. Matches the size MySQL autosizes to.
DEFAULT_DIGESTS_SIZE = 10000

# Digests per IN list. Bounded to keep the statement short enough to stay well inside
# max_allowed_packet and to avoid a pathological parse on the first collection after startup.
DIGEST_TEXT_BATCH_SIZE = 500


def _digest_delta_key(row: Row) -> DeltaKey:
    """Key the cumulative counters of a digest row.

    `events_statements_summary_by_digest` aggregates per (schema, digest), so both are needed even
    though the query text depends on the digest alone.
    """
    return row['schema_name'], row['digest']


def _prepared_delta_key(row: Row) -> DeltaKey:
    """Key the cumulative counters of a prepared statement row.

    `object_instance_begin` is a reusable address, so a recycled instance can carry unrelated text.
    Including the signature keeps a counter series tied to one statement.
    """
    return PREPARED_STATEMENT_SOURCE, row['schema_name'], row['_dd_statement_id'], row['query_signature']


def _output_row_key(row: Row):
    return row['schema_name'], row['query_signature']


def _strip_internal_columns(row: Row) -> Row:
    return {k: v for k, v in row.items() if k not in INTERNAL_COLUMNS}


def _merge_rows_by_query_signature(rows: list[Row]) -> list[Row]:
    """Merge rows sharing (schema_name, query_signature) by summing their metric columns."""
    merged_rows: dict[tuple, Row] = {}
    for row in rows:
        query_key = _output_row_key(row)
        if query_key in merged_rows:
            for metric in METRICS_COLUMNS:
                if metric in row:
                    merged_rows[query_key][metric] = merged_rows[query_key].get(metric, 0) + row[metric]
        else:
            merged_rows[query_key] = _strip_internal_columns(row)

    return list(merged_rows.values())


class MySQLStatementMetricsV2(ManagedAuthConnectionMixin, DBMAsyncJob):
    """Collects per-statement metrics using change detection and cached obfuscation.

    The v1 collector transfers and obfuscates `digest_text` for every row in
    `events_statements_summary_by_digest` on every collection, even though most of those statements
    did not run during the interval. Each cycle here instead:

      1. Reads a counters-only snapshot of the digest table (no query text).
      2. Diffs it against the previous snapshot to find the statements that actually executed.
      3. Resolves those digests against an obfuscation cache; on a miss, fetches the text, obfuscates
         it via the FFI, caches the result, and discards the raw text.
      4. Merges the derivative rows by (schema_name, query_signature) and emits.

    Prepared statements stay on the eager path: `prepared_statements_instances` exposes no stable
    identity for its `sql_text`, so their text is fetched and obfuscated every cycle. That table is
    small, and its rows are merged into the output alongside the digest rows.
    """

    def __init__(self, check, config, connection_args_provider, uses_managed_auth=False):
        collection_interval = float(config.statement_metrics_config.get('collection_interval', 10))
        if collection_interval <= 0:
            collection_interval = 10
        super().__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=is_affirmative(config.statement_metrics_config.get('run_sync', False)),
            enabled=is_affirmative(config.statement_metrics_config.get('enabled', True)),
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            min_collection_interval=config.min_collection_interval,
            dbms=check.dbms,
            job_name="statement-metrics",
            shutdown_callback=self._close_db_conn,
        )
        self._check = check
        self._collect_prepared_statements = None
        self._metric_collection_interval = collection_interval
        self._connection_args_provider = connection_args_provider
        self._uses_managed_auth = uses_managed_auth
        self._db_created_at = 0
        self._db = None
        self._config = config
        self.log = get_check_logger()

        if is_affirmative(config.statement_metrics_config.get('only_query_recent_statements', False)):
            self.log.warning(
                "only_query_recent_statements has no effect when incremental_query_metrics is enabled, "
                "because the counters-only snapshot already restricts collection to statements that ran."
            )

        self._obfuscate_options = to_native_string(json.dumps(self._config.obfuscator_options))
        self._obfuscation_lookup = ObfuscationLookup(
            maxsize=DEFAULT_DIGESTS_SIZE,
            obfuscate_options=self._obfuscate_options,
            log_unobfuscated_queries=self._config.log_unobfuscated_queries,
        )

        # Separate detectors: the two sources are read by separate queries, so feeding both through
        # one detector would make each source's keys look vanished to the other.
        self._digest_delta = DeltaDetector(
            metric_columns=METRICS_COLUMNS,
            key=_digest_delta_key,
            execution_indicators=frozenset({'count_star'}),
        )
        self._prepared_delta = DeltaDetector(
            metric_columns=METRICS_COLUMNS,
            key=_prepared_delta_key,
            execution_indicators=frozenset({'count_star'}),
        )

        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=self._config.full_statement_text_cache_max_size,
            ttl=60 * 60 / self._config.full_statement_text_samples_per_hour_per_query,
        )

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close db connection", exc_info=1)
            finally:
                self._db = None

    # -- Main collection pipeline -----------------------------------------

    def run_job(self):
        start = time.time()
        self.collect_per_statement_metrics()
        self._check.gauge(
            "dd.mysql.statement_metrics.collect_metrics.elapsed_ms",
            (time.time() - start) * 1000,
            tags=self._check.tag_manager.get_tags() + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    @tracked_method(agent_check_getter=attrgetter('_check'))
    def collect_per_statement_metrics(self):
        # Detect a database misconfiguration by checking if the performance schema is enabled since mysql
        # just returns no rows without errors if the performance schema is disabled
        if self._check.global_variables.performance_schema_enabled is False:
            self._check.record_warning(
                DatabaseConfigurationError.performance_schema_not_enabled,
                warning_with_tags(
                    'Unable to collect statement metrics because the performance schema is disabled. '
                    'See https://docs.datadoghq.com/database_monitoring/setup_mysql/'
                    'troubleshooting#%s for more details',
                    DatabaseConfigurationError.performance_schema_not_enabled.value,
                    code=DatabaseConfigurationError.performance_schema_not_enabled.value,
                    host=self._check.reported_hostname,
                ),
            )
            return

        # Omit internal tags for dbm payloads since those are only relevant to metrics processed directly
        # by the agent
        tags = [t for t in self._tags if not t.startswith('dd.internal')]

        rows = self._collect_per_statement_metrics(tags)
        if not rows:
            # No rows to process, can skip the rest of the payload generation and avoid an empty payload
            return
        for event in self._rows_to_fqt_events(rows, tags):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
        payload = {
            'host': self._check.resolved_hostname,
            'timestamp': time.time() * 1000,
            'mysql_version': self._check.version.version + '+' + self._check.version.build,
            'mysql_flavor': self._check.version.flavor,
            'ddagentversion': datadog_agent.get_version(),
            'min_collection_interval': self._metric_collection_interval,
            'tags': tags,
            'cloud_metadata': self._config.cloud_metadata,
            'service': self._config.service,
            'mysql_rows': rows,
        }
        self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))
        self._check.gauge(
            "dd.mysql.collect_per_statement_metrics.rows",
            len(rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _collect_per_statement_metrics(self, tags: list[str]) -> list[Row]:
        self._get_statement_count(tags)
        self._sync_cache_sizes()

        snapshot_rows = self._query_digest_snapshot()
        self._check.gauge(
            "dd.mysql.statement_metrics.query_rows",
            len(snapshot_rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

        delta = self._digest_delta.compute(snapshot_rows)

        changed_digests = {digest for _schema_name, digest in delta.changed_keys}
        # A digest is only forgotten once no schema references it any more, since the cached text is
        # shared across every schema that ran the same statement.
        live_digests = {row['digest'] for row in snapshot_rows}
        vanished_digests = {digest for _schema_name, digest in delta.vanished_keys} - live_digests

        self._check.gauge(
            "dd.mysql.statement_metrics.delta.derivative_rows",
            len(delta.derivative_rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )
        self._check.gauge(
            "dd.mysql.statement_metrics.delta.changed_digests",
            len(changed_digests),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )

        obfuscations = self._resolve_obfuscations(changed_digests, vanished_digests, tags)
        rows = self._assemble_digest_rows(delta.derivative_rows, obfuscations)
        rows.extend(self._collect_prepared_statement_rows())

        self._log.debug(
            "collect: snapshot=%d derivative=%d changed_digests=%d obfuscated=%d rows=%d",
            len(snapshot_rows),
            len(delta.derivative_rows),
            len(changed_digests),
            len(obfuscations),
            len(rows),
        )

        return _merge_rows_by_query_signature(rows)

    # -- Cache size management --------------------------------------------

    def _sync_cache_sizes(self):
        """Size the obfuscation cache to the digest table it mirrors.

        The cache is keyed on the digest while `performance_schema_digests_size` bounds
        (schema, digest) rows, so the table's size is a safe upper bound on the distinct digests
        that can be live at once.
        """
        digests_size = self._check.global_variables.performance_schema_digests_size
        maxsize = digests_size if digests_size and digests_size > 0 else DEFAULT_DIGESTS_SIZE
        if self._obfuscation_lookup.maxsize != maxsize:
            self._obfuscation_lookup.maxsize = maxsize

    # -- Database reads ---------------------------------------------------

    def _get_statement_count(self, tags: list[str]):
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(STATEMENT_COUNT_QUERY)

            rows = cursor.fetchall() or []
            if rows:
                self._check.gauge(
                    "dd.mysql.statement_metrics.events_statements_summary_by_digest.total_rows",
                    rows[0]['count'],
                    tags=tags + self._check._get_debug_tags(),
                    hostname=self._check.resolved_hostname,
                )

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _query_digest_snapshot(self) -> list[Row]:
        """Read the cumulative counters for every digest, without any query text."""
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(DIGEST_SNAPSHOT_QUERY)
            return cursor.fetchall() or []

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _fetch_digest_texts(self, digests: set[str]) -> dict[str, str]:
        """Fetch `digest_text` for the given digests, in batches."""
        texts: dict[str, str] = {}
        if not digests:
            return texts
        try:
            with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
                for chunk in get_list_chunks(sorted(digests), DIGEST_TEXT_BATCH_SIZE):
                    query = DIGEST_TEXT_QUERY.format(placeholders=', '.join(['%s'] * len(chunk)))
                    cursor.execute(query, chunk)
                    for row in cursor.fetchall() or []:
                        texts[row['digest']] = row['digest_text']
        except pymysql.err.DatabaseError as e:
            # Digests left unresolved stay misses and are retried on the next collection.
            self._log.warning("Failed to fetch digest text for %d digests: %s", len(digests), e)
        return texts

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _query_prepared_statements(self) -> list[Row]:
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(PREPARED_STATEMENTS_QUERY)
            return cursor.fetchall() or []

    # -- Obfuscation resolution -------------------------------------------

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _resolve_obfuscations(
        self, changed_digests: set[str], vanished_digests: set[str], tags: list[str]
    ) -> dict[str, ObfuscationResult]:
        self._obfuscation_lookup.evict(vanished_digests)

        if not changed_digests:
            return {}

        hits, misses = self._obfuscation_lookup.lookup(changed_digests)

        self._check.gauge(
            "dd.mysql.statement_metrics.lookup.hits",
            len(hits),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )
        self._check.gauge(
            "dd.mysql.statement_metrics.lookup.misses",
            len(misses),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.reported_hostname,
        )

        if misses:
            raw_texts = self._fetch_digest_texts(misses)
            cacheable: dict[str, str] = {}
            ignorable: set[str] = set()
            for digest, text in raw_texts.items():
                if not text:
                    continue
                if text.lower().startswith('explain'):
                    # EXPLAIN statements are an artifact of plan collection rather than application
                    # traffic. v1 filters them out of the snapshot; here the snapshot has no text to
                    # filter on, so they are recognized after resolution and negative-cached to keep
                    # the filtering to one fetch per digest.
                    ignorable.add(digest)
                    continue
                cacheable[digest] = text
            populated, failures = self._obfuscation_lookup.populate(cacheable)
            self._obfuscation_lookup.mark_ignored(ignorable | failures)
            hits.update(populated)

        return hits

    # -- Row assembly -----------------------------------------------------

    def _assemble_digest_rows(
        self, derivative_rows: list[Row], obfuscations: dict[str, ObfuscationResult]
    ) -> list[Row]:
        assembled: list[Row] = []
        for row in derivative_rows:
            obf = obfuscations.get(row['digest'])
            if obf is None:
                continue
            out = dict(row)
            out['digest_text'] = obf.obfuscated_statement
            out['query_signature'] = obf.query_signature
            out['dd_tables'] = obf.tables
            out['dd_commands'] = obf.commands
            out['dd_comments'] = obf.comments
            assembled.append(out)
        return assembled

    def _collect_prepared_statement_rows(self) -> list[Row]:
        if not self.collect_prepared_statements:
            return []
        rows = self._normalize_prepared_statements(self._query_prepared_statements())
        return self._prepared_delta.compute(rows).derivative_rows

    def _normalize_prepared_statements(self, rows: list[Row]) -> list[Row]:
        """Obfuscate prepared statement text, which must happen before the delta is computed.

        Unlike a digest, `object_instance_begin` does not determine the statement text, so the
        signature is part of the counter key and has to be resolved for every row every cycle.
        """
        normalized_rows: list[Row] = []
        for row in rows:
            text = row['digest_text']
            if text is None or text.lower().startswith('explain'):
                continue
            result = obfuscate_statement(text, self._obfuscate_options, self._config.log_unobfuscated_queries)
            if result is None:
                continue
            normalized_row = dict(row)
            normalized_row['digest_text'] = result.obfuscated_statement
            normalized_row['query_signature'] = result.query_signature
            normalized_row['dd_tables'] = result.tables
            normalized_row['dd_commands'] = result.commands
            normalized_row['dd_comments'] = result.comments
            normalized_rows.append(normalized_row)
        return normalized_rows

    # -- Output formatting ------------------------------------------------

    def _rows_to_fqt_events(self, rows: list[Row], tags: list[str]):
        for row in rows:
            query_cache_key = _output_row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True
            row_tags = tags + ["schema:{}".format(row['schema_name'])] if row['schema_name'] else tags
            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.reported_hostname,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "mysql",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                'service': self._config.service,
                "db": {
                    "instance": row['schema_name'],
                    "query_signature": row['query_signature'],
                    "statement": row['digest_text'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row['dd_comments'],
                    },
                },
                "mysql": {"schema": row["schema_name"]},
            }

    @property
    def collect_prepared_statements(self):
        if self._collect_prepared_statements is None:
            # prepared_statements_instances table was added to MariaDB 10.5.2
            if self._check.is_mariadb and self._check.version.version_compatible((10, 5, 2)) is False:
                self._collect_prepared_statements = False
            # prepared_statements_instances table was added to MySQL 5.7.4
            elif self._check.version.version_compatible((5, 7, 4)) is False:
                self._collect_prepared_statements = False
            else:
                self._collect_prepared_statements = self._config.statement_metrics_config.get(
                    'collect_prepared_statements', True
                )
        return self._collect_prepared_statements
