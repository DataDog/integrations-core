# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta
from typing import Any

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


def normalize_activity(row: dict[str, Any], database: str) -> dict[str, Any] | None:
    """Build an allowlisted observation; both timestamps must come from the database's local clock.

    Connection context is optional and never contributes to execution identity: the monitoring
    join may lose that context while an activity remains visible. Raw SQL and comment metadata
    are never copied into the result. Unavailable SQL, timestamps, or identity omit the sample.
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
        'database_name': database,
        'elapsed_ns': (elapsed.days * 86_400 + elapsed.seconds) * 1_000_000_000 + elapsed.microseconds * 1_000,
        'local_start_time': start.isoformat(),
        **{column: row[column] for column in IDENTITY_COLUMNS},
    }
    for column in CONTEXT_COLUMNS:
        value = row.get(column)
        if isinstance(value, str) and value.strip():
            result[column] = value.strip()[:CONTEXT_MAX_CHARS]
    connection_start = row.get('connection_start_time')
    if isinstance(connection_start, datetime):
        result['connection_start_time'] = connection_start.isoformat()
    return result
