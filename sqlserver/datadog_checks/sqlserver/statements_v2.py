# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from cachetools import LRUCache

from datadog_checks.base.utils.db.query_metrics import QueryStats
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION
from datadog_checks.sqlserver.statements import (
    SQL_SERVER_QUERY_METRICS_COLUMNS,
    SqlserverStatementMetrics,
    _hash_to_hex,
    _row_key,
    agent_check_getter,
)
from datadog_checks.sqlserver.utils import is_azure_sql_database, raise_if_cancelled

Row = dict[str, Any]

GroupKey = tuple[bytes, bytes, int | None, int | None]
"""(query_hash, query_plan_hash, dbid, sproc_object_id): the aggregation key of the counter snapshot."""

# The v1 statement metrics queries without the `dm_exec_sql_text` cross apply. The aggregation, lookback filter and row
# limit are v1's, so the counters are too. In place of `plan_handle_and_offsets` they return `statement_key`, which
# appends the plan's creation time; the handle and offsets come first and have a fixed length, so the greatest key is
# that of the statement v1 reports, and starts with v1's value.
STATEMENT_COUNTERS_QUERY = """\
with qstats as (
    select
        qs.query_hash,
        qs.query_plan_hash,
        qs.last_execution_time,
        qs.last_elapsed_time,
        qs.creation_time,
        CONCAT(
            CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1)) as plan_handle_and_offsets,
           (select value from sys.dm_exec_plan_attributes(qs.plan_handle) where attribute = 'dbid') as dbid,
           eps.object_id as sproc_object_id,
           {query_metrics_columns}
    from sys.dm_exec_query_stats qs
    left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
),
qstats_aggr as (
    select
        query_hash,
        query_plan_hash,
        CAST(qs.dbid as int) as dbid,
        D.name as database_name,
        max(CONCAT(
            plan_handle_and_offsets, CONVERT(VARCHAR(18), CONVERT(binary(8), creation_time), 1))) as statement_key,
        max(last_execution_time) as last_execution_time,
        max(last_elapsed_time) as last_elapsed_time,
        sproc_object_id,
        {query_metrics_column_sums}
    from qstats qs
    left join sys.databases D on qs.dbid = D.database_id
    group by query_hash, query_plan_hash, qs.dbid, D.name, sproc_object_id
)
select TOP {limit} * from qstats_aggr
where DATEADD(ms, last_elapsed_time / 1000, last_execution_time) > dateadd(second, -?, getdate())
"""

STATEMENT_COUNTERS_QUERY_AZURE_SQL_DATABASE = """\
with qstats as (
    select
        qs.query_hash,
        qs.query_plan_hash,
        qs.last_execution_time,
        qs.last_elapsed_time,
        qs.creation_time,
        CONCAT(
            CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
            CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1)) as plan_handle_and_offsets,
           (select value from sys.dm_exec_plan_attributes(qs.plan_handle) where attribute = 'dbid') as dbid,
           eps.object_id as sproc_object_id,
           {query_metrics_columns}
    from sys.dm_exec_query_stats qs
    left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
),
qstats_aggr as (
    select
        query_hash,
        query_plan_hash,
        CAST(qs.dbid as int) as dbid,
        DB_NAME(CAST(qs.dbid as int)) as database_name,
        max(CONCAT(
            plan_handle_and_offsets, CONVERT(VARCHAR(18), CONVERT(binary(8), creation_time), 1))) as statement_key,
        max(last_execution_time) as last_execution_time,
        max(last_elapsed_time) as last_elapsed_time,
        sproc_object_id,
        {query_metrics_column_sums}
    from qstats qs
    group by query_hash, query_plan_hash, qs.dbid, sproc_object_id
)
select TOP {limit} * from qstats_aggr
where DATEADD(ms, last_elapsed_time / 1000, last_execution_time) > dateadd(second, -?, getdate())
"""

STATEMENT_COUNTERS_QUERY_NO_AGGREGATES = """\
select TOP {limit}
    qs.query_hash,
    qs.query_plan_hash,
    max(CONCAT(
        CONVERT(VARCHAR(64), CONVERT(binary(64), qs.plan_handle), 1),
        CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_start_offset), 1),
        CONVERT(VARCHAR(10), CONVERT(varbinary(4), qs.statement_end_offset), 1),
        CONVERT(VARCHAR(18), CONVERT(binary(8), qs.creation_time), 1))) as statement_key,
    eps.object_id as sproc_object_id,
    {database_name_column}
    {query_metrics_column_sums}
from sys.dm_exec_query_stats qs
left join sys.dm_exec_procedure_stats eps ON eps.plan_handle = qs.plan_handle
where qs.last_execution_time > dateadd(second, -?, getdate())
group by qs.query_hash, qs.query_plan_hash, eps.object_id
"""

# Reads the text of the given statements the way v1 does inline: the handle and offsets are decoded from the statement
# key with the same expressions, and the procedure names are resolved from the group's object and database ids.
STATEMENT_TEXT_QUERY = """\
select
    k.statement_key,
    SUBSTRING(qt.text, (k.statement_start_offset / 2) + 1,
    ((CASE k.statement_end_offset
        WHEN -1 THEN DATALENGTH(qt.text)
        ELSE k.statement_end_offset END
            - k.statement_start_offset) / 2) + 1) AS statement_text,
    SUBSTRING(qt.text, 1, {proc_char_limit}) as text,
    qt.encrypted as is_encrypted{procedure_name_columns}
from (
    select
        statement_key,
        sproc_object_id,
        dbid,
        convert(varbinary(64), convert(binary(64), substring(statement_key, 1, 64), 1)) as plan_handle,
        convert(int, convert(varbinary(10), substring(statement_key, 64+1, 10), 1)) as statement_start_offset,
        convert(int, convert(varbinary(10), substring(statement_key, 64+11, 10), 1)) as statement_end_offset
    from (values {values}) as v(statement_key, sproc_object_id, dbid)
) k
cross apply sys.dm_exec_sql_text(k.plan_handle) qt
"""

PROCEDURE_NAME_COLUMNS = """,
    OBJECT_SCHEMA_NAME(k.sproc_object_id, k.dbid) as schema_name,
    OBJECT_NAME(k.sproc_object_id, k.dbid) as procedure_name"""

# `statement_key` is `plan_handle_and_offsets` (84 characters) followed by the plan's creation time (18).
PLAN_HANDLE_AND_OFFSETS_LENGTH = 84
STATEMENT_TEXT_QUERY_ROW = "(CAST(? AS varchar(102)), CAST(? AS int), CAST(? AS int))"

# SQL Server caches a plan per distinct statement text, and every VALUES length is a distinct text. Padding each
# batch up to one of these sizes keeps the text query to a handful of plan cache entries rather than one per miss
# count. Compile time grows with the number of VALUES rows, so batches larger than 64 cost more to compile than
# they save in round trips.
STATEMENT_TEXT_BATCH_SIZES = (1, 2, 4, 8, 16, 32, 64)


def _group_key(row: Row) -> GroupKey:
    return row['query_hash'], row['query_plan_hash'], row.get('dbid'), row['sproc_object_id']


def split_plan_handle_and_offsets(plan_handle_and_offsets: str) -> tuple[str, int, int]:
    """Decode `plan_handle_and_offsets` into the hex plan handle and the statement offsets.

    The value concatenates three style 1 hex literals: the plan handle cut to 64 characters, then the start and end
    offsets as 4-byte integers. This mirrors how v1 decodes it in SQL, where converting the handle back to
    `binary(64)` pads the bytes the cut dropped with zeros.
    """
    plan_handle = bytes.fromhex(plan_handle_and_offsets[2:64]).ljust(64, b'\x00')
    start = int.from_bytes(bytes.fromhex(plan_handle_and_offsets[66:74]), 'big', signed=True)
    end = int.from_bytes(bytes.fromhex(plan_handle_and_offsets[76:84]), 'big', signed=True)
    return _hash_to_hex(plan_handle), start, end


def padded_batches(keys: list[str]) -> Iterator[list[str]]:
    """Split *keys* into batches padded, by repeating their last key, to one of `STATEMENT_TEXT_BATCH_SIZES`."""
    max_size = STATEMENT_TEXT_BATCH_SIZES[-1]
    for start in range(0, len(keys), max_size):
        batch = keys[start : start + max_size]
        size = next(s for s in STATEMENT_TEXT_BATCH_SIZES if s >= len(batch))
        yield batch + [batch[-1]] * (size - len(batch))


class SqlserverStatementMetricsV2(SqlserverStatementMetrics):
    """Collects query metrics using change detection and cached obfuscation.

    v1 reads and obfuscates the text of every statement in the lookback window on every collection. Each collection
    here instead:

      1. Reads the counters of the statements in the lookback window, without their text.
      2. Diffs them against the previous snapshot to find the statements that executed.
      3. Resolves those statements against a cache of their text-derived fields, reading and obfuscating the text of
         the misses.
      4. Merges the rows on the v1 row key and hands them to the unchanged v1 payload and plan collection.

    The cache is keyed on `statement_key`. Its handle and offsets name one statement in one cached plan, but altering a
    procedure compiles the new text under the same handle, and the same offsets wherever a statement's length did not
    change. The plan's creation time tells them apart, so an entry can become unreachable but never wrong; a recompile
    costs one more read. Entries are per key rather than per query signature because the procedure fields differ
    between statements that obfuscate to the same text.
    """

    def __init__(self, check, config):
        super().__init__(check, config)
        self._query_stats: QueryStats[GroupKey] = QueryStats(
            counter_columns=SQL_SERVER_QUERY_METRICS_COLUMNS,
            key=_group_key,
            execution_indicators=frozenset({'execution_count'}),
        )
        # None marks text that cannot be obfuscated, so it is not read again. The row limit bounds the live keys.
        self._statement_cache: LRUCache[str, Row | None] = LRUCache(maxsize=max(self.dm_exec_query_stats_row_limit, 1))
        # v1 resolves procedure names only when it aggregates per database, since resolving them needs the dbid.
        self._procedure_name_columns = "" if self.disable_secondary_tags else PROCEDURE_NAME_COLUMNS
        self._statement_text_queries: dict[int, str] = {}

    def _get_statement_metrics_query_cached(self, cursor):
        if self._statement_metrics_query:
            return self._statement_metrics_query
        available_columns = self._get_available_query_metrics_columns(cursor, SQL_SERVER_QUERY_METRICS_COLUMNS)

        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
        database_name_column = ""
        if self.disable_secondary_tags:
            statements_query = STATEMENT_COUNTERS_QUERY_NO_AGGREGATES
            if is_azure_sql_database(engine_edition):
                # Same reasoning as v1: the check connects to a single database on Azure SQL Database, and resolving a
                # dbid would need `sys.dm_exec_plan_attributes`, which this setting avoids.
                database_name_column = "DB_NAME() as database_name,"
        elif is_azure_sql_database(engine_edition):
            statements_query = STATEMENT_COUNTERS_QUERY_AZURE_SQL_DATABASE
        else:
            statements_query = STATEMENT_COUNTERS_QUERY

        self._statement_metrics_query = statements_query.format(
            query_metrics_columns=', '.join(['qs.{} as {}'.format(col, col) for col in available_columns]),
            query_metrics_column_sums=', '.join(['sum(qs.{}) as {}'.format(c, c) for c in available_columns]),
            limit=self.dm_exec_query_stats_row_limit,
            database_name_column=database_name_column,
        )
        return self._statement_metrics_query

    def _get_statement_text_query(self, batch_size: int) -> str:
        query = self._statement_text_queries.get(batch_size)
        if query is None:
            query = STATEMENT_TEXT_QUERY.format(
                proc_char_limit=self._config.stored_procedure_characters_limit,
                procedure_name_columns=self._procedure_name_columns,
                values=', '.join([STATEMENT_TEXT_QUERY_ROW] * batch_size),
            )
            self._statement_text_queries[batch_size] = query
        return query

    def _collect_metrics_rows(self, cursor):
        snapshot = [
            row for row in self._load_raw_query_metrics_rows(cursor) if self._should_include_query_metrics_row(row)
        ]
        if not snapshot:
            # Like v1, keep the baseline rather than forget every statement, so their next executions are reported.
            return []

        delta = self._query_stats.diff(snapshot)
        self._check.gauge("dd.sqlserver.statements.snapshot.rows", len(snapshot), **self._check.debug_stats_kwargs())
        self._check.gauge(
            "dd.sqlserver.statements.delta.derivative_rows",
            len(delta.derivative_rows),
            **self._check.debug_stats_kwargs(),
        )

        # Resolve even when nothing changed: it also drops the entries of statements that left the snapshot.
        live_keys = {row['statement_key'] for row in snapshot}
        resolved = self._resolve_statements(cursor, live_keys, delta.derivative_rows)
        return self._assemble_rows(delta.derivative_rows, resolved)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _resolve_statements(self, cursor, live_keys: set[str], derivative_rows: list[Row]) -> dict[str, Row]:
        """Return the text-derived fields of *derivative_rows* by `statement_key`, reading only cache misses."""
        stale = self._statement_cache.keys() - live_keys
        for key in stale:
            del self._statement_cache[key]

        resolved: dict[str, Row] = {}
        misses: dict[str, Row] = {}
        ignored = 0
        for row in derivative_rows:
            key = row['statement_key']
            if key not in self._statement_cache:
                misses[key] = row
                continue
            fields = self._statement_cache[key]
            if fields is None:
                ignored += 1
            else:
                resolved[key] = fields
        hits = len(resolved)

        texts = self._fetch_statement_texts(cursor, misses) if misses else {}
        failed = 0
        for key, text_row in texts.items():
            fields = self._normalize_statement_text(text_row)
            self._statement_cache[key] = fields
            if fields is None:
                failed += 1
            else:
                resolved[key] = fields

        for name, value in (
            ("hits", hits),
            ("misses", len(misses)),
            ("fetched", len(texts)),
            ("failed", failed),
            ("ignored", ignored),
            ("dropped", len(stale)),
        ):
            self._check.gauge(
                "dd.sqlserver.statements.lookup.{}".format(name), value, **self._check.debug_stats_kwargs()
            )
        self._check.gauge(
            "dd.sqlserver.statements.statement_cache.len",
            len(self._statement_cache),
            **self._check.debug_stats_kwargs(),
        )
        return resolved

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _fetch_statement_texts(self, cursor, misses: dict[str, Row]) -> dict[str, Row]:
        """Read the statement and batch text of *misses*, keyed on `statement_key`.

        A statement whose plan left the plan cache is absent from the result and stays a miss. A failed read is
        reported and returns what was read, so the collection still reports the cached statements.
        """
        texts: dict[str, Row] = {}
        try:
            for batch in padded_batches(list(misses)):
                raise_if_cancelled(self._cancel_event)
                params = []
                for key in batch:
                    params.extend((key, misses[key]['sproc_object_id'], misses[key].get('dbid')))
                cursor.execute(self._get_statement_text_query(len(batch)), tuple(params))
                columns = [i[0] for i in cursor.description]
                for values in cursor.fetchall():
                    text_row = dict(zip(columns, values))
                    key = text_row.pop('statement_key')
                    text_row['sproc_object_id'] = misses[key]['sproc_object_id']
                    texts[key] = text_row
        except Exception as e:
            # A connection closed during cancellation may surface as a database error.
            raise_if_cancelled(self._cancel_event)
            self.log.warning("Failed to read the text of %d statements: %s", len(misses) - len(texts), e)
            self._check.count(
                "dd.sqlserver.statements.error",
                1,
                **self._check.debug_stats_kwargs(tags=["error:fetch-statement-text-{}".format(type(e))]),
            )
        return texts

    def _normalize_statement_text(self, text_row: Row) -> Row | None:
        """Derive the fields a statement's text contributes to its rows, or None if it cannot be obfuscated."""
        text_fields = self._normalize_query_text(text_row)
        if text_fields is None:
            return None
        fields = {'is_encrypted': text_row['is_encrypted']}
        if 'schema_name' in text_row:
            fields['schema_name'] = text_row['schema_name']
            fields['procedure_name'] = text_row['procedure_name']
        fields.update(text_fields)
        return fields

    def _assemble_rows(self, derivative_rows: list[Row], resolved: dict[str, Row]) -> list[Row]:
        """Complete the derivative rows with their text-derived fields and merge them on the v1 row key.

        v1 sums the rows sharing that key before diffing. Summing their deltas gives the same result while the plans
        behind a key are stable, and does not drop the key when one of them leaves the snapshot.
        """
        merged: dict[tuple, Row] = {}
        for row in derivative_rows:
            statement_key = row.pop('statement_key')
            fields = resolved.get(statement_key)
            if fields is None:
                continue
            row['plan_handle_and_offsets'] = statement_key[:PLAN_HANDLE_AND_OFFSETS_LENGTH]
            row['plan_handle'], row['statement_start_offset'], row['statement_end_offset'] = (
                split_plan_handle_and_offsets(row['plan_handle_and_offsets'])
            )
            row['query_hash'] = _hash_to_hex(row['query_hash'])
            row['query_plan_hash'] = _hash_to_hex(row['query_plan_hash'])
            row.update(fields)

            key = _row_key(row)
            existing = merged.get(key)
            if existing is None:
                merged[key] = row
                continue
            for col in SQL_SERVER_QUERY_METRICS_COLUMNS:
                if col in row:
                    existing[col] = existing.get(col, 0) + row[col]
        return list(merged.values())
