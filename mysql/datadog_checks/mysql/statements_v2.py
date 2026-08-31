# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from contextlib import closing
from operator import attrgetter
from typing import Any

import pymysql

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.query_metrics import (
    ObfuscationLookup,
    ObfuscationResult,
    QueryStats,
    ResolveStats,
    TextKind,
    obfuscate_statement,
    resolve_obfuscations,
)
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mysql.cursor import CommenterDictCursor

from .statements import (
    METRICS_COLUMNS,
    PREPARED_STATEMENT_SOURCE,
    MySQLStatementMetrics,
    _merge_rows_by_query_signature,
)
from .util import get_list_chunks

Row = dict[str, Any]
DigestKey = tuple[str | None, str | None]
PreparedKey = tuple[str, str | None, Any, str]

SNAPSHOT_METRIC_COLUMNS = tuple(sorted(METRICS_COLUMNS))
SNAPSHOT_ROW_LIMIT = 10000
DEFAULT_DIGESTS_SIZE = 10000
DIGEST_TEXT_BATCH_SIZE = 500
STATEMENT_COUNT_REFRESH_INTERVAL = 60

DIGEST_SNAPSHOT_QUERY_BODY = """\
    SELECT `schema_name`,
           `digest`,
           {metric_columns},
           `last_seen`
    FROM performance_schema.events_statements_summary_by_digest
    """.format(metric_columns=',\n           '.join('`{}`'.format(col) for col in SNAPSHOT_METRIC_COLUMNS))

DIGEST_SNAPSHOT_QUERY = DIGEST_SNAPSHOT_QUERY_BODY + "LIMIT {}\n".format(SNAPSHOT_ROW_LIMIT)

DIGEST_SNAPSHOT_QUERY_TRUNCATED = DIGEST_SNAPSHOT_QUERY_BODY + (
    "ORDER BY `count_star` DESC\n    LIMIT {}\n".format(SNAPSHOT_ROW_LIMIT)
)

DIGEST_TEXT_QUERY = """\
    SELECT `digest`,
           MIN(`digest_text`) AS `digest_text`
    FROM performance_schema.events_statements_summary_by_digest
    WHERE `digest` IN ({placeholders})
    GROUP BY `digest`
    """

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


def digest_key(row: Row) -> DigestKey:
    return row['schema_name'], row['digest']


def prepared_key(row: Row) -> PreparedKey:
    return PREPARED_STATEMENT_SOURCE, row['schema_name'], row['_dd_statement_id'], row['query_signature']


def classify_digest_text(text: str) -> TextKind:
    if text.lower().startswith('explain'):
        return TextKind.EXCLUDED
    return TextKind.STATEMENT


class MySQLStatementMetricsV2(MySQLStatementMetrics):
    """Collect statement metrics by resolving text only for digests that executed."""

    def __init__(self, check, config, connection_args_provider, uses_managed_auth=False):
        super().__init__(check, config, connection_args_provider, uses_managed_auth)

        if is_affirmative(config.statement_metrics_config.get('only_query_recent_statements', False)):
            self.log.warning(
                "only_query_recent_statements has no effect when incremental_query_metrics is enabled, "
                "because incremental collection requires a complete counter snapshot"
            )

        self._query_stats: QueryStats[DigestKey] = QueryStats(
            counter_columns=METRICS_COLUMNS,
            key=digest_key,
            execution_indicators=frozenset({'count_star'}),
        )
        self._prepared_query_stats: QueryStats[PreparedKey] = QueryStats(
            counter_columns=METRICS_COLUMNS,
            key=prepared_key,
            execution_indicators=frozenset({'count_star'}),
        )
        self._obfuscation_lookup: ObfuscationLookup[str] = ObfuscationLookup(
            maxsize=DEFAULT_DIGESTS_SIZE,
            obfuscate_options=self._obfuscate_options,
            log_unobfuscated_queries=config.log_unobfuscated_queries,
        )
        self._statement_count = None
        self._statement_count_updated_at = 0.0

    def shutdown(self) -> None:
        super().shutdown()
        self._query_stats = None
        self._prepared_query_stats = None
        self._obfuscation_lookup = None

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _collect_per_statement_metrics(self, tags: list[str]) -> list[Row]:
        self._get_statement_count(tags)
        self._sync_cache_size()

        snapshot_rows = self._query_digest_snapshot()
        self._check.gauge(
            "dd.mysql.statement_metrics.query_rows",
            len(snapshot_rows),
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

        delta = self._query_stats.diff(snapshot_rows)
        live_digests = {row['digest'] for row in snapshot_rows if row['digest'] is not None}
        changed_digests = {digest for _schema_name, digest in delta.changed_keys if digest is not None}

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

        obfuscations = self._resolve_obfuscations(live_digests, changed_digests, tags)
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

    def _sync_cache_size(self) -> None:
        digests_size = self._check.global_variables.performance_schema_digests_size
        maxsize = digests_size if digests_size and digests_size > 0 else DEFAULT_DIGESTS_SIZE
        if self._obfuscation_lookup.maxsize != maxsize:
            self._obfuscation_lookup.maxsize = maxsize

    def _get_statement_count(self, tags: list[str]) -> None:
        now = time.monotonic()
        if self._statement_count is None or now - self._statement_count_updated_at >= STATEMENT_COUNT_REFRESH_INTERVAL:
            self._raise_if_cancelled()
            with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
                cursor.execute(STATEMENT_COUNT_QUERY)
                rows = cursor.fetchall() or []
            if not rows:
                return
            self._statement_count = rows[0]['count']
            self._statement_count_updated_at = now

        self._check.gauge(
            "dd.mysql.statement_metrics.events_statements_summary_by_digest.total_rows",
            self._statement_count,
            tags=tags + self._check._get_debug_tags(),
            hostname=self._check.resolved_hostname,
        )

    def _snapshot_query(self) -> str:
        digests_size = self._check.global_variables.performance_schema_digests_size
        if digests_size is None or digests_size <= 0 or digests_size > SNAPSHOT_ROW_LIMIT:
            return DIGEST_SNAPSHOT_QUERY_TRUNCATED
        return DIGEST_SNAPSHOT_QUERY

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _query_digest_snapshot(self) -> list[Row]:
        self._raise_if_cancelled()
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(self._snapshot_query())
            return cursor.fetchall() or []

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _fetch_digest_texts(self, digests: set[str]) -> dict[str, str]:
        texts: dict[str, str] = {}
        if not digests:
            return texts

        try:
            with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
                for chunk in get_list_chunks(sorted(digests), DIGEST_TEXT_BATCH_SIZE):
                    self._raise_if_cancelled()
                    query = DIGEST_TEXT_QUERY.format(placeholders=', '.join(['%s'] * len(chunk)))
                    cursor.execute(query, chunk)
                    for row in cursor.fetchall() or []:
                        texts[row['digest']] = row['digest_text']
        except pymysql.err.DatabaseError as e:
            self._log.warning("Failed to fetch digest text for %d digests: %s", len(digests), e)
        return texts

    @tracked_method(agent_check_getter=attrgetter('_check'), track_result_length=True)
    def _query_prepared_statements(self) -> list[Row]:
        self._raise_if_cancelled()
        with closing(self._get_db_connection().cursor(CommenterDictCursor)) as cursor:
            cursor.execute(PREPARED_STATEMENTS_QUERY)
            return cursor.fetchall() or []

    def _resolve_obfuscations(
        self, live_digests: set[str], changed_digests: set[str], tags: list[str]
    ) -> dict[str, ObfuscationResult]:
        result = resolve_obfuscations(
            lookup=self._obfuscation_lookup,
            live_keys=live_digests,
            changed_keys=changed_digests,
            fetch_texts=self._fetch_digest_texts,
            classify=classify_digest_text,
        )
        self._emit_resolve_stats(result.stats, tags)
        return result.results

    def _emit_resolve_stats(self, stats: ResolveStats, tags: list[str]) -> None:
        metric_tags = tags + self._check._get_debug_tags()
        for name, value in (
            ("hits", stats.hits),
            ("misses", stats.misses),
            ("fetched", stats.fetched),
            ("ignored", stats.ignored),
            ("failed", stats.failed),
            ("dropped", stats.dropped),
        ):
            self._check.gauge(
                "dd.mysql.statement_metrics.lookup.{}".format(name),
                value,
                tags=metric_tags,
                hostname=self._check.reported_hostname,
            )

    def _assemble_digest_rows(
        self, derivative_rows: list[Row], obfuscations: dict[str, ObfuscationResult]
    ) -> list[Row]:
        assembled: list[Row] = []
        for row in derivative_rows:
            digest = row['digest']
            if digest is None:
                out = dict(row)
                out['digest_text'] = None
                out['query_signature'] = None
                out['dd_tables'] = None
                out['dd_commands'] = None
                out['dd_comments'] = None
                assembled.append(out)
                continue

            obfuscation = obfuscations.get(digest)
            if obfuscation is None:
                continue
            out = dict(row)
            out['digest_text'] = obfuscation.obfuscated_query
            out['query_signature'] = obfuscation.query_signature
            out['dd_tables'] = obfuscation.tables
            out['dd_commands'] = obfuscation.commands
            out['dd_comments'] = obfuscation.comments
            assembled.append(out)
        return assembled

    def _collect_prepared_statement_rows(self) -> list[Row]:
        if not self.collect_prepared_statements:
            return []
        rows = self._normalize_prepared_statements(self._query_prepared_statements())
        return self._prepared_query_stats.diff(rows).derivative_rows

    def _normalize_prepared_statements(self, rows: list[Row]) -> list[Row]:
        normalized_rows: list[Row] = []
        for row in rows:
            text = row['digest_text']
            if text is None or classify_digest_text(text) is TextKind.EXCLUDED:
                continue
            result = obfuscate_statement(
                text,
                self._obfuscate_options,
                self._config.log_unobfuscated_queries,
            )
            if result is None:
                continue
            normalized_row = dict(row)
            normalized_row['digest_text'] = result.obfuscated_query
            normalized_row['query_signature'] = result.query_signature
            normalized_row['dd_tables'] = result.tables
            normalized_row['dd_commands'] = result.commands
            normalized_row['dd_comments'] = result.comments
            normalized_rows.append(normalized_row)
        return normalized_rows
