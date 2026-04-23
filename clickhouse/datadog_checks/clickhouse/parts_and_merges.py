# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collects MergeTree storage health data from ClickHouse system tables.

Emits two outputs each collection cycle:
  1. Gauge metrics (self._check.gauge) for trend dashboards and alerting.
  2. A per-cycle row-level event payload via database_monitoring_query_activity,
     consumed by dbm-events-processor under dbm_type="storage_health".
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import PartsAndMerges

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

DBM_TYPE = "storage_health"

# system.detached_parts.reason values that indicate actual data integrity problems
# (ClickHouse quarantined the part). NULL/empty reason means operator ran ALTER TABLE ... DETACH
# and is routine. Anything else (noquorum, ignored, clone, ...) is unusual but not corruption.
_CORRUPTED_DETACH_REASONS = frozenset(['broken', 'unexpected', 'covered-by-broken', 'broken-on-start'])


def _classify_detach_reason(reason: str | None) -> str:
    if not reason:
        return 'manual'
    if reason in _CORRUPTED_DETACH_REASONS:
        return 'corrupted'
    return 'other'


PARTS_AGGREGATED_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    count()                              AS active_part_count,
    countIf(level = 0)                   AS level_zero_count,
    countIf(part_type = 'Compact')       AS compact_parts,
    countIf(part_type = 'Wide')          AS wide_parts,
    sum(rows)                            AS total_rows,
    sum(bytes_on_disk)                   AS bytes_on_disk,
    sum(data_compressed_bytes)           AS compressed_bytes,
    sum(data_uncompressed_bytes)         AS uncompressed_bytes,
    max(level)                           AS max_merge_level,
    avg(level)                           AS avg_merge_level,
    min(modification_time)               AS oldest_part_time,
    max(modification_time)               AS newest_part_time
FROM {parts_table}
WHERE active = 1
  AND database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
GROUP BY database, table, server_node
ORDER BY active_part_count DESC
LIMIT {max_parts_rows}
"""

PARTS_BY_PARTITION_QUERY = """\
SELECT
    database,
    table,
    partition,
    hostName() AS server_node,
    count()                              AS active_part_count,
    countIf(level = 0)                   AS level_zero_count,
    countIf(part_type = 'Compact')       AS compact_parts,
    countIf(part_type = 'Wide')          AS wide_parts,
    sum(rows)                            AS total_rows,
    sum(bytes_on_disk)                   AS bytes_on_disk,
    sum(data_compressed_bytes)           AS compressed_bytes,
    sum(data_uncompressed_bytes)         AS uncompressed_bytes,
    max(level)                           AS max_merge_level,
    avg(level)                           AS avg_merge_level,
    min(modification_time)               AS oldest_part_time,
    max(modification_time)               AS newest_part_time
FROM {parts_table}
WHERE active = 1
  AND database NOT IN ('system', 'INFORMATION_SCHEMA', 'information_schema')
GROUP BY database, table, partition, server_node
ORDER BY active_part_count DESC
LIMIT {max_parts_rows}
"""

DETACHED_PARTS_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    reason,
    count() AS detached_count
FROM {detached_parts_table}
GROUP BY database, table, server_node, reason
LIMIT {max_detached_parts_rows}
"""

MERGES_QUERY = """\
SELECT
    database,
    table,
    partition_id,
    hostName() AS server_node,
    elapsed,
    progress,
    num_parts,
    is_mutation,
    merge_type,
    merge_algorithm,
    total_size_bytes_compressed,
    bytes_read_uncompressed,
    rows_read,
    bytes_written_uncompressed,
    rows_written,
    memory_usage,
    source_part_names,
    result_part_name
FROM {merges_table}
"""

MUTATIONS_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    mutation_id,
    command,
    create_time,
    is_done,
    parts_to_do,
    latest_failed_part,
    latest_fail_time,
    latest_fail_reason
FROM {mutations_table}
WHERE NOT is_done
ORDER BY create_time ASC
LIMIT {max_mutations_rows}
"""

MUTATIONS_AGGREGATED_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    count()                                  AS in_progress,
    countIf(latest_fail_reason IS NOT NULL)  AS failing,
    sum(parts_to_do)                         AS parts_remaining,
    min(create_time)                         AS oldest_create_time
FROM {mutations_table}
WHERE NOT is_done
GROUP BY database, table, server_node
"""

REPLICATION_QUEUE_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    type,
    position,
    is_currently_executing,
    num_tries,
    last_exception,
    last_exception_time,
    num_postponed,
    postpone_reason,
    parts_to_merge
FROM {replication_queue_table}
ORDER BY position ASC
LIMIT {max_replication_queue_rows}
"""

REPLICATION_QUEUE_AGGREGATED_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    count()                                  AS depth,
    countIf(num_tries > {stuck_threshold})   AS stuck
FROM {replication_queue_table}
GROUP BY database, table, server_node
"""

#   parts_to_delay_insert  — ClickHouse starts throttling INSERTs at this count.
#   parts_to_throw_insert  — ClickHouse rejects INSERTs at this count.
# Per-table SETTINGS overrides are not surfaced here; this returns only the server defaults.
THRESHOLDS_QUERY = """\
SELECT
    hostName() AS server_node,
    name,
    value
FROM {merge_tree_settings_table}
WHERE name IN ('parts_to_delay_insert', 'parts_to_throw_insert')
"""


def agent_check_getter(self):
    return self._check


class ClickhousePartsAndMerges(DBMAsyncJob):
    """
    Monitors MergeTree storage health by polling:
      - system.parts            — per-table part inventory
      - system.merges           — currently executing background merges
      - system.mutations        — pending ALTER UPDATE/DELETE operations
      - system.replication_queue — replication task backlog (ReplicatedMergeTree only)

    Produces gauges (trend data) and row-level events (dbm_type="storage_health").
    """

    def __init__(self, check: ClickhouseCheck, config: PartsAndMerges):
        collection_interval = config.collection_interval

        super(ClickhousePartsAndMerges, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled,
            dbms="clickhouse",
            min_collection_interval=check._config.min_collection_interval,
            expected_db_exceptions=(Exception,),
            job_name="parts-and-merges",
        )
        self._check = check
        self._config = config
        self._collection_interval = collection_interval
        self._tags_no_db: list[str] | None = None
        self.tags: list[str] | None = None

        self._include_partition_tag: bool = bool(config.table_metrics_include_partition_tag)
        self._max_tables: int = config.table_metrics_max_tables
        self._stalled_merge_threshold: int = config.stalled_merge_elapsed_threshold_seconds
        self._stuck_replication_num_tries: int = config.stuck_replication_num_tries

        self._db_client = None

        obfuscate_options = {
            'return_json_metadata': False,
            'collect_tables': False,
            'collect_commands': False,
            'collect_comments': False,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

    def cancel(self):
        super(ClickhousePartsAndMerges, self).cancel()
        self._close_db_client()

    def _close_db_client(self):
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing parts-and-merges client: %s", e)
            self._db_client = None

    def _get_debug_tags(self) -> list[str]:
        return list(self._tags_no_db) if self._tags_no_db else []

    def _execute_query(self, query: str) -> list:
        if self._db_client is None:
            self._db_client = self._check.create_dbm_client()
        try:
            return self._db_client.query(query).result_rows
        except OperationalError as e:
            self._log.warning("Connection error, will reconnect on next query: %s", e)
            self._close_db_client()
            raise

    def _collect_parts(self) -> list[dict]:
        if self._include_partition_tag:
            query_template = PARTS_BY_PARTITION_QUERY
        else:
            query_template = PARTS_AGGREGATED_QUERY
        query = query_template.format(
            parts_table=self._check.get_system_table('parts'),
            max_parts_rows=self._config.max_parts_rows,
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect parts")
            self._emit_error_count("collect-parts")
            return []

        result = []
        for row in rows:
            if self._include_partition_tag:
                (
                    database,
                    table,
                    partition,
                    server_node,
                    active_part_count,
                    level_zero_count,
                    compact_parts,
                    wide_parts,
                    total_rows,
                    bytes_on_disk,
                    compressed_bytes,
                    uncompressed_bytes,
                    max_merge_level,
                    avg_merge_level,
                    oldest_part_time,
                    newest_part_time,
                ) = row
            else:
                (
                    database,
                    table,
                    server_node,
                    active_part_count,
                    level_zero_count,
                    compact_parts,
                    wide_parts,
                    total_rows,
                    bytes_on_disk,
                    compressed_bytes,
                    uncompressed_bytes,
                    max_merge_level,
                    avg_merge_level,
                    oldest_part_time,
                    newest_part_time,
                ) = row
                partition = None
            result.append(
                {
                    'database': database,
                    'table': table,
                    'partition': partition,
                    'server_node': server_node,
                    'active_part_count': int(active_part_count),
                    'level_zero_count': int(level_zero_count),
                    'compact_parts': int(compact_parts),
                    'wide_parts': int(wide_parts),
                    'total_rows': int(total_rows),
                    'bytes_on_disk': int(bytes_on_disk),
                    'compressed_bytes': int(compressed_bytes),
                    'uncompressed_bytes': int(uncompressed_bytes),
                    'max_merge_level': int(max_merge_level),
                    'avg_merge_level': float(avg_merge_level),
                    'oldest_part_time': int(oldest_part_time.timestamp()) if oldest_part_time else None,
                    'newest_part_time': int(newest_part_time.timestamp()) if newest_part_time else None,
                }
            )
        return result

    def _collect_detached_parts(self) -> list[dict]:
        query = DETACHED_PARTS_QUERY.format(
            detached_parts_table=self._check.get_system_table('detached_parts'),
            max_detached_parts_rows=self._config.max_detached_parts_rows,
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect detached parts")
            self._emit_error_count("collect-detached-parts")
            return []

        result = []
        for row in rows:
            database, table, server_node, reason, detached_count = row
            reason_str = str(reason) if reason else None
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'reason': reason_str,
                    'reason_category': _classify_detach_reason(reason_str),
                    'detached_count': int(detached_count),
                }
            )
        return result

    def _collect_merges(self) -> list[dict]:
        query = MERGES_QUERY.format(merges_table=self._check.get_system_table('merges'))
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect merges")
            self._emit_error_count("collect-merges")
            return []

        result = []
        for row in rows:
            (
                database,
                table,
                partition_id,
                server_node,
                elapsed,
                progress,
                num_parts,
                is_mutation,
                merge_type,
                merge_algorithm,
                total_size_bytes_compressed,
                bytes_read_uncompressed,
                rows_read,
                bytes_written_uncompressed,
                rows_written,
                memory_usage,
                source_part_names,
                result_part_name,
            ) = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'partition_id': partition_id,
                    'server_node': server_node,
                    'elapsed': float(elapsed) if elapsed is not None else 0.0,
                    'progress': float(progress) if progress is not None else 0.0,
                    'num_parts': int(num_parts) if num_parts else 0,
                    'is_mutation': bool(is_mutation),
                    'merge_type': str(merge_type) if merge_type else None,
                    'merge_algorithm': str(merge_algorithm) if merge_algorithm else None,
                    'total_size_bytes_compressed': int(total_size_bytes_compressed)
                    if total_size_bytes_compressed
                    else 0,
                    'bytes_read_uncompressed': int(bytes_read_uncompressed) if bytes_read_uncompressed else 0,
                    'rows_read': int(rows_read) if rows_read else 0,
                    'bytes_written_uncompressed': int(bytes_written_uncompressed) if bytes_written_uncompressed else 0,
                    'rows_written': int(rows_written) if rows_written else 0,
                    'memory_usage': int(memory_usage) if memory_usage else 0,
                    'source_part_names': list(source_part_names) if source_part_names else [],
                    'result_part_name': str(result_part_name) if result_part_name else None,
                }
            )
        return result

    def _collect_mutations(self) -> list[dict]:
        query = MUTATIONS_QUERY.format(
            mutations_table=self._check.get_system_table('mutations'),
            max_mutations_rows=self._config.max_mutations_rows,
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect mutations")
            self._emit_error_count("collect-mutations")
            return []

        result = []
        for row in rows:
            (
                database,
                table,
                server_node,
                mutation_id,
                command,
                create_time,
                is_done,
                parts_to_do,
                latest_failed_part,
                latest_fail_time,
                latest_fail_reason,
            ) = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'mutation_id': mutation_id,
                    'command': self._obfuscate_mutation_command(command),
                    'create_time': int(create_time.timestamp()) if create_time else None,
                    'is_done': bool(is_done),
                    'parts_to_do': int(parts_to_do) if parts_to_do else 0,
                    'latest_failed_part': str(latest_failed_part) if latest_failed_part else None,
                    'latest_fail_time': int(latest_fail_time.timestamp()) if latest_fail_time else None,
                    'latest_fail_reason': str(latest_fail_reason) if latest_fail_reason else None,
                }
            )
        return result

    def _collect_mutations_aggregated(self) -> list[dict]:
        query = MUTATIONS_AGGREGATED_QUERY.format(
            mutations_table=self._check.get_system_table('mutations'),
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect mutation aggregates")
            self._emit_error_count("collect-mutations-aggregated")
            return []

        result = []
        for row in rows:
            database, table, server_node, in_progress, failing, parts_remaining, oldest_create_time = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'in_progress': int(in_progress),
                    'failing': int(failing),
                    'parts_remaining': int(parts_remaining) if parts_remaining else 0,
                    'oldest_create_time': int(oldest_create_time.timestamp()) if oldest_create_time else None,
                }
            )
        return result

    def _collect_replication_queue(self) -> list[dict]:
        query = REPLICATION_QUEUE_QUERY.format(
            replication_queue_table=self._check.get_system_table('replication_queue'),
            max_replication_queue_rows=self._config.max_replication_queue_rows,
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect replication queue")
            self._emit_error_count("collect-replication-queue")
            return []

        result = []
        for row in rows:
            (
                database,
                table,
                server_node,
                task_type,
                position,
                is_currently_executing,
                num_tries,
                last_exception,
                last_exception_time,
                num_postponed,
                postpone_reason,
                parts_to_merge,
            ) = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'type': str(task_type) if task_type else None,
                    'position': int(position) if position else 0,
                    'is_currently_executing': bool(is_currently_executing),
                    'num_tries': int(num_tries) if num_tries else 0,
                    'last_exception': str(last_exception) if last_exception else None,
                    'last_exception_time': int(last_exception_time.timestamp()) if last_exception_time else None,
                    'num_postponed': int(num_postponed) if num_postponed else 0,
                    'postpone_reason': str(postpone_reason) if postpone_reason else None,
                    'parts_to_merge': list(parts_to_merge) if parts_to_merge else [],
                }
            )
        return result

    def _collect_replication_queue_aggregated(self) -> list[dict]:
        query = REPLICATION_QUEUE_AGGREGATED_QUERY.format(
            replication_queue_table=self._check.get_system_table('replication_queue'),
            stuck_threshold=self._stuck_replication_num_tries,
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect replication queue aggregates")
            self._emit_error_count("collect-replication-queue-aggregated")
            return []

        result = []
        for row in rows:
            database, table, server_node, depth, stuck = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'depth': int(depth),
                    'stuck': int(stuck),
                }
            )
        return result

    def _collect_thresholds(self) -> list[dict]:
        """Fetch server-level parts_to_delay_insert / parts_to_throw_insert from system.merge_tree_settings."""
        query = THRESHOLDS_QUERY.format(
            merge_tree_settings_table=self._check.get_system_table('merge_tree_settings'),
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect MergeTree thresholds")
            self._emit_error_count("collect-thresholds")
            return []

        result = []
        for row in rows:
            server_node, name, value = row
            try:
                numeric_value = int(value)
            except (TypeError, ValueError):
                self._log.debug("Non-numeric MergeTree threshold value: %s=%r", name, value)
                continue
            result.append(
                {
                    'server_node': server_node,
                    'name': str(name),
                    'value': numeric_value,
                }
            )
        return result

    def _emit_gauges(
        self,
        parts: list[dict],
        merges: list[dict],
        mutations_aggregated: list[dict],
        replication_aggregated: list[dict],
        detached_parts: list[dict],
        thresholds: list[dict] | None = None,
    ) -> None:
        now = time.time()

        # --- Parts ---
        parts_agg: dict[tuple, dict] = defaultdict(
            lambda: {
                'active': 0,
                'level_zero': 0,
                'compact': 0,
                'wide': 0,
                'rows': 0,
                'bytes_on_disk': 0,
                'compressed_bytes': 0,
                'uncompressed_bytes': 0,
                'max_merge_level': 0,
                'oldest_part_time': None,
            }
        )
        for row in parts:
            server_node = row.get('server_node', '')
            if self._include_partition_tag:
                key = (row['database'], row['table'], server_node, row['partition'])
            else:
                key = (row['database'], row['table'], server_node)
            agg = parts_agg[key]
            agg['active'] += row['active_part_count']
            agg['level_zero'] += row.get('level_zero_count', 0)
            agg['compact'] += row.get('compact_parts', 0)
            agg['wide'] += row.get('wide_parts', 0)
            agg['rows'] += row['total_rows']
            agg['bytes_on_disk'] += row['bytes_on_disk']
            agg['compressed_bytes'] += row['compressed_bytes']
            agg['uncompressed_bytes'] += row['uncompressed_bytes']
            agg['max_merge_level'] = max(agg['max_merge_level'], row.get('max_merge_level', 0))
            oldest = row.get('oldest_part_time')
            if oldest is not None and (agg['oldest_part_time'] is None or oldest < agg['oldest_part_time']):
                agg['oldest_part_time'] = oldest

        sorted_parts = sorted(parts_agg.items(), key=lambda kv: kv[1]['active'], reverse=True)
        for key, agg in sorted_parts[: self._max_tables]:
            if self._include_partition_tag:
                database, table, server_node, partition = key
                tags = self.tags + [
                    f'database:{database}',
                    f'table:{table}',
                    f'server_node:{server_node}',
                    f'partition:{partition}',
                ]
            else:
                database, table, server_node = key
                tags = self.tags + [
                    f'database:{database}',
                    f'table:{table}',
                    f'server_node:{server_node}',
                ]
            self._check.gauge('table.parts.active', agg['active'], tags=tags)
            self._check.gauge('table.parts.level_zero', agg['level_zero'], tags=tags)
            self._check.gauge('table.parts.compact', agg['compact'], tags=tags)
            self._check.gauge('table.parts.wide', agg['wide'], tags=tags)
            self._check.gauge('table.parts.rows', agg['rows'], tags=tags)
            self._check.gauge('table.parts.bytes_on_disk', agg['bytes_on_disk'], tags=tags)
            self._check.gauge('table.parts.compressed_bytes', agg['compressed_bytes'], tags=tags)
            self._check.gauge('table.parts.uncompressed_bytes', agg['uncompressed_bytes'], tags=tags)
            self._check.gauge('table.parts.max_merge_level', agg['max_merge_level'], tags=tags)
            if agg['oldest_part_time'] is not None:
                self._check.gauge(
                    'table.parts.oldest_part_age_seconds',
                    now - agg['oldest_part_time'],
                    tags=tags,
                )

        # --- Merges ---
        merges_agg: dict[tuple, dict] = defaultdict(
            lambda: {
                'active': 0,
                'stalled': 0,
                'max_elapsed': 0.0,
                'memory_bytes': 0,
                'total_bytes': 0,
                'progress_sum': 0.0,
                'progress_count': 0,
            }
        )
        for row in merges:
            key = (row['database'], row['table'], row.get('server_node', ''))
            agg = merges_agg[key]
            agg['active'] += 1
            elapsed = row.get('elapsed', 0.0)
            if elapsed > self._stalled_merge_threshold:
                agg['stalled'] += 1
            if elapsed > agg['max_elapsed']:
                agg['max_elapsed'] = elapsed
            agg['memory_bytes'] += row.get('memory_usage', 0)
            agg['total_bytes'] += row.get('total_size_bytes_compressed', 0)
            agg['progress_sum'] += row.get('progress', 0.0)
            agg['progress_count'] += 1

        for (database, table, server_node), agg in merges_agg.items():
            tags = self.tags + [
                f'database:{database}',
                f'table:{table}',
                f'server_node:{server_node}',
            ]
            avg_progress = agg['progress_sum'] / agg['progress_count'] if agg['progress_count'] > 0 else 0.0
            self._check.gauge('merges.active', agg['active'], tags=tags)
            self._check.gauge('merges.stalled', agg['stalled'], tags=tags)
            self._check.gauge('merges.max_elapsed_seconds', agg['max_elapsed'], tags=tags)
            self._check.gauge('merges.memory_bytes', agg['memory_bytes'], tags=tags)
            self._check.gauge('merges.total_bytes', agg['total_bytes'], tags=tags)
            self._check.gauge('merges.avg_progress', avg_progress, tags=tags)

        # --- Mutations (server-side aggregated) ---
        for row in mutations_aggregated:
            tags = self.tags + [
                f'database:{row["database"]}',
                f'table:{row["table"]}',
                f'server_node:{row.get("server_node", "")}',
            ]
            oldest_create_time = row.get('oldest_create_time')
            oldest_age = now - oldest_create_time if oldest_create_time is not None else 0
            self._check.gauge('mutations.in_progress', row['in_progress'], tags=tags)
            self._check.gauge('mutations.failing', row['failing'], tags=tags)
            self._check.gauge('mutations.parts_remaining', row['parts_remaining'], tags=tags)
            self._check.gauge('mutations.oldest_age_seconds', oldest_age, tags=tags)

        # --- Replication queue (server-side aggregated) ---
        for row in replication_aggregated:
            tags = self.tags + [
                f'database:{row["database"]}',
                f'table:{row["table"]}',
                f'server_node:{row.get("server_node", "")}',
            ]
            self._check.gauge('replication.queue_depth', row['depth'], tags=tags)
            self._check.gauge('replication.stuck_tasks', row['stuck'], tags=tags)

        # --- Detached parts ---
        detached_agg: dict[tuple, dict] = defaultdict(
            lambda: {
                'total': 0,
                'manual': 0,
                'corrupted': 0,
                'other': 0,
            }
        )
        for row in detached_parts:
            key = (row['database'], row['table'], row.get('server_node', ''))
            agg = detached_agg[key]
            agg['total'] += row['detached_count']
            agg[row['reason_category']] += row['detached_count']

        for (database, table, server_node), agg in detached_agg.items():
            tags = self.tags + [
                f'database:{database}',
                f'table:{table}',
                f'server_node:{server_node}',
            ]
            self._check.gauge('table.detached_parts.count', agg['total'], tags=tags)
            self._check.gauge('table.detached_parts.manual', agg['manual'], tags=tags)
            self._check.gauge('table.detached_parts.corrupted', agg['corrupted'], tags=tags)
            self._check.gauge('table.detached_parts.other', agg['other'], tags=tags)

        # --- Thresholds (server-level MergeTree settings) ---
        for row in thresholds or []:
            server_node = row.get('server_node', '')
            tags = self.tags + [f'server_node:{server_node}']
            if row['name'] == 'parts_to_delay_insert':
                self._check.gauge('parts.threshold.delay_insert', row['value'], tags=tags)
            elif row['name'] == 'parts_to_throw_insert':
                self._check.gauge('parts.threshold.throw_insert', row['value'], tags=tags)

    def _emit_events(
        self,
        parts: list[dict],
        merges: list[dict],
        mutations: list[dict],
        replication_queue: list[dict],
        detached_parts: list[dict],
        thresholds: list[dict] | None = None,
    ) -> None:
        """Emit a per-cycle row-level payload consumed by dbm-events-processor."""
        now_ms = int(time.time() * 1000)
        payload = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddagenthostname": self._check.agent_hostname,
            "dbms": "clickhouse",
            "ddsource": "clickhouse",
            "dbms_version": self._check.dbms_version,
            "dbm_type": DBM_TYPE,
            "ddtags": list(self._tags_no_db) if self._tags_no_db else [],
            "timestamp": now_ms,
            "collection_interval": self._collection_interval,
            "clickhouse": {
                "top_tables_by_parts": parts,
                "active_merges": merges,
                "pending_mutations": mutations,
                "replication_queue": replication_queue,
                "detached_parts": detached_parts,
                "thresholds": thresholds or [],
            },
        }
        self._check.database_monitoring_query_activity(json.dumps(payload, default=default_json_event_encoding))

    def _obfuscate_mutation_command(self, command: str) -> str | None:
        if not command:
            return None
        try:
            return obfuscate_sql_with_metadata(command, self._obfuscate_options)['query']
        except Exception as e:
            self._log.debug("Mutation command obfuscation failed, dropping literal: %s", e)
            return None

    def _emit_error_count(self, error_label: str) -> None:
        base_tags = self.tags if self.tags else []
        self._check.count(
            "dd.clickhouse.parts_and_merges.error",
            1,
            tags=base_tags + [f"error:{error_label}"] + self._get_debug_tags(),
            raw=True,
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_emit(self):
        start_time = time.time()

        parts = self._collect_parts()
        merges = self._collect_merges()
        mutations = self._collect_mutations()
        mutations_aggregated = self._collect_mutations_aggregated()
        replication_queue = self._collect_replication_queue()
        replication_aggregated = self._collect_replication_queue_aggregated()
        detached_parts = self._collect_detached_parts()
        thresholds = self._collect_thresholds()

        self._emit_gauges(parts, merges, mutations_aggregated, replication_aggregated, detached_parts, thresholds)
        self._emit_events(parts, merges, mutations, replication_queue, detached_parts, thresholds)

        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.clickhouse.parts_and_merges.collect.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._log.debug(
            "parts_and_merges cycle: parts=%d merges=%d mutations=%d "
            "replication_queue=%d detached_parts=%d elapsed_ms=%.2f",
            len(parts),
            len(merges),
            len(mutations),
            len(replication_queue),
            len(detached_parts),
            elapsed_ms,
        )

    def run_job(self):
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        try:
            self._collect_and_emit()
        except Exception as e:
            self._log.exception("parts_and_merges run_job failed: %s", e)
            self._emit_error_count("run-job")
