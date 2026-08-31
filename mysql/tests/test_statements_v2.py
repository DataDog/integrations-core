# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from concurrent.futures.thread import ThreadPoolExecutor

import mock
import pymysql
import pytest

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.serialization import json
from datadog_checks.mysql import MySql
from datadog_checks.mysql.statements import METRICS_COLUMNS, MySQLStatementMetrics
from datadog_checks.mysql.statements_v2 import (
    DEFAULT_DIGESTS_SIZE,
    DIGEST_SNAPSHOT_QUERY,
    DIGEST_SNAPSHOT_QUERY_TRUNCATED,
    STATEMENT_COUNT_REFRESH_INTERVAL,
    MySQLStatementMetricsV2,
)

from . import common

pytestmark = pytest.mark.unit

CLOSE_TO_ZERO_INTERVAL = 0.0000001
NORMALIZED_QUERY = 'SELECT * FROM `employees` WHERE `id` = ?'
QUERY_SIGNATURE = compute_sql_signature(NORMALIZED_QUERY)


@pytest.fixture
def dbm_instance(instance_complex):
    instance_complex['dbm'] = True
    instance_complex['disable_generic_tags'] = False
    instance_complex['query_samples'] = {'enabled': False}
    instance_complex['query_metrics'] = {
        'enabled': True,
        'run_sync': True,
        'collection_interval': CLOSE_TO_ZERO_INTERVAL,
        'incremental_query_metrics': True,
    }
    instance_complex['query_activity'] = {'enabled': False}
    instance_complex['collect_settings'] = {'enabled': False}
    return instance_complex


@pytest.fixture(autouse=True)
def stop_orphaned_threads():
    DBMAsyncJob.executor.shutdown(wait=True)
    DBMAsyncJob.executor = ThreadPoolExecutor()


def snapshot_row(digest, count_star, schema_name='testdb'):
    row = {
        'schema_name': schema_name,
        'digest': digest,
        'last_seen': '2026-01-01 00:00:00',
    }
    row.update(dict.fromkeys(METRICS_COLUMNS, 0))
    row['count_star'] = count_star
    return row


def prepared_row(instance_id, count_star, sql_text='SELECT * FROM employees WHERE id = ?', schema_name='testdb'):
    row = {
        '_dd_statement_id': instance_id,
        'schema_name': schema_name,
        'digest': None,
        'digest_text': sql_text,
        'last_seen': '2026-01-01 00:00:00',
    }
    row.update(dict.fromkeys(METRICS_COLUMNS, 0))
    row['count_star'] = count_star
    return row


@pytest.fixture
def obfuscator(datadog_agent):
    with mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent:
        mock_agent.side_effect = lambda query, options=None: json.dumps({'query': NORMALIZED_QUERY, 'metadata': {}})
        yield mock_agent


def make_job(dbm_instance):
    check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    job = check.statement_metrics
    job._collect_prepared_statements = False
    return check, job


def test_check_selects_incremental_collector(dbm_instance):
    check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    assert isinstance(check.statement_metrics, MySQLStatementMetricsV2)


def test_check_selects_legacy_collector_by_default(dbm_instance):
    del dbm_instance['query_metrics']['incremental_query_metrics']
    check = MySql(common.CHECK_NAME, {}, [dbm_instance])
    assert type(check.statement_metrics) is MySQLStatementMetrics


def test_only_query_recent_statements_warns(dbm_instance, caplog):
    dbm_instance['query_metrics']['only_query_recent_statements'] = True
    caplog.set_level(logging.WARNING, logger="datadog_checks")
    MySql(common.CHECK_NAME, {}, [dbm_instance])
    assert 'only_query_recent_statements has no effect' in caplog.text


def test_first_cycle_only_establishes_baseline(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', return_value=[snapshot_row('d1', 100)]),
        mock.patch.object(job, '_fetch_digest_texts') as fetch,
    ):
        assert job._collect_per_statement_metrics([]) == []
    fetch.assert_not_called()
    obfuscator.assert_not_called()


def test_only_changed_digest_is_resolved(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter(
        [
            [snapshot_row('d1', 100), snapshot_row('d2', 200)],
            [snapshot_row('d1', 110), snapshot_row('d2', 200)],
        ]
    )
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
    ):
        assert job._collect_per_statement_metrics([]) == []
        rows = job._collect_per_statement_metrics([])

    fetch.assert_called_once_with({'d1'})
    assert obfuscator.call_count == 1
    assert len(rows) == 1
    assert rows[0]['count_star'] == 10
    assert rows[0]['query_signature'] == QUERY_SIGNATURE
    assert rows[0]['digest_text'] == NORMALIZED_QUERY


def test_cached_digest_is_not_fetched_or_obfuscated_again(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter(
        [
            [snapshot_row('d1', 100)],
            [snapshot_row('d1', 110)],
            [snapshot_row('d1', 120)],
        ]
    )
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
    ):
        job._collect_per_statement_metrics([])
        job._collect_per_statement_metrics([])
        rows = job._collect_per_statement_metrics([])

    assert fetch.call_count == 1
    assert obfuscator.call_count == 1
    assert rows[0]['count_star'] == 10


def test_digest_shared_across_schemas_is_resolved_once(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter(
        [
            [snapshot_row('d1', 100, schema_name=schema) for schema in ('a', 'b')],
            [snapshot_row('d1', 110, schema_name=schema) for schema in ('a', 'b')],
        ]
    )
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}) as fetch,
    ):
        job._collect_per_statement_metrics([])
        rows = job._collect_per_statement_metrics([])

    fetch.assert_called_once_with({'d1'})
    assert obfuscator.call_count == 1
    assert {row['schema_name'] for row in rows} == {'a', 'b'}


def test_explain_digest_is_negative_cached(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter(
        [
            [snapshot_row('d1', 100)],
            [snapshot_row('d1', 110)],
            [snapshot_row('d1', 120)],
        ]
    )
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'EXPLAIN SELECT 1'}) as fetch,
    ):
        job._collect_per_statement_metrics([])
        assert job._collect_per_statement_metrics([]) == []
        assert job._collect_per_statement_metrics([]) == []

    assert fetch.call_count == 1
    assert obfuscator.call_count == 0
    assert job._obfuscation_lookup.ignored_map_size == 1


def test_quiet_cycle_prunes_departed_digest(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter(
        [
            [snapshot_row('d1', 100), snapshot_row('d2', 100)],
            [snapshot_row('d1', 110), snapshot_row('d2', 110)],
            [snapshot_row('d1', 110)],
        ]
    )
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1', 'd2': 'SELECT 2'}),
    ):
        job._collect_per_statement_metrics([])
        job._collect_per_statement_metrics([])
        assert job._obfuscation_lookup.key_map_size == 2
        assert job._collect_per_statement_metrics([]) == []

    assert job._obfuscation_lookup.key_map_size == 1


def test_counter_reset_does_not_emit(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter([[snapshot_row('d1', 100)], [snapshot_row('d1', 50)]])
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts') as fetch,
    ):
        job._collect_per_statement_metrics([])
        assert job._collect_per_statement_metrics([]) == []
    fetch.assert_not_called()


def test_prepared_statements_merge_with_digest_rows(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    job._collect_prepared_statements = True
    snapshots = iter([[snapshot_row('d1', 100)], [snapshot_row('d1', 110)]])
    prepared = iter([[prepared_row(1001, 100)], [prepared_row(1001, 105)]])

    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_query_prepared_statements', side_effect=prepared),
        mock.patch.object(job, '_fetch_digest_texts', return_value={'d1': 'SELECT 1'}),
    ):
        assert job._collect_per_statement_metrics([]) == []
        rows = job._collect_per_statement_metrics([])

    assert len(rows) == 1
    assert rows[0]['query_signature'] == QUERY_SIGNATURE
    assert rows[0]['count_star'] == 15
    assert '_dd_statement_id' not in rows[0]
    assert obfuscator.call_count == 3


def test_digest_overflow_row_preserves_legacy_shape(dbm_instance, obfuscator):
    _, job = make_job(dbm_instance)
    snapshots = iter([[snapshot_row(None, 100, None)], [snapshot_row(None, 110, None)]])
    with (
        mock.patch.object(job, '_get_statement_count'),
        mock.patch.object(job, '_query_digest_snapshot', side_effect=snapshots),
        mock.patch.object(job, '_fetch_digest_texts') as fetch,
    ):
        job._collect_per_statement_metrics([])
        rows = job._collect_per_statement_metrics([])

    fetch.assert_not_called()
    obfuscator.assert_not_called()
    assert len(rows) == 1
    assert rows[0]['digest'] is None
    assert rows[0]['digest_text'] is None
    assert rows[0]['query_signature'] is None


@pytest.mark.parametrize(
    "digests_size, expected_maxsize",
    [
        pytest.param('20000', 20000, id='reported-size'),
        pytest.param('-1', DEFAULT_DIGESTS_SIZE, id='autosized'),
        pytest.param(None, DEFAULT_DIGESTS_SIZE, id='absent'),
        pytest.param('invalid', DEFAULT_DIGESTS_SIZE, id='malformed'),
    ],
)
def test_sync_cache_size(dbm_instance, digests_size, expected_maxsize):
    check, job = make_job(dbm_instance)
    check.global_variables._variables = (
        {'performance_schema_digests_size': digests_size} if digests_size is not None else {}
    )
    job._sync_cache_size()
    assert job._obfuscation_lookup.maxsize == expected_maxsize


@pytest.mark.parametrize(
    "digests_size, expected_query",
    [
        pytest.param('5000', DIGEST_SNAPSHOT_QUERY, id='complete-table'),
        pytest.param('20000', DIGEST_SNAPSHOT_QUERY_TRUNCATED, id='truncated-table'),
        pytest.param('-1', DIGEST_SNAPSHOT_QUERY_TRUNCATED, id='autosized-table'),
        pytest.param(None, DIGEST_SNAPSHOT_QUERY_TRUNCATED, id='unknown-table'),
    ],
)
def test_snapshot_query_stabilizes_truncated_results(dbm_instance, digests_size, expected_query):
    check, job = make_job(dbm_instance)
    check.global_variables._variables = (
        {'performance_schema_digests_size': digests_size} if digests_size is not None else {}
    )
    assert job._snapshot_query() == expected_query


def test_statement_count_is_refreshed_at_most_once_per_minute(dbm_instance):
    check, job = make_job(dbm_instance)
    cursor = mock.MagicMock()
    cursor.fetchall.return_value = [{'count': 42}]
    connection = mock.MagicMock()
    connection.cursor.return_value = cursor

    with (
        mock.patch.object(job, '_get_db_connection', return_value=connection),
        mock.patch.object(check, 'gauge') as gauge,
    ):
        job._get_statement_count([])
        job._get_statement_count([])
        job._statement_count_updated_at -= STATEMENT_COUNT_REFRESH_INTERVAL + 1
        job._get_statement_count([])

    assert cursor.execute.call_count == 2
    assert [call.args[1] for call in gauge.call_args_list] == [42, 42, 42]


def test_digest_text_fetch_is_batched_and_preserves_partial_results(dbm_instance):
    _, job = make_job(dbm_instance)
    cursor = mock.MagicMock()
    cursor.execute.side_effect = [None, pymysql.err.OperationalError('gone')]
    cursor.fetchall.return_value = [{'digest': 'd0000', 'digest_text': 'SELECT 1'}]
    connection = mock.MagicMock()
    connection.cursor.return_value = cursor

    with mock.patch.object(job, '_get_db_connection', return_value=connection):
        texts = job._fetch_digest_texts({'d{:04d}'.format(i) for i in range(600)})

    assert texts == {'d0000': 'SELECT 1'}
    assert [len(call.args[1]) for call in cursor.execute.call_args_list] == [500, 100]


def test_queries_abort_after_cancellation(dbm_instance):
    _, job = make_job(dbm_instance)
    job.cancel()
    job._get_db_connection = mock.MagicMock()
    with pytest.raises(Exception, match='cancelled'):
        job._query_digest_snapshot()
    job._get_db_connection.assert_not_called()


def test_shutdown_closes_connection_and_releases_state(dbm_instance):
    _, job = make_job(dbm_instance)
    connection = mock.MagicMock()
    job._db = connection
    job.shutdown()
    connection.close.assert_called_once()
    assert job._db is None
    assert job._check is None
    assert job._query_stats is None
    assert job._prepared_query_stats is None
    assert job._obfuscation_lookup is None


def test_v2_rows_match_v1_rows(dbm_instance, datadog_agent):
    v1_instance = dict(dbm_instance)
    v1_instance['query_metrics'] = dict(dbm_instance['query_metrics'])
    del v1_instance['query_metrics']['incremental_query_metrics']

    v1_check = MySql(common.CHECK_NAME, {}, [v1_instance])
    v2_check = MySql(common.CHECK_NAME, {}, [dbm_instance])

    def v1_row(count_star):
        row = {
            '_dd_statement_id': None,
            'schema_name': 'testdb',
            'digest': 'd1',
            'digest_text': 'SELECT * FROM employees WHERE id = ?',
            'last_seen': '2026-01-01 00:00:00',
        }
        row.update(dict.fromkeys(METRICS_COLUMNS, 0))
        row['count_star'] = count_star
        return row

    with (
        mock.patch.object(datadog_agent, 'obfuscate_sql', passthrough=True) as mock_agent,
        mock.patch.object(v1_check.statement_metrics, '_get_statement_count'),
        mock.patch.object(
            v1_check.statement_metrics,
            '_query_summary_per_statement',
            side_effect=iter([[v1_row(100)], [v1_row(110)]]),
        ),
        mock.patch.object(v2_check.statement_metrics, '_get_statement_count'),
        mock.patch.object(
            v2_check.statement_metrics,
            '_query_digest_snapshot',
            side_effect=iter([[snapshot_row('d1', 100)], [snapshot_row('d1', 110)]]),
        ),
        mock.patch.object(
            v2_check.statement_metrics,
            '_fetch_digest_texts',
            return_value={'d1': 'SELECT * FROM employees WHERE id = ?'},
        ),
    ):
        mock_agent.side_effect = lambda query, options=None: json.dumps({'query': NORMALIZED_QUERY, 'metadata': {}})
        v2_check.statement_metrics._collect_prepared_statements = False

        v1_check.statement_metrics._collect_per_statement_metrics([])
        v1_rows = v1_check.statement_metrics._collect_per_statement_metrics([])
        v2_check.statement_metrics._collect_per_statement_metrics([])
        v2_rows = v2_check.statement_metrics._collect_per_statement_metrics([])

    assert v1_rows == v2_rows
