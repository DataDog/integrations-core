# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.table_metrics import ClickhouseTableMetrics

pytestmark = pytest.mark.unit


def _table_size_row(database='default', name='events', total_rows=1000, total_bytes=2048):
    return (database, name, total_rows, total_bytes)


@pytest.fixture
def schema_metrics_instance():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'schema_metrics': {'enabled': True, 'collection_interval': 60, 'run_sync': True},
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check(schema_metrics_instance):
    return ClickhouseCheck('clickhouse', {}, [schema_metrics_instance])


def _patch_query(job, table_rows=None):
    table_rows = table_rows or []

    def fake_query(query):
        return table_rows

    return mock.patch.object(job, '_execute_query', side_effect=fake_query)


def test_initialization(check):
    assert isinstance(check.table_metrics, ClickhouseTableMetrics)
    assert check.table_metrics._collection_interval == 60


def test_default_disabled_when_dbm_on():
    check = ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'dbm': True}])
    assert check.table_metrics is None


def test_disabled_when_dbm_off():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': False, 'schema_metrics': {'enabled': True}}],
    )
    assert check.table_metrics is None


def test_disabled_when_explicitly_opted_out():
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [{'server': 'localhost', 'dbm': True, 'schema_metrics': {'enabled': False}}],
    )
    assert check.table_metrics is None


@pytest.mark.parametrize('bad_value', [None, 0, -1])
def test_init_falls_back_when_collection_interval_is_invalid(bad_value):
    check = ClickhouseCheck(
        'clickhouse',
        {},
        [
            {
                'server': 'localhost',
                'dbm': True,
                'schema_metrics': {'enabled': True, 'collection_interval': bad_value},
            }
        ],
    )
    assert check.table_metrics is not None
    assert check.table_metrics._collection_interval == 60


def test_run_job_emits_table_size_gauges(check):
    job = check.table_metrics
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    with _patch_query(job, table_rows=[_table_size_row(name='events', total_rows=1000, total_bytes=2048)]):
        job.run_job()

    by_name = {n: (v, t) for n, v, t in emitted}
    assert by_name['table.rows'][0] == 1000
    assert by_name['table.bytes'][0] == 2048
    tags = by_name['table.rows'][1]
    assert 'db:default' in tags
    assert 'table:events' in tags


def test_run_job_dedupes_duplicate_table_rows(check):
    job = check.table_metrics
    emitted = []
    check.gauge = lambda name, value, tags=None: emitted.append((name, value, tags))

    row = _table_size_row(name='events')
    with _patch_query(job, table_rows=[row, row, row]):
        job.run_job()

    rows_emissions = [m for m in emitted if m[0] == 'table.rows']
    assert len(rows_emissions) == 1


def test_cancel_closes_db_client(check):
    job = check.table_metrics
    fake_client = mock.MagicMock()
    job._db_client = fake_client

    job.cancel()

    assert job._db_client is None
    fake_client.close.assert_called_once()


def test_routes_through_cluster_all_replicas_in_single_endpoint_mode(schema_metrics_instance):
    schema_metrics_instance['single_endpoint_mode'] = True
    check = ClickhouseCheck('clickhouse', {}, [schema_metrics_instance])
    seen_queries = []

    def fake_query(query):
        seen_queries.append(query)
        return []

    check.gauge = lambda *a, **kw: None
    with mock.patch.object(check.table_metrics, '_execute_query', side_effect=fake_query):
        check.table_metrics.run_job()

    joined = '\n'.join(seen_queries)
    assert "clusterAllReplicas('default', system.tables)" in joined
