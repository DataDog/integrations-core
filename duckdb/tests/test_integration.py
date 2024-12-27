# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from datadog_checks.duckdb import DuckdbCheck

from . import common


def test_check(dd_run_check, aggregator, instance):
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)

    for metric in common.METRICS_MAP:
        aggregator.assert_metric(metric)


def test_failed_connection(dd_run_check, instance, caplog):
    caplog.set_level(logging.ERROR)
    instance = common.WRONG_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    dd_run_check(check)

    expected_error = "Database file not found"
    assert expected_error in caplog.text


def test_version(dd_run_check, instance, datadog_agent):
    instance = common.DEFAULT_INSTANCE
    check = DuckdbCheck('duckdb', {}, [instance])
    check.check_id = 'test:123'
    raw_version = '1.1.1'
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }
    dd_run_check(check)

    datadog_agent.assert_metadata('test:123', version_metadata)
