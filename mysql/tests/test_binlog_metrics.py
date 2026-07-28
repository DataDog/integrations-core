# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.mysql import MySql

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
