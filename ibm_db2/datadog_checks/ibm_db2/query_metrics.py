# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from binascii import hexlify, unhexlify
from datetime import datetime
from itertools import batched
from time import time
from typing import TYPE_CHECKING

import ibm_db

from datadog_checks.base import to_native_string
from datadog_checks.base.utils.db.query_metrics import ObfuscationLookup, QueryStats, TextKind, resolve_obfuscations
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from .connection import Db2Connection, Db2ConnectionError

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .ibm_db2 import IbmDb2Check

COLLECTION_INTERVAL = 10
# Provisional limit; validate against larger workloads. Db2 sizes its package cache in memory, not entry counts.
TEXT_CACHE_SIZE = 10_000
TEXT_FETCH_BATCH_SIZE = 50
NANOSECONDS_PER_MILLISECOND = 1_000_000
NANOSECONDS_PER_MICROSECOND = 1_000
OBFUSCATION_OPTIONS = to_native_string(json.dumps({'obfuscation_mode': 'obfuscate_and_normalize', 'dbms': 'ibm_db2'}))

STATEMENT_COUNTERS_QUERY = """
/* DDIGNORE */
SELECT MEMBER, EXECUTABLE_ID, INSERT_TIMESTAMP,
       NUM_COORD_EXEC_WITH_METRICS AS "count", COORD_STMT_EXEC_TIME AS "time",
       TOTAL_CPU_TIME AS "cpu_time", ROWS_READ, ROWS_RETURNED
FROM TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))
"""

STATEMENT_TEXT_LOOKUP_QUERY = """
SELECT MEMBER, EXECUTABLE_ID, INSERT_TIMESTAMP, STMT_TEXT
FROM TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, CAST(? AS VARCHAR(32) FOR BIT DATA), NULL, CAST(? AS INTEGER)))
WHERE INSERT_TIMESTAMP = ?
"""

StatementKey = tuple[int, str, datetime]


def statement_key(row: dict) -> StatementKey:
    return row['member'], row['executable_id'], row['insert_timestamp']


def classify_statement_text(text: str) -> TextKind:
    return TextKind.EXCLUDED if text.lstrip().startswith('/* DDIGNORE */') else TextKind.STATEMENT


class QueryMetricsCollector(DBMAsyncJob):
    def __init__(self, check: IbmDb2Check, config: InstanceConfig):
        super().__init__(
            check,
            config_host=config.host,
            expected_db_exceptions=(Db2ConnectionError,),
            min_collection_interval=config.min_collection_interval,
            rate_limit=1 / COLLECTION_INTERVAL,
            dbms=check.dbms,
            job_name='query-metrics',
        )
        # Each background job owns its connection.
        self._connection = Db2Connection(check, config)
        self._obfuscation_lookup: ObfuscationLookup[StatementKey] = ObfuscationLookup(
            maxsize=TEXT_CACHE_SIZE, obfuscate_options=OBFUSCATION_OPTIONS
        )
        self._query_stats = QueryStats(
            counter_columns={'count', 'time', 'cpu_time', 'rows_read', 'rows_returned'},
            key=statement_key,
            execution_indicators={'count'},
        )

    def run_job(self) -> None:
        connection = self._connection.ensure_connected()
        cursor = ibm_db.prepare(connection, STATEMENT_COUNTERS_QUERY, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: 10})
        try:
            ibm_db.execute(cursor)
            snapshot = []
            while (row := ibm_db.fetch_assoc(cursor)) is not False:
                row['executable_id'] = hexlify(row['executable_id']).decode('ascii')
                snapshot.append(row)
        finally:
            ibm_db.free_stmt(cursor)

        delta = self._query_stats.diff(snapshot)
        resolved = resolve_obfuscations(
            self._obfuscation_lookup,
            live_keys={statement_key(row) for row in snapshot},
            changed_keys=delta.changed_keys,
            fetch_texts=self._fetch_statement_texts,
            classify=classify_statement_text,
        )
        self._check.log.debug('Query text resolution: %s', resolved.stats)
        rows_by_signature: dict[str, dict] = {}
        for row in delta.derivative_rows:
            obfuscated = resolved.results.get(statement_key(row))
            if obfuscated is None:
                continue
            output = rows_by_signature.setdefault(
                obfuscated.query_signature,
                {
                    'query': obfuscated.obfuscated_query,
                    'query_signature': obfuscated.query_signature,
                    'count': 0,
                    'time': 0,
                    'cpu_time': 0,
                    'rows_read': 0,
                    'rows_returned': 0,
                },
            )
            output['count'] += row['count']
            # Db2 coordinator time is milliseconds; the DBM payload uses nanoseconds.
            output['time'] += row['time'] * NANOSECONDS_PER_MILLISECOND
            output['cpu_time'] += row['cpu_time'] * NANOSECONDS_PER_MICROSECOND
            output['rows_read'] += row['rows_read']
            output['rows_returned'] += row['rows_returned']

        if rows_by_signature:
            payload = {
                'host': self._check.reported_hostname,
                'database_instance': self._check.database_identifier,
                'timestamp': time() * 1000,
                'min_collection_interval': COLLECTION_INTERVAL,
                'tags': self._check.tag_manager.get_tags(include_internal=False),
                'ddagentversion': self._check.agent_version,
                'ibm_db2_version': self._check.dbms_version,
                'ibm_db2_rows': list(rows_by_signature.values()),
            }
            self._check.database_monitoring_query_metrics(json.dumps(payload, default=default_json_event_encoding))

    def _fetch_statement_texts(self, keys: set[StatementKey]) -> dict[StatementKey, str]:
        texts = {}
        for batch in batched(sorted(keys), TEXT_FETCH_BATCH_SIZE, strict=False):
            # Combine one fixed SQL fragment per key into a single request. Only the number of
            # fragments varies; all key values are bound separately, never interpolated into SQL.
            query = '/* DDIGNORE */\n' + '\nUNION ALL\n'.join(STATEMENT_TEXT_LOOKUP_QUERY for _ in batch)
            # Flatten in fragment order, matching each fragment's three placeholders:
            # binary executable ID, member, then insertion timestamp.
            params = tuple(
                value
                for member, executable_id, inserted in batch
                for value in (unhexlify(executable_id), member, inserted)
            )
            cursor = ibm_db.prepare(self._connection.conn, query, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: 10})
            try:
                ibm_db.execute(cursor, params)
                while (row := ibm_db.fetch_assoc(cursor)) is not False:
                    row['executable_id'] = hexlify(row['executable_id']).decode('ascii')
                    texts[statement_key(row)] = row['stmt_text']
            finally:
                ibm_db.free_stmt(cursor)
        return texts

    def shutdown(self) -> None:
        self._connection.close()
