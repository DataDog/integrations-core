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
        self.executed.append(query if args is None else query % args)
        if query.startswith('SELECT @@SESSION.net_write_timeout'):
            self._rows = [(60,)]
        elif query.startswith('SHOW BINARY LOGS'):
            if self._show_binary_logs_error:
                raise self._show_binary_logs_error
            self._rows = [('mysql-bin.000001', 100), ('mysql-bin.000002', 23)]

    def fetchone(self):
        return self._rows[0]

    def fetchall(self):
        return self._rows

    def close(self):
        pass


def _binary_log_stats(cursor, connection_open=True):
    check = _build_check(binlog_size_metrics=True)
    db = mock.MagicMock()
    db.cursor.return_value = cursor
    db.open = connection_open
    return check._get_binary_log_stats(db)


@pytest.mark.unit
def test_binary_logs_query_runs_with_short_net_write_timeout():
    """SHOW BINARY LOGS holds the binlog index lock while it sends rows, so a slow reader blocks every commit.

    The query must run with a short `net_write_timeout`, and the session value must be restored for later queries.
    """
    cursor = FakeCursor()

    assert _binary_log_stats(cursor) == 123
    assert cursor.executed == [
        'SELECT @@SESSION.net_write_timeout',
        'SET SESSION net_write_timeout = {}'.format(BINARY_LOGS_NET_WRITE_TIMEOUT),
        'SHOW BINARY LOGS;',
        'SET SESSION net_write_timeout = 60',
    ]


@pytest.mark.unit
def test_binary_logs_query_restores_net_write_timeout_after_error():
    cursor = FakeCursor(show_binary_logs_error=pymysql.err.OperationalError(1227, 'Access denied'))

    assert _binary_log_stats(cursor) is None
    assert cursor.executed[-1] == 'SET SESSION net_write_timeout = 60'


@pytest.mark.unit
def test_binary_logs_query_net_write_timeout_drops_connection():
    """When the server hits `net_write_timeout` it closes the connection, so there is no session left to restore."""
    cursor = FakeCursor(show_binary_logs_error=pymysql.err.OperationalError(2013, 'Lost connection'))

    assert _binary_log_stats(cursor, connection_open=False) is None
    assert cursor.executed[-1] == 'SHOW BINARY LOGS;'
