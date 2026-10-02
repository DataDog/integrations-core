# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from datetime import datetime
from time import time
from typing import TYPE_CHECKING

import ibm_db

from datadog_checks.base.utils.db.query_metrics import ObfuscationLookup, QueryStats, TextKind, resolve_obfuscations
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.format import json

from . import queries

if TYPE_CHECKING:
    from .ibm_db2 import IbmDb2Check

StatementKey = tuple[int, str, datetime]
OBFUSCATION_CACHE_SIZE = 10000
TEXT_FETCH_BATCH_SIZE = 100
MAX_PAYLOAD_SIZE = 20_000_000
COUNTER_COLUMNS = frozenset({'num_exec_with_metrics', 'coord_stmt_exec_time'})


class Db2QueryError(Exception):
    """A query-metrics database operation failed."""


def statement_key(row: dict) -> StatementKey:
    # Recompilation or cache eviction must not join a new section to an old counter baseline.
    return row['member'], row['executable_id'], row['insert_timestamp']


def classify_query_text(text: str) -> TextKind:
    if text.lstrip().startswith(queries.DDIGNORE_COMMENT):
        return TextKind.EXCLUDED
    return TextKind.STATEMENT


class Db2StatementMetrics(DBMAsyncJob):
    """Collect counter deltas, resolving SQL text only for changed sections missing from the cache."""

    def __init__(self, check: IbmDb2Check, collection_interval: float, run_sync: bool = False):
        super().__init__(
            check,
            config_host=check.reported_hostname,
            min_collection_interval=check.instance.get('min_collection_interval', 15),
            dbms=check.dbms,
            rate_limit=1 / collection_interval,
            run_sync=run_sync,
            expected_db_exceptions=(Db2QueryError,),
            shutdown_callback=self._close_connection,
            job_name='query-metrics',
        )
        self._collection_interval = collection_interval
        self._conn = None
        self._query_stats: QueryStats[StatementKey] = QueryStats(
            counter_columns=COUNTER_COLUMNS,
            key=statement_key,
            execution_indicators={'num_exec_with_metrics'},
        )
        self._obfuscation_lookup: ObfuscationLookup[StatementKey] = ObfuscationLookup(
            maxsize=OBFUSCATION_CACHE_SIZE,
            obfuscate_options=json.encode({'return_json_metadata': True}),
        )

    def _close_connection(self) -> None:
        self._query_stats.reset()
        if self._conn is not None:
            connection, self._conn = self._conn, None
            ibm_db.close(connection)

    def shutdown(self) -> None:
        try:
            self._close_connection()
        finally:
            self._obfuscation_lookup.retain(set())
            self._check = None

    def _execute_query(self, query: str, params: tuple = ()) -> list[dict]:
        if self._cancel_event.is_set():
            raise Db2QueryError('Query metrics collection cancelled')
        if self._conn is None:
            self._conn = self._check.get_connection()
        if self._conn is None:
            raise Db2QueryError('Unable to connect for query metrics collection')

        statement = None
        try:
            if params:
                statement = ibm_db.prepare(self._conn, query)
                ibm_db.execute(statement, params)
            else:
                statement = ibm_db.exec_immediate(self._conn, query)
            rows = []
            while not self._cancel_event.is_set():
                row = ibm_db.fetch_assoc(statement)
                if row is False:
                    return rows
                rows.append(row)
            raise Db2QueryError('Query metrics collection cancelled')
        except Exception as e:
            # ibm_db exposes native errors as generic Exception rather than a database-specific type.
            raise Db2QueryError(str(e)) from e
        finally:
            if statement is not None:
                ibm_db.free_stmt(statement)

    def _fetch_query_texts(self, keys: set[StatementKey]) -> dict[StatementKey, str]:
        texts = {}
        executable_ids = sorted({key[1] for key in keys})
        for start in range(0, len(executable_ids), TEXT_FETCH_BATCH_SIZE):
            batch = executable_ids[start : start + TEXT_FETCH_BATCH_SIZE]
            query = queries.STATEMENT_TEXT.format(placeholders=', '.join('?' for _ in batch))
            for row in self._execute_query(query, tuple(batch)):
                key = statement_key(row)
                # A section may have been replaced between the counter snapshot and text lookup.
                if key in keys:
                    texts[key] = row['stmt_text']
        return texts

    def _collect_rows(self) -> list[dict]:
        snapshot = self._execute_query(queries.STATEMENT_METRICS)
        delta = self._query_stats.diff(snapshot)
        resolved = resolve_obfuscations(
            lookup=self._obfuscation_lookup,
            live_keys={statement_key(row) for row in snapshot},
            changed_keys=delta.changed_keys,
            fetch_texts=self._fetch_query_texts,
            classify=classify_query_text,
        )

        merged = {}
        for row in delta.derivative_rows:
            obfuscated = resolved.results.get(statement_key(row))
            if obfuscated is None or not obfuscated.query_signature:
                continue
            result = merged.setdefault(
                obfuscated.query_signature,
                {
                    'query_signature': obfuscated.query_signature,
                    'query': obfuscated.obfuscated_query,
                    'count': 0,
                    'time': 0,
                },
            )
            result['count'] += row['num_exec_with_metrics']
            result['time'] += row['coord_stmt_exec_time'] * 1_000_000
        return list(merged.values())

    def run_job(self) -> None:
        try:
            rows = self._collect_rows()
        except Exception:
            self._close_connection()
            raise

        if self._cancel_event.is_set():
            return
        payload = {
            'kind': 'query_metrics',
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ibm_db2_version': self._check.dbms_version,
            'timestamp': time() * 1000,
            'min_collection_interval': self._collection_interval,
            'tags': self._check.tag_manager.get_tags(include_internal=False),
            'cloud_metadata': self._check.cloud_metadata,
            'service': self._check.instance.get('service') or self._check.init_config.get('service') or '',
            'ddagentversion': self._check.agent_version,
            'ddagenthostname': self._check.agent_hostname,
        }
        self._submit_payloads(payload, rows)

    def _submit_payloads(self, wrapper: dict, rows: list[dict]) -> None:
        queue = [rows]
        while queue:
            batch = queue.pop()
            payload = json.encode({**wrapper, 'ibm_db2_rows': batch}, default=default_json_event_encoding)
            if len(payload.encode('utf-8')) <= MAX_PAYLOAD_SIZE:
                # Empty successful collections keep idle instances visible to DBM metering.
                self._check.database_monitoring_query_metrics(payload)
            elif len(batch) > 1:
                midpoint = len(batch) // 2
                queue.extend((batch[midpoint:], batch[:midpoint]))
            else:
                self._log.warning('Query metrics payload exceeds the size limit and will be dropped')
