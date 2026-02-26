# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock, patch

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.do_query_actions import DoQueryActionsCheck

from .common import METRICS


def _make_mock_conn(rows=None, description=None):
    """Create a mock DB connection with cursor context manager support."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.description = description or [('count',)]
    mock_cursor.fetchall.return_value = rows if rows is not None else [(42,)]
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def _make_mock_pool(rows=None, description=None):
    """Create a mock ConnectionPool wrapping a mock connection."""
    mock_conn = _make_mock_conn(rows, description)
    mock_pool = MagicMock()
    mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_pool.connection.return_value.__exit__ = MagicMock(return_value=False)
    return mock_pool, mock_conn


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='host\n  Field required',
    ):
        check = DoQueryActionsCheck('do_query_actions', {}, [{}])
        dd_run_check(check)


def test_missing_db_type(dd_run_check):
    with pytest.raises(
        Exception,
        match='db_type\n  Field required',
    ):
        check = DoQueryActionsCheck(
            'do_query_actions',
            {},
            [{'host': 'localhost', 'username': 'test', 'dbname': 'test', 'queries': []}],
        )
        dd_run_check(check)


def test_postgres_single_query_success(dd_run_check, aggregator, postgres_instance):
    mock_pool, _ = _make_mock_pool()

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_metric('do_query_actions.query_success', value=1)
    aggregator.assert_service_check('do_query_actions.query_status', AgentCheck.OK)


def test_postgres_query_failure(dd_run_check, aggregator, postgres_instance):
    mock_pool, mock_conn = _make_mock_pool()

    def execute_side_effect(sql, *args, **kwargs):
        if sql == postgres_instance['queries'][0]['query']:
            raise Exception("syntax error")

    mock_conn.cursor.return_value.execute = MagicMock(side_effect=execute_side_effect)

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    aggregator.assert_metric('do_query_actions.query_success', value=0)
    aggregator.assert_service_check('do_query_actions.query_status', AgentCheck.CRITICAL)


def test_unsupported_db_type(dd_run_check, aggregator, postgres_instance):
    postgres_instance['db_type'] = 'oracle'

    check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
    dd_run_check(check)

    aggregator.assert_metric('do_query_actions.query_success', value=0)
    aggregator.assert_service_check('do_query_actions.query_status', AgentCheck.CRITICAL)


def test_connection_failure_marks_all_queries_critical(dd_run_check, aggregator, multi_query_instance):
    with patch(
        'datadog_checks.do_query_actions.check.ConnectionPool',
        side_effect=Exception('Connection refused'),
    ):
        check = DoQueryActionsCheck('do_query_actions', {}, [multi_query_instance])
        dd_run_check(check)

    assert len(aggregator.service_checks('do_query_actions.query_status')) == 2
    for sc in aggregator.service_checks('do_query_actions.query_status'):
        assert sc.status == AgentCheck.CRITICAL

    success_metrics = aggregator.metrics('do_query_actions.query_success')
    assert len(success_metrics) == 2
    for m in success_metrics:
        assert m.value == 0


def test_multi_query_execution(dd_run_check, aggregator, multi_query_instance):
    mock_pool, _ = _make_mock_pool()

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [multi_query_instance])
        dd_run_check(check)

    success_metrics = aggregator.metrics('do_query_actions.query_success')
    assert len(success_metrics) == 2
    for m in success_metrics:
        assert m.value == 1

    time_metrics = aggregator.metrics('do_query_actions.query_execution_time')
    assert len(time_metrics) == 2

    service_checks = aggregator.service_checks('do_query_actions.query_status')
    assert len(service_checks) == 2


def test_scheduling_interval(dd_run_check, aggregator, postgres_instance):
    """First check runs all queries, immediate second check runs none, time-advanced third runs all."""
    mock_pool, _ = _make_mock_pool()

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])

        dd_run_check(check)
        assert len(aggregator.metrics('do_query_actions.query_success')) == 1

        aggregator.reset()
        dd_run_check(check)
        assert len(aggregator.metrics('do_query_actions.query_success')) == 0

        aggregator.reset()
        check._last_execution = {1: 0.0}
        dd_run_check(check)
        assert len(aggregator.metrics('do_query_actions.query_success')) == 1


def test_per_query_timeout_is_set(dd_run_check, aggregator, postgres_instance):
    mock_pool, mock_conn = _make_mock_pool()
    execute_calls = []
    mock_cursor = mock_conn.cursor.return_value
    original_execute = mock_cursor.execute

    def capture_execute(sql, *args, **kwargs):
        execute_calls.append(sql)
        return original_execute(sql, *args, **kwargs)

    mock_cursor.execute = MagicMock(side_effect=capture_execute)

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    timeout_calls = [c for c in execute_calls if 'statement_timeout' in str(c)]
    assert len(timeout_calls) == 1
    assert 'SET statement_timeout = 10000' in timeout_calls[0]


def test_event_platform_event_payload(dd_run_check, aggregator, postgres_instance):
    mock_pool, _ = _make_mock_pool(rows=[(42,)], description=[('count',)])

    with (
        patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool),
        patch.object(DoQueryActionsCheck, 'event_platform_event') as mock_epe,
    ):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    mock_epe.assert_called_once()
    import json

    raw_event = mock_epe.call_args[0][0]
    event_type = mock_epe.call_args[0][1]
    payload = json.loads(raw_event)

    assert event_type == 'do-query-results'
    assert payload['remote_config_id'] == 'test-config-123'
    assert payload['db_type'] == 'postgres'
    assert payload['db_host'] == 'localhost'
    assert payload['db_name'] == 'test_db'
    assert payload['monitor_id'] == 1
    assert payload['status'] == 'success'
    assert payload['columns'] == ['count']
    assert payload['rows'] == [[42]]
    assert payload['row_count'] == 1
    assert payload['error'] is None
    assert 'duration_s' in payload
    assert 'entity' in payload
    assert payload['entity']['platform'] == 'aws'
    assert payload['entity']['table'] == 'orders'


def test_tags_include_monitor_id(dd_run_check, aggregator, postgres_instance):
    mock_pool, _ = _make_mock_pool()

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    expected_tags = [
        'remote_config_id:test-config-123',
        'db_type:postgres',
        'db_name:test_db',
        'db_host:localhost',
        'port:5432',
        'monitor_id:1',
    ]

    for metric in METRICS:
        aggregator.assert_metric(metric, tags=expected_tags)


def test_shared_connection_pool_reuse(dd_run_check, aggregator, postgres_instance):
    """Pool is created once and reused across multiple check() calls."""
    mock_pool, _ = _make_mock_pool()

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool) as MockPool:
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])

        dd_run_check(check)
        assert MockPool.call_count == 1

        check._last_execution = {}
        aggregator.reset()

        dd_run_check(check)
        assert MockPool.call_count == 1  # pool not recreated


def test_query_failure_does_not_block_subsequent_queries(dd_run_check, aggregator, multi_query_instance):
    """If the first query fails, the second query should still execute."""
    mock_pool, mock_conn = _make_mock_pool()
    mock_cursor = mock_conn.cursor.return_value

    def execute_side_effect(sql, *args, **kwargs):
        if sql == 'SELECT count(*) FROM orders':
            raise Exception("table not found")

    mock_cursor.execute = MagicMock(side_effect=execute_side_effect)

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [multi_query_instance])
        dd_run_check(check)

    success_metrics = aggregator.metrics('do_query_actions.query_success')
    assert len(success_metrics) == 2

    service_checks = aggregator.service_checks('do_query_actions.query_status')
    assert len(service_checks) == 2


def test_cancel_closes_pool(postgres_instance):
    mock_pool = MagicMock()

    check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
    check._pool = mock_pool
    check.cancel()

    mock_pool.close.assert_called_once()
    assert check._pool is None


def test_no_queries_emits_nothing(dd_run_check, aggregator, postgres_instance):
    postgres_instance['queries'] = []

    check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
    dd_run_check(check)

    assert len(aggregator.metrics('do_query_actions.query_success')) == 0
    assert len(aggregator.service_checks('do_query_actions.query_status')) == 0


def test_pool_timeout_marks_queries_critical(dd_run_check, aggregator, postgres_instance):
    """If the pool cannot provide a connection, queries are marked CRITICAL."""
    from psycopg_pool import PoolTimeout

    mock_pool = MagicMock()
    mock_pool.connection.side_effect = PoolTimeout("no connection available")

    with patch('datadog_checks.do_query_actions.check.ConnectionPool', return_value=mock_pool):
        check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
        dd_run_check(check)

    aggregator.assert_metric('do_query_actions.query_success', value=0)
    aggregator.assert_service_check('do_query_actions.query_status', AgentCheck.CRITICAL)


def test_postgres_ssl_params_forwarded(postgres_instance):
    """SSL parameters from instance config are passed to ConnectionPool kwargs."""
    postgres_instance['ssl'] = 'verify-full'
    postgres_instance['ssl_cert'] = '/path/to/cert.pem'
    postgres_instance['ssl_root_cert'] = '/path/to/ca.pem'
    postgres_instance['ssl_key'] = '/path/to/key.pem'

    check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])

    with patch('datadog_checks.do_query_actions.check.ConnectionPool') as MockPool:
        MockPool.return_value = MagicMock()
        check._create_postgres_pool()

    pool_kwargs = MockPool.call_args.kwargs['kwargs']
    assert pool_kwargs['sslmode'] == 'verify-full'
    assert pool_kwargs['sslcert'] == '/path/to/cert.pem'
    assert pool_kwargs['sslrootcert'] == '/path/to/ca.pem'
    assert pool_kwargs['sslkey'] == '/path/to/key.pem'


def test_aws_iam_token_provider(postgres_instance):
    """AWS IAM auth config creates an AWSTokenProvider."""
    postgres_instance['aws'] = {
        'region': 'us-east-1',
        'managed_authentication': {'enabled': True, 'role_arn': 'arn:aws:iam::role/test'},
    }

    check = DoQueryActionsCheck('do_query_actions', {}, [postgres_instance])
    provider = check._build_token_provider()

    from datadog_checks.base.utils.db.postgres_connection import AWSTokenProvider

    assert isinstance(provider, AWSTokenProvider)
    assert provider.host == 'localhost'
    assert provider.region == 'us-east-1'
    assert provider.role_arn == 'arn:aws:iam::role/test'
