# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Integration tests for the ClickhousePartsAndMerges collector.

Exercises the full SQL-to-DogStatsD path against a real ClickHouse container:
  1. Create a MergeTree table
  2. Force multiple parts via separate INSERTs (each creates a new part)
  3. Run the check and verify per-table gauges are emitted with correct tags
  4. DETACH a part and verify detached_parts gauges classify it as manual
"""

from concurrent.futures.thread import ThreadPoolExecutor

import clickhouse_connect
import pytest

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.clickhouse import ClickhouseCheck

from .common import CLICKHOUSE_VERSION

UNSUPPORTED_VERSIONS = {'18', '19', '20', '21.8', '22.7'}


def _is_supported():
    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in UNSUPPORTED_VERSIONS


pytestmark = [
    pytest.mark.integration,
    pytest.mark.usefixtures('dd_environment'),
    pytest.mark.skipif(
        not _is_supported(),
        reason="parts_and_merges requires DBM support (ClickHouse 21.8+)",
    ),
]


@pytest.fixture
def parts_and_merges_instance(instance):
    instance['dbm'] = True
    instance['parts_and_merges'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': 60,
    }
    # Disable other DBM sub-collectors to keep the test focused.
    instance['query_metrics'] = {'enabled': False}
    instance['query_samples'] = {'enabled': False}
    instance['query_completions'] = {'enabled': False}
    instance['query_errors'] = {'enabled': False}
    return instance


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def _client(instance_config):
    return clickhouse_connect.get_client(
        host=instance_config['server'],
        port=instance_config['port'],
        username=instance_config['username'],
        password=instance_config['password'],
    )


def _find_metric(aggregator, name, required_tags, value=None):
    """Return the first submitted metric whose tag set is a superset of required_tags."""
    required = set(required_tags)
    matches = [
        m for m in aggregator.metrics(name) if required.issubset(set(m.tags)) and (value is None or m.value == value)
    ]
    assert matches, (
        f"No '{name}' submission had tags superset of {sorted(required)} "
        f"(value={value}). Submissions: "
        f"{[(m.value, sorted(m.tags)) for m in aggregator.metrics(name)]}"
    )
    return matches[0]


def test_parts_and_merges_emits_per_table_gauges(aggregator, parts_and_merges_instance, dd_run_check):
    """Create a table, force multiple parts, run the check, verify per-table gauges arrive."""
    client = _client(parts_and_merges_instance)
    table = 'dd_pm_parts_gauge_test'
    try:
        client.command(f'DROP TABLE IF EXISTS default.{table}')
        client.command(f'CREATE TABLE default.{table} (id UInt64, ts DateTime) ENGINE = MergeTree ORDER BY id')
        # Two separate INSERTs produce two distinct parts (no merge scheduled yet).
        client.command(f'INSERT INTO default.{table} SELECT number, now() FROM numbers(1000)')
        client.command(f'INSERT INTO default.{table} SELECT number, now() FROM numbers(1000, 1000)')

        check = ClickhouseCheck('clickhouse', {}, [parts_and_merges_instance])
        dd_run_check(check)

        required_tags = ['database:default', f'table:{table}']
        _find_metric(aggregator, 'clickhouse.table.parts.active', required_tags, value=2)
        _find_metric(aggregator, 'clickhouse.table.parts.rows', required_tags, value=2000)
        for metric in (
            'clickhouse.table.parts.bytes_on_disk',
            'clickhouse.table.parts.compressed_bytes',
            'clickhouse.table.parts.max_merge_level',
            'clickhouse.table.parts.oldest_part_age_seconds',
        ):
            _find_metric(aggregator, metric, required_tags)
    finally:
        client.command(f'DROP TABLE IF EXISTS default.{table} SYNC')


def test_parts_and_merges_detects_manual_detached_part(aggregator, parts_and_merges_instance, dd_run_check):
    """DETACH PART produces a detached_parts gauge in the 'manual' category (reason IS NULL)."""
    client = _client(parts_and_merges_instance)
    table = 'dd_pm_detached_test'
    try:
        client.command(f'DROP TABLE IF EXISTS default.{table}')
        client.command(f'CREATE TABLE default.{table} (id UInt64, ts DateTime) ENGINE = MergeTree ORDER BY id')
        client.command(f'INSERT INTO default.{table} SELECT number, now() FROM numbers(1000)')
        client.command(f'INSERT INTO default.{table} SELECT number, now() FROM numbers(1000, 1000)')

        # Grab the name of the first active part so we can detach it.
        part_name = client.query(
            f"SELECT name FROM system.parts WHERE database='default' AND table='{table}' AND active=1 LIMIT 1"
        ).result_rows[0][0]
        client.command(f"ALTER TABLE default.{table} DETACH PART '{part_name}'")

        check = ClickhouseCheck('clickhouse', {}, [parts_and_merges_instance])
        dd_run_check(check)

        table_tags = ['database:default', f'table:{table}']
        # The manual-detach path (reason IS NULL in system.detached_parts) must classify as 'manual'.
        _find_metric(aggregator, 'clickhouse.table.detached_parts.count', table_tags, value=1)
        _find_metric(aggregator, 'clickhouse.table.detached_parts.manual', table_tags, value=1)
        _find_metric(aggregator, 'clickhouse.table.detached_parts.corrupted', table_tags, value=0)
    finally:
        client.command(f'DROP TABLE IF EXISTS default.{table} SYNC')
