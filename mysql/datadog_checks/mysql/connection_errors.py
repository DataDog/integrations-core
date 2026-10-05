# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Classification of MySQL connection / setup failures into stable
kebab-case error codes that the DBM Setup UI uses to render an
actionable remediation card. Mirrors the pattern in
sqlserver/connection_errors.py.
"""

from __future__ import annotations

import re
from enum import Enum


class ConnectionErrorCode(Enum):
    """Stable kebab-case classification of a MySQL connection / setup failure.

    Values match the APIDatabaseHostAgentWarningCode union in the web-ui
    (packages/apps/databases/lib/api-database-types/api-database-types.ts).
    """

    unknown = "inferred-connection-error"
    connection_refused = "connection-refused"
    connection_timeout = "connection-timeout"
    host_unreachable = "host-unreachable"
    auth_failed_password = "auth-failed-password"
    auth_failed_user_not_found = "auth-failed-user-not-found"
    auth_database_not_found = "auth-database-not-found"
    privilege_replication_client = "privilege-replication-client"
    privilege_select_on_schema = "privilege-select-on-schema"
    performance_schema_not_enabled = "performance-schema-not-enabled"
    events_statements_consumers_disabled = "mysql-events-statements-consumers-disabled"
    events_waits_current_not_enabled = "events-waits-current-not-enabled"
    user_exceeded_max_user_connections = "user-exceeded-max_user_connections"


# pymysql OperationalError exposes its mysql error code as exc.args[0]. The
# canonical mapping below is consulted before regex matching on the message.
MYSQL_ERROR_CODE_MAP: dict[int, ConnectionErrorCode] = {
    1044: ConnectionErrorCode.auth_database_not_found,  # Access denied for user to db
    1045: ConnectionErrorCode.auth_failed_password,  # Access denied (using password: YES)
    1049: ConnectionErrorCode.auth_database_not_found,  # Unknown database
    1226: ConnectionErrorCode.user_exceeded_max_user_connections,  # max_user_connections exceeded
    1227: ConnectionErrorCode.privilege_replication_client,  # privilege required (e.g. SUPER, REPLICATION CLIENT)
    2003: ConnectionErrorCode.connection_refused,  # Can't connect to MySQL server
    2005: ConnectionErrorCode.host_unreachable,  # Unknown server host
    2013: ConnectionErrorCode.connection_timeout,  # Lost connection during query
}


# Regex fallback when the mysql error code is missing or ambiguous. Order
# matters — the first match wins.
KNOWN_ERROR_PATTERNS: list[tuple[re.Pattern, ConnectionErrorCode]] = [
    (
        re.compile(r"must grant REPLICATION CLIENT|SLAVE MONITOR", re.IGNORECASE),
        ConnectionErrorCode.privilege_replication_client,
    ),
    (re.compile(r"must grant PROCESS", re.IGNORECASE), ConnectionErrorCode.privilege_select_on_schema),
    (
        re.compile(r"Access denied for user .+ \(using password", re.IGNORECASE),
        ConnectionErrorCode.auth_failed_password,
    ),
    (re.compile(r"Unknown database", re.IGNORECASE), ConnectionErrorCode.auth_database_not_found),
    (
        re.compile(r"has exceeded the 'max_user_connections'", re.IGNORECASE),
        ConnectionErrorCode.user_exceeded_max_user_connections,
    ),
    (re.compile(r"Connection refused", re.IGNORECASE), ConnectionErrorCode.connection_refused),
    (re.compile(r"timed out|timeout expired", re.IGNORECASE), ConnectionErrorCode.connection_timeout),
    (re.compile(r"Unknown server host|Name or service not known", re.IGNORECASE), ConnectionErrorCode.host_unreachable),
    (re.compile(r"performance_schema is disabled", re.IGNORECASE), ConnectionErrorCode.performance_schema_not_enabled),
    (
        re.compile(r"events_statements.*consumers are disabled|events_statements.*not enabled", re.IGNORECASE),
        ConnectionErrorCode.events_statements_consumers_disabled,
    ),
]


def classify_error_message(message: str) -> ConnectionErrorCode:
    """Match the raw error string against KNOWN_ERROR_PATTERNS.

    Returns ConnectionErrorCode.unknown when nothing matches.
    """
    if not message:
        return ConnectionErrorCode.unknown
    for pattern, code in KNOWN_ERROR_PATTERNS:
        if pattern.search(message):
            return code
    return ConnectionErrorCode.unknown


def format_connection_exception(exc: Exception) -> tuple[str, ConnectionErrorCode]:
    """Classify a pymysql OperationalError (or similar) into a (message, code).

    Prefers the structured mysql error code on exc.args[0] when present,
    else falls back to regex matching on the exception's repr.
    """
    msg = repr(exc)
    # pymysql.err.OperationalError raises with (errno, message). Trust that first.
    args = getattr(exc, "args", None)
    if args and isinstance(args, tuple) and len(args) >= 1 and isinstance(args[0], int):
        mapped = MYSQL_ERROR_CODE_MAP.get(args[0])
        if mapped is not None:
            return msg, mapped
    return msg, classify_error_message(msg)
