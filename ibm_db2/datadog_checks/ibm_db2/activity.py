# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from binascii import hexlify
from datetime import datetime, timedelta
from typing import Any

import ibm_db

from datadog_checks.base.utils.db.query_metrics import obfuscate_statement

from .utils import OBFUSCATION_OPTIONS

IDENTITY_COLUMNS = ('member', 'application_handle', 'appl_id', 'uow_id', 'activity_id')
CONTEXT_COLUMNS = (
    'activity_state',
    'session_auth_id',
    'application_name',
    'client_applname',
    'client_hostname',
    'client_wrkstnname',
)
CONTEXT_MAX_CHARS = 512
ACTIVITY_MAX_ROWS = 1_000
ACTIVITY_MAX_TEXT_BYTES = 16_384
ACTIVITY_QUERY_TIMEOUT = 5

ACTIVITY_QUERY = f"""/* DDIGNORE */
SELECT A.MEMBER, A.APPLICATION_HANDLE, A.APPL_ID, A.UOW_ID, A.ACTIVITY_ID,
       A.EXECUTABLE_ID, A.PLANID,
       A.LOCAL_START_TIME, CURRENT TIMESTAMP AS OBSERVED_TIMESTAMP, A.ACTIVITY_STATE,
       OCTET_LENGTH(A.STMT_TEXT) AS STMT_TEXT_BYTES,
       CAST(SUBSTRING(A.STMT_TEXT, 1, LEAST(OCTET_LENGTH(A.STMT_TEXT), {ACTIVITY_MAX_TEXT_BYTES}), OCTETS)
            AS VARCHAR({ACTIVITY_MAX_TEXT_BYTES} OCTETS)) AS STMT_TEXT,
       C.SESSION_AUTH_ID, C.APPLICATION_NAME, C.CLIENT_APPLNAME, C.CLIENT_HOSTNAME,
       C.CLIENT_WRKSTNNAME, C.CONNECTION_START_TIME
FROM TABLE(SYSPROC.MON_GET_ACTIVITY(NULL, -1)) AS A
LEFT JOIN TABLE(SYSPROC.MON_GET_CONNECTION(NULL, -1, 0)) AS C
  ON A.MEMBER = C.MEMBER AND A.APPLICATION_HANDLE = C.APPLICATION_HANDLE
WHERE A.APPLICATION_HANDLE <> SYSPROC.MON_GET_APPLICATION_HANDLE()
ORDER BY A.LOCAL_START_TIME, A.MEMBER, A.APPLICATION_HANDLE, A.UOW_ID, A.ACTIVITY_ID
FETCH FIRST {ACTIVITY_MAX_ROWS + 1} ROWS ONLY
"""


def read_activity(connection: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Read local activities oldest first, bounding SQL transfer and releasing the statement on every exit.

    The extra database row detects the row cap. Limits bound returned data, not the monitoring
    function's internal scan; the statement timeout bounds each execution separately.
    """
    cursor = ibm_db.prepare(connection, ACTIVITY_QUERY, {ibm_db.SQL_ATTR_QUERY_TIMEOUT: ACTIVITY_QUERY_TIMEOUT})
    rows = []
    stats = {'row_limit': 0}
    try:
        ibm_db.execute(cursor)
        for index in range(ACTIVITY_MAX_ROWS + 1):
            row = ibm_db.fetch_assoc(cursor)
            if row is False:
                break
            if index == ACTIVITY_MAX_ROWS:
                stats['row_limit'] = 1
                break
            if row['stmt_text']:
                text = row['stmt_text'].encode('utf-8')
                if len(text) > ACTIVITY_MAX_TEXT_BYTES:
                    # Preserve evidence of truncation in either the database code page or UTF-8.
                    row['stmt_text_bytes'] = max(row['stmt_text_bytes'], len(text))
                    row['stmt_text'] = text[:ACTIVITY_MAX_TEXT_BYTES].decode('utf-8', errors='ignore')
            rows.append(row)
    finally:
        ibm_db.free_stmt(cursor)
    return rows, stats


def normalize_activity(row: dict[str, Any], database: str) -> dict[str, Any] | None:
    """Build an allowlisted observation; both timestamps must come from the database's local clock.

    Connection context is optional and never contributes to execution identity: the monitoring
    join may lose that context while an activity remains visible. SQL is obfuscated and its
    extracted metadata is preserved. Unavailable SQL, timestamps, or identity omit the sample.
    """
    raw_text = row.get('stmt_text')
    start, observed = row.get('local_start_time'), row.get('observed_timestamp')
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None
    if not isinstance(start, datetime) or not isinstance(observed, datetime):
        return None
    if any(row.get(column) is None for column in IDENTITY_COLUMNS):
        return None
    elapsed = observed - start
    if elapsed < timedelta(0):
        return None
    statement = obfuscate_statement(raw_text, OBFUSCATION_OPTIONS)
    if statement is None or not statement.obfuscated_query:
        return None

    result = {
        'statement': statement.obfuscated_query,
        'query_signature': statement.query_signature,
        'dd_tables': statement.tables,
        'dd_commands': statement.commands,
        'dd_comments': statement.comments,
        'query_truncated': 'truncated'
        if (row.get('stmt_text_bytes') or 0) > ACTIVITY_MAX_TEXT_BYTES
        else 'not_truncated',
        'database_name': database,
        'elapsed_ns': elapsed // timedelta(microseconds=1) * 1_000,
        'local_start_time': start.isoformat(),
        **{column: row[column] for column in IDENTITY_COLUMNS},
    }
    if row.get('executable_id') is not None:
        result['executable_id'] = hexlify(row['executable_id']).decode('ascii')
    if row.get('planid') is not None:
        result['planid'] = row['planid']
    for column in CONTEXT_COLUMNS:
        value = row.get(column)
        if isinstance(value, str) and value.strip():
            result[column] = value.strip()[:CONTEXT_MAX_CHARS]
    connection_start = row.get('connection_start_time')
    if isinstance(connection_start, datetime):
        result['connection_start_time'] = connection_start.isoformat()
    return result
