# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.mysql import BINARY_LOGS_NET_WRITE_TIMEOUT

from . import common


def _build_check(binlog_size_metrics):
    options = {'replication': False}
    if binlog_size_metrics is not None:
        options['binlog_size_metrics'] = binlog_size_metrics
    instance = {
        'host': 'localhost',
        'user': 'datadog',
        'options': options,
    }
    check = MySql(common.CHECK_NAME, {}, [instance])
    check.global_variables._variables = {'log_bin': 'ON'}
    return check


def _collect(check):
    with (
        mock.patch.object(check, '_get_stats_from_status', return_value={}),
        mock.patch.object(check, '_check_innodb_engine_enabled', return_value=False),
        mock.patch.object(check, '_submit_metrics'),
        mock.patch.object(check, '_compute_synthetic_results'),
        mock.patch.object(check, 'version') as version,
        mock.patch.object(check, '_get_binary_log_stats', return_value=123) as binary_log_stats,
    ):
        version.version_compatible.return_value = False
        check._collect_metrics(mock.MagicMock(), tags=[])
    return binary_log_stats


@pytest.mark.unit
@pytest.mark.parametrize('binlog_size_metrics', [None, True])
def test_binlog_size_metrics_collected_by_default(binlog_size_metrics):
    """Binary log size metrics are collected when binlog is enabled and the option is not set or true."""
    check = _build_check(binlog_size_metrics)
    binary_log_stats = _collect(check)
    binary_log_stats.assert_called_once()


@pytest.mark.unit
def test_binlog_size_metrics_disabled_by_option():
    """Setting binlog_size_metrics to false skips the SHOW BINARY LOGS query."""
    check = _build_check(binlog_size_metrics=False)
    binary_log_stats = _collect(check)
    binary_log_stats.assert_not_called()


class FakeCursor:
    def __init__(self, show_binary_logs_error=None):
        self.executed = []
        self._show_binary_logs_error = show_binary_logs_error
        self._rows = []

    def execute(self, query, args=None):
        self.executed.append(query)
        if query.startswith('SHOW BINARY LOGS'):
            if self._show_binary_logs_error:
                raise self._show_binary_logs_error
            self._rows = [('mysql-bin.000001', 100), ('mysql-bin.000002', 23)]

    def fetchall(self):
        return self._rows

    def close(self):
        pass


CONNECTION_ARGS = {'host': 'db.example', 'port': 3306, 'ssl': {'check_hostname': False}}


def _binary_log_stats(check, cursor):
    """Run `_get_binary_log_stats` against a fake dedicated connection, and return the connect mock and result."""
    binlog_connection = mock.MagicMock()
    binlog_connection.cursor.return_value = cursor
    with (
        mock.patch.object(check, '_get_connection_args', return_value=CONNECTION_ARGS),
        mock.patch(
            'datadog_checks.mysql.mysql.connect_with_session_variables', return_value=binlog_connection
        ) as connect,
    ):
        result = check._get_binary_log_stats()
    binlog_connection.close.assert_called_once()
    return connect, result


@pytest.mark.unit
def test_binary_logs_query_runs_with_short_net_write_timeout():
    """SHOW BINARY LOGS holds the binlog index lock while it sends rows, so a slow reader blocks every commit.

    The query must run with a short `net_write_timeout`, on a connection that uses the instance's connection settings.
    """
    check = _build_check(binlog_size_metrics=True)
    cursor = FakeCursor()

    connect, result = _binary_log_stats(check, cursor)

    assert result == 123
    assert cursor.executed == [
        'SET SESSION net_write_timeout = {}'.format(BINARY_LOGS_NET_WRITE_TIMEOUT),
        'SHOW BINARY LOGS;',
    ]
    connect.assert_called_once_with(mysql_version=check.version, **CONNECTION_ARGS)


@pytest.mark.unit
@pytest.mark.parametrize(
    'error, expected_warning',
    [
        pytest.param(
            pymysql.err.OperationalError(2013, 'Lost connection to MySQL server during query'),
            'possibly after net_write_timeout',
            id='timeout',
        ),
        pytest.param(
            pymysql.err.OperationalError(1227, 'Access denied'),
            'must grant REPLICATION CLIENT',
            id='privileges',
        ),
    ],
)
def test_binary_logs_query_error_skips_metric_with_warning(error, expected_warning):
    check = _build_check(binlog_size_metrics=True)

    _, result = _binary_log_stats(check, FakeCursor(show_binary_logs_error=error))

    assert result is None
    assert any(expected_warning in warning for warning in check.warnings)


@pytest.mark.unit
def test_binary_logs_timeout_does_not_affect_main_connection():
    """A write timeout drops the connection that ran SHOW BINARY LOGS.

    That connection must not be the main check connection, or every later query in the run fails and the run's
    status metrics are lost.
    """
    check = _build_check(binlog_size_metrics=True)
    main_cursor = FakeCursor()
    main_db = mock.MagicMock()
    main_db.cursor.return_value = main_cursor
    binlog_connection = mock.MagicMock()
    binlog_connection.cursor.return_value = FakeCursor(
        show_binary_logs_error=pymysql.err.OperationalError(2013, 'Lost connection to MySQL server during query')
    )

    with (
        mock.patch.object(check, '_get_stats_from_status', return_value={}),
        mock.patch.object(check, '_check_innodb_engine_enabled', return_value=False),
        mock.patch.object(check, '_submit_metrics') as submit_metrics,
        mock.patch.object(check, '_compute_synthetic_results'),
        mock.patch.object(check, 'version') as version,
        mock.patch.object(check, '_get_connection_args', return_value=CONNECTION_ARGS),
        mock.patch('datadog_checks.mysql.mysql.connect_with_session_variables', return_value=binlog_connection),
    ):
        version.version_compatible.return_value = False
        check._collect_metrics(main_db, tags=[])

    assert not any('BINARY LOGS' in query for query in main_cursor.executed)
    main_db.close.assert_not_called()
    submit_metrics.assert_called_once()
    assert submit_metrics.call_args.args[1]['Binlog_space_usage_bytes'] is None
