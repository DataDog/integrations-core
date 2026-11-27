# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from typing import Iterator

import mock
import pymysql
import pytest

from datadog_checks.mysql import MySql
from datadog_checks.mysql.mysql import BINARY_LOGS_NET_WRITE_TIMEOUT

from . import common

SET_TIMEOUT = 'SET SESSION net_write_timeout = {}'.format(BINARY_LOGS_NET_WRITE_TIMEOUT)
SHOW_BINARY_LOGS = 'SHOW BINARY LOGS;'
TAGS = ['foo:bar']


class FakeCursor:
    def __init__(self, executed: list[str], show_binary_logs_error: Exception | None = None):
        self.executed = executed
        self._show_binary_logs_error = show_binary_logs_error
        self._rows: list[tuple[str, int]] = []

    def execute(self, query: str, args: object = None) -> None:
        self.executed.append(query)
        if query == SHOW_BINARY_LOGS:
            if self._show_binary_logs_error:
                raise self._show_binary_logs_error
            self._rows = [('mysql-bin.000001', 100), ('mysql-bin.000002', 23)]

    def fetchall(self) -> list[tuple[str, int]]:
        return self._rows

    def close(self) -> None:
        pass


def _build_check(binlog_size_metrics: bool | None = None, log_bin: str = 'ON') -> MySql:
    options: dict[str, object] = {'replication': False}
    if binlog_size_metrics is not None:
        options['binlog_size_metrics'] = binlog_size_metrics
    instance = {
        'host': 'localhost',
        'user': 'datadog',
        'options': options,
    }
    check = MySql(common.CHECK_NAME, {}, [instance])
    check.global_variables._variables = {'log_bin': log_bin}
    return check


def _fake_db(executed: list[str], show_binary_logs_error: Exception | None = None) -> mock.MagicMock:
    db = mock.MagicMock()
    db.cursor.side_effect = lambda *args: FakeCursor(executed, show_binary_logs_error)
    return db


@pytest.mark.unit
@pytest.mark.parametrize(
    'binlog_size_metrics, log_bin, collected',
    [
        pytest.param(None, 'ON', True, id='default'),
        pytest.param(True, 'ON', True, id='enabled'),
        pytest.param(False, 'ON', False, id='disabled-by-option'),
        pytest.param(None, 'OFF', False, id='log-bin-off'),
    ],
)
def test_binary_log_metrics(aggregator, binlog_size_metrics: bool | None, log_bin: str, collected: bool):
    check = _build_check(binlog_size_metrics, log_bin)
    executed: list[str] = []

    check._collect_binary_log_metrics(_fake_db(executed), TAGS)

    if collected:
        assert executed == [SET_TIMEOUT, SHOW_BINARY_LOGS]
        aggregator.assert_metric(
            'mysql.binlog.disk_use', value=123, tags=TAGS, hostname=check.reported_hostname, count=1
        )
    else:
        assert executed == []
        aggregator.assert_metric('mysql.binlog.disk_use', count=0)


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
def test_binary_log_query_error_skips_metric_with_warning(aggregator, error: Exception, expected_warning: str):
    check = _build_check()

    check._collect_binary_log_metrics(_fake_db([], show_binary_logs_error=error), TAGS)

    aggregator.assert_metric('mysql.binlog.disk_use', count=0)
    assert any(expected_warning in warning for warning in check.warnings)


@pytest.mark.unit
def test_binary_log_query_runs_last_on_main_connection():
    """A net_write_timeout drops the connection, so any query run on it after SHOW BINARY LOGS would fail."""
    check = _build_check()
    executed: list[str] = []
    db = _fake_db(executed)

    @contextmanager
    def connect() -> Iterator[mock.MagicMock]:
        check.service_check_tags = []
        yield db

    with (
        mock.patch.object(check, '_connect', connect),
        mock.patch.object(check.global_variables, 'collect'),
        mock.patch.object(check, 'set_version'),
        mock.patch.object(check, '_send_metadata'),
        mock.patch.object(check, '_check_database_configuration'),
        mock.patch.object(check, 'set_server_uuid'),
        mock.patch.object(check, 'set_cluster_tags'),
        mock.patch.object(check, '_send_database_instance_metadata'),
        mock.patch.object(check, '_collect_metrics', side_effect=lambda *a, **kw: executed.append('metrics')),
        mock.patch.object(check, '_collect_system_metrics'),
        mock.patch.object(check, '_get_runtime_queries', return_value=None),
        mock.patch.object(check, 'run_async_jobs'),
        mock.patch.object(
            check._query_manager, 'execute', side_effect=lambda *a, **kw: executed.append('custom_queries')
        ),
    ):
        check.check(None)

    assert executed == ['metrics', 'custom_queries', SET_TIMEOUT, SHOW_BINARY_LOGS]
