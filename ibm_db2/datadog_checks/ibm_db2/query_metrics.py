# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from binascii import hexlify
from datetime import datetime
from time import time
from typing import TYPE_CHECKING

import ibm_db
from requests import ConnectionError

from datadog_checks.base.utils.db.query_metrics import QueryStats, obfuscate_statement
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from .connection import Db2Connection

if TYPE_CHECKING:
    from .config_models import InstanceConfig
    from .ibm_db2 import IbmDb2Check

COLLECTION_INTERVAL = 10
NANOSECONDS_PER_MILLISECOND = 1_000_000
OBFUSCATION_OPTIONS = json.dumps({'obfuscation_mode': 'obfuscate_and_normalize', 'dbms': 'ibm_db2'})

QUERY_METRICS = """
/* DDIGNORE */
SELECT MEMBER, EXECUTABLE_ID, INSERT_TIMESTAMP,
       NUM_COORD_EXEC_WITH_METRICS AS "count", COORD_STMT_EXEC_TIME AS "time", STMT_TEXT
FROM TABLE(SYSPROC.MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1))
"""


def statement_key(row: dict) -> tuple[int, str, datetime]:
    return row['member'], row['executable_id'], row['insert_timestamp']


class QueryMetricsCollector(DBMAsyncJob):
    def __init__(self, check: IbmDb2Check, config: InstanceConfig):
        super().__init__(
            check,
            config_host=config.host,
            expected_db_exceptions=(ConnectionError,),
            min_collection_interval=config.min_collection_interval,
            rate_limit=1 / COLLECTION_INTERVAL,
            dbms=check.dbms,
            job_name='query-metrics',
        )
        # Each background job owns its connection.
        self._connection = Db2Connection(check, config)
        self._query_stats = QueryStats(
            counter_columns={'count', 'time'}, key=statement_key, execution_indicators={'count'}
        )

    def run_job(self) -> None:
        connection = self._connection.ensure_connected()
        cursor = ibm_db.prepare(connection, QUERY_METRICS, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: 10})
        try:
            ibm_db.execute(cursor)
            snapshot = []
            while (row := ibm_db.fetch_assoc(cursor)) is not False:
                row['executable_id'] = hexlify(row['executable_id']).decode('ascii')
                snapshot.append(row)
        finally:
            ibm_db.free_stmt(cursor)

        rows_by_signature: dict[str, dict] = {}
        for row in self._query_stats.diff(snapshot).derivative_rows:
            text = row['stmt_text']
            if not text or text.lstrip().startswith('/* DDIGNORE */'):
                continue
            obfuscated = obfuscate_statement(text, OBFUSCATION_OPTIONS)
            if obfuscated is None:
                continue
            output = rows_by_signature.setdefault(
                obfuscated.query_signature,
                {
                    'query': obfuscated.obfuscated_query,
                    'query_signature': obfuscated.query_signature,
                    'count': 0,
                    'time': 0,
                },
            )
            output['count'] += row['count']
            # Db2 coordinator time is milliseconds; the DBM payload uses nanoseconds.
            output['time'] += row['time'] * NANOSECONDS_PER_MILLISECOND

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

    def shutdown(self) -> None:
        self._connection.close()
