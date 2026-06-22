# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Classification of Postgres connection / setup failures into stable
kebab-case error codes that the DBM Setup UI uses to render an
actionable remediation card. Mirrors the pattern in
sqlserver/connection_errors.py.
"""

from __future__ import annotations

import re
from enum import Enum


class ConnectionErrorCode(Enum):
    """Stable kebab-case classification of a Postgres connection / setup failure.

    Values match the APIDatabaseHostAgentWarningCode union in the web-ui
    (packages/apps/databases/lib/api-database-types/api-database-types.ts).
    """

    unknown = "inferred-connection-error"
    connection_refused = "connection-refused"
    connection_timeout = "connection-timeout"
    host_unreachable = "host-unreachable"
    database_starting_up = "database-starting-up"
    database_shutting_down = "database-shutting-down"
    auth_failed_password = "auth-failed-password"
    auth_failed_user_not_found = "auth-failed-user-not-found"
    auth_database_not_found = "auth-database-not-found"
    privilege_pg_monitor = "privilege-pg-monitor"
    privilege_select_on_schema = "privilege-select-on-schema"
    pg_stat_statements_not_loaded = "pg-stat-statements-not-loaded"
    pg_stat_statements_not_created = "pg-stat-statements-not-created"
    ssl_required_by_server = "ssl-required-by-server"
    ssl_cert_verify_failed = "ssl-cert-verify-failed"
    ssl_protocol_mismatch = "ssl-protocol-mismatch"


# Order matters: more-specific patterns first so they win over generic fallbacks.
KNOWN_ERROR_PATTERNS: list[tuple[re.Pattern, ConnectionErrorCode]] = [
    (re.compile(r"the database system is starting up", re.IGNORECASE), ConnectionErrorCode.database_starting_up),
    (re.compile(r"the database system is shutting down", re.IGNORECASE), ConnectionErrorCode.database_shutting_down),
    (re.compile(r"could not translate host name", re.IGNORECASE), ConnectionErrorCode.host_unreachable),
    (re.compile(r"no route to host|network is unreachable", re.IGNORECASE), ConnectionErrorCode.host_unreachable),
    (re.compile(r"name or service not known", re.IGNORECASE), ConnectionErrorCode.host_unreachable),
    (re.compile(r"password authentication failed", re.IGNORECASE), ConnectionErrorCode.auth_failed_password),
    (re.compile(r"no pg_hba\.conf entry", re.IGNORECASE), ConnectionErrorCode.auth_failed_user_not_found),
    (re.compile(r'role ".+" does not exist', re.IGNORECASE), ConnectionErrorCode.auth_failed_user_not_found),
    (re.compile(r'database ".+" does not exist', re.IGNORECASE), ConnectionErrorCode.auth_database_not_found),
    (
        re.compile(r"server does not support SSL|SSL connection.*required", re.IGNORECASE),
        ConnectionErrorCode.ssl_required_by_server,
    ),
    (
        re.compile(r"certificate verify failed|self.signed certificate", re.IGNORECASE),
        ConnectionErrorCode.ssl_cert_verify_failed,
    ),
    (re.compile(r"tlsv1|protocol version", re.IGNORECASE), ConnectionErrorCode.ssl_protocol_mismatch),
    (re.compile(r"connection refused", re.IGNORECASE), ConnectionErrorCode.connection_refused),
    (re.compile(r"timed out|timeout expired", re.IGNORECASE), ConnectionErrorCode.connection_timeout),
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
    """Classify a psycopg OperationalError (or similar) into a (message, code) tuple.

    The code is suitable for plumbing into Health.submit_health_event(error_code=...).
    The message is the original exception's repr — preserved so the UI can show
    "Show raw error" for support context.
    """
    msg = repr(exc)
    return msg, classify_error_message(msg)
