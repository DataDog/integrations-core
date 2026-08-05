# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Unit tests for the Postgres connection-error classifier."""

import pytest

from datadog_checks.postgres.connection_errors import (
    ConnectionErrorCode,
    classify_error_message,
    format_connection_exception,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        # Connection-level
        (
            'connection failed: connection to server at "10.0.0.1", port 5432 failed: '
            'Connection refused Is the server running on that host and accepting TCP/IP connections?',
            ConnectionErrorCode.connection_refused,
        ),
        (
            'connection failed: connection to server at "10.0.0.1", port 5432 failed: '
            'FATAL:  the database system is starting up',
            ConnectionErrorCode.database_starting_up,
        ),
        (
            'connection failed: connection to server at "10.0.0.1", port 5432 failed: '
            'FATAL:  the database system is shutting down',
            ConnectionErrorCode.database_shutting_down,
        ),
        (
            'could not translate host name "no-such-host" to address: nodename nor servname provided',
            ConnectionErrorCode.host_unreachable,
        ),
        (
            'connection failed: timeout expired',
            ConnectionErrorCode.connection_timeout,
        ),
        # Auth
        (
            'connection failed: FATAL:  password authentication failed for user "datadog"',
            ConnectionErrorCode.auth_failed_password,
        ),
        (
            'FATAL:  no pg_hba.conf entry for host "10.0.0.1", user "datadog"',
            ConnectionErrorCode.auth_failed_user_not_found,
        ),
        (
            'FATAL:  role "datadog" does not exist',
            ConnectionErrorCode.auth_failed_user_not_found,
        ),
        (
            'FATAL:  database "production" does not exist',
            ConnectionErrorCode.auth_database_not_found,
        ),
        # SSL
        (
            'server does not support SSL, but SSL was required',
            ConnectionErrorCode.ssl_required_by_server,
        ),
        (
            'SSL error: certificate verify failed',
            ConnectionErrorCode.ssl_cert_verify_failed,
        ),
        # Fallback
        (
            'some random error we have never seen',
            ConnectionErrorCode.unknown,
        ),
        ('', ConnectionErrorCode.unknown),
    ],
)
def test_classify_error_message(raw, expected):
    assert classify_error_message(raw) == expected


def test_format_connection_exception_returns_message_and_code():
    exc = Exception('connection refused')
    msg, code = format_connection_exception(exc)
    assert code == ConnectionErrorCode.connection_refused
    assert 'connection refused' in msg


def test_format_connection_exception_unknown_falls_back_to_unknown():
    exc = Exception('something wholly unrecognized')
    msg, code = format_connection_exception(exc)
    assert code == ConnectionErrorCode.unknown
    assert 'wholly unrecognized' in msg


def test_codes_match_canonical_kebab_case_strings():
    """Catch accidental drift from the web-ui APIDatabaseHostAgentWarningCode union."""
    assert ConnectionErrorCode.connection_refused.value == 'connection-refused'
    assert ConnectionErrorCode.database_starting_up.value == 'database-starting-up'
    assert ConnectionErrorCode.privilege_pg_monitor.value == 'privilege-pg-monitor'
    assert ConnectionErrorCode.unknown.value == 'inferred-connection-error'
