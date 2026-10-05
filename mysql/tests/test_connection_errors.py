# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for the MySQL connection-error classifier."""

import pytest

from datadog_checks.mysql.connection_errors import (
    MYSQL_ERROR_CODE_MAP,
    ConnectionErrorCode,
    classify_error_message,
    format_connection_exception,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Privilege errors observed in staging
        (
            "Privileges error getting replication status (must grant REPLICATION CLIENT): "
            "(1227, 'Access denied; you need (at least one of) the SUPER, SLAVE MONITOR privilege(s) for this operation')",
            ConnectionErrorCode.privilege_replication_client,
        ),
        # Auth
        (
            "(1045, \"Access denied for user 'datadog'@'10.0.0.1' (using password: YES)\")",
            ConnectionErrorCode.auth_failed_password,
        ),
        # DB not found
        (
            "(1049, \"Unknown database 'analytics'\")",
            ConnectionErrorCode.auth_database_not_found,
        ),
        # Connection
        (
            "(2003, \"Can't connect to MySQL server on '10.0.0.1' (Connection refused)\")",
            ConnectionErrorCode.connection_refused,
        ),
        (
            "Lost connection to MySQL server during query (timed out)",
            ConnectionErrorCode.connection_timeout,
        ),
        # max_user_connections
        (
            "User datadog has exceeded the 'max_user_connections' resource",
            ConnectionErrorCode.user_exceeded_max_user_connections,
        ),
        # Fallback
        ('something we have never seen', ConnectionErrorCode.unknown),
        ('', ConnectionErrorCode.unknown),
    ],
)
def test_classify_error_message(raw, expected):
    assert classify_error_message(raw) == expected


class _FakePyMySQLOperationalError(Exception):
    """Mimics pymysql.err.OperationalError where args = (errno, message)."""

    def __init__(self, errno, message):
        super().__init__(errno, message)


@pytest.mark.parametrize(
    "errno,expected",
    [
        (1044, ConnectionErrorCode.auth_database_not_found),
        (1045, ConnectionErrorCode.auth_failed_password),
        (1049, ConnectionErrorCode.auth_database_not_found),
        (1227, ConnectionErrorCode.privilege_replication_client),
        (2003, ConnectionErrorCode.connection_refused),
        (2005, ConnectionErrorCode.host_unreachable),
        (2013, ConnectionErrorCode.connection_timeout),
    ],
)
def test_format_connection_exception_uses_errno(errno, expected):
    exc = _FakePyMySQLOperationalError(errno, 'irrelevant message')
    msg, code = format_connection_exception(exc)
    assert code == expected, f'errno {errno} should map to {expected}'
    assert msg  # always returns a non-empty repr


def test_format_connection_exception_falls_back_to_regex_when_no_errno():
    exc = Exception('must grant REPLICATION CLIENT')
    msg, code = format_connection_exception(exc)
    assert code == ConnectionErrorCode.privilege_replication_client
    assert 'REPLICATION CLIENT' in msg


def test_codes_match_canonical_kebab_case_strings():
    """Catch accidental drift from the web-ui APIDatabaseHostAgentWarningCode union."""
    assert ConnectionErrorCode.connection_refused.value == 'connection-refused'
    assert ConnectionErrorCode.privilege_replication_client.value == 'privilege-replication-client'
    assert ConnectionErrorCode.performance_schema_not_enabled.value == 'performance-schema-not-enabled'
    assert ConnectionErrorCode.unknown.value == 'inferred-connection-error'


def test_mysql_error_code_map_covers_canonical_codes():
    """Every entry in MYSQL_ERROR_CODE_MAP should resolve to a defined enum value."""
    for errno, code in MYSQL_ERROR_CODE_MAP.items():
        assert isinstance(code, ConnectionErrorCode), errno
