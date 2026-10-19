# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from binascii import hexlify, unhexlify
from copy import deepcopy
from datetime import datetime
from itertools import batched
from time import time
from typing import TYPE_CHECKING

import ibm_db
from cachetools import TTLCache

from datadog_checks.base import to_native_string
from datadog_checks.base.utils.db.query_metrics import (
    ObfuscationLookup,
    ObfuscationResult,
    QueryStats,
    TextKind,
    resolve_obfuscations,
)
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from .connection import Db2Connection, Db2ConnectionError

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .ibm_db2 import IbmDb2Check

COLLECTION_INTERVAL = 10
# Provisional limit; validate against larger workloads. Db2 sizes its package cache in memory, not entry counts.
TEXT_CACHE_SIZE = 10_000
TEXT_FETCH_BATCH_SIZE = 500
FULL_QUERY_TEXT_CACHE_SIZE = 10_000
FULL_QUERY_TEXT_REFRESH_INTERVAL = 3600
NANOSECONDS_PER_MILLISECOND = 1_000_000
NANOSECONDS_PER_MICROSECOND = 1_000
OBFUSCATION_OPTIONS = to_native_string(
    json.dumps(
        {
            'obfuscation_mode': 'obfuscate_and_normalize',
            'dbms': 'ibm_db2',
            'return_json_metadata': True,
            'table_names': True,
            'collect_commands': True,
        }
    )
)

STATEMENT_COUNTERS_QUERY = """
/* DDIGNORE */
SELECT MEMBER, EXECUTABLE_ID, INSERT_TIMESTAMP,
       NUM_COORD_EXEC_WITH_METRICS AS "count", COORD_STMT_EXEC_TIME AS "time",
       TOTAL_CPU_TIME AS "cpu_time", ROWS_READ, ROWS_RETURNED
FROM TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))
"""

STATEMENT_TEXT_LOOKUP_QUERY = """
/* DDIGNORE */
WITH REQUESTED(EXECUTABLE_ID, MEMBER, INSERT_TIMESTAMP) AS (VALUES {key_rows})
SELECT S.MEMBER, S.EXECUTABLE_ID, S.INSERT_TIMESTAMP, S.STMT_TEXT
FROM REQUESTED AS R,
     TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, R.EXECUTABLE_ID, NULL, R.MEMBER)) AS S
WHERE S.INSERT_TIMESTAMP = R.INSERT_TIMESTAMP
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
        self._config = config
        self._connection = Db2Connection(check, config)
        self._full_query_text_cache = TTLCache(maxsize=FULL_QUERY_TEXT_CACHE_SIZE, ttl=FULL_QUERY_TEXT_REFRESH_INTERVAL)
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

        # Text lookup can fail after counters are read. Commit the baseline only after it succeeds.
        query_stats = deepcopy(self._query_stats)
        delta = query_stats.diff(snapshot)
        resolved = resolve_obfuscations(
            self._obfuscation_lookup,
            live_keys={statement_key(row) for row in snapshot},
            changed_keys=delta.changed_keys,
            fetch_texts=self._fetch_statement_texts,
            classify=classify_statement_text,
        )
        self._check.log.debug('Query text resolution: %s', resolved.stats)
        self._query_stats = query_stats
        rows_by_signature: dict[str, dict] = {}
        for row in delta.derivative_rows:
            obfuscated = resolved.results.get(statement_key(row))
            if obfuscated is None:
                continue
            self._submit_full_query_text(obfuscated)
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

    def _submit_full_query_text(self, statement: ObfuscationResult) -> None:
        """Send obfuscated SQL at most once per cache lifetime for this database and signature."""
        if statement.query_signature in self._full_query_text_cache:
            return
        event = {
            'timestamp': time() * 1000,
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': self._check.agent_version,
            'ddsource': 'ibm_db2',
            'ddtags': ','.join(self._check.tag_manager.get_tags(include_internal=False)),
            'dbm_type': 'fqt',
            'service': self._config.service,
            'db': {
                'instance': self._config.db,
                'query_signature': statement.query_signature,
                'statement': statement.obfuscated_query,
                'metadata': {'tables': statement.tables, 'commands': statement.commands},
            },
        }
        self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
        self._full_query_text_cache[statement.query_signature] = True

    def _fetch_statement_texts(self, keys: set[StatementKey]) -> dict[StatementKey, str]:
        """Fetch each requested cache entry's text only if its insertion lifetime still matches."""
        texts = {}
        key_placeholders = '(CAST(? AS VARCHAR(32) FOR BIT DATA), CAST(? AS INTEGER), CAST(? AS TIMESTAMP))'
        for batch in batched(sorted(keys), TEXT_FETCH_BATCH_SIZE, strict=False):
            # REQUESTED drives a targeted lookup per key, not a scan of every cached statement.
            # Only fixed placeholder rows enter the SQL string; all key values are bound separately.
            query = STATEMENT_TEXT_LOOKUP_QUERY.format(key_rows=', '.join(key_placeholders for _ in batch))
            params = []
            for member, executable_id, inserted in batch:
                # Match REQUESTED's column order, converting our hex ID back to Db2's binary ID.
                params.extend((unhexlify(executable_id), member, inserted))
            cursor = ibm_db.prepare(self._connection.conn, query, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: 10})
            try:
                ibm_db.execute(cursor, tuple(params))
                while (row := ibm_db.fetch_assoc(cursor)) is not False:
                    row['executable_id'] = hexlify(row['executable_id']).decode('ascii')
                    texts[statement_key(row)] = row['stmt_text']
            finally:
                ibm_db.free_stmt(cursor)
        return texts

    def shutdown(self) -> None:
        self._connection.close()
