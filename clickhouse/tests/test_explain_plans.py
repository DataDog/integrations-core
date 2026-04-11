# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.explain_plans import ClickhouseExplainPlans, DBExplainError

pytestmark = pytest.mark.unit

SAMPLE_PLAN = {
    "Plan": {
        "Node Type": "Expression",
        "Description": "",
        "Plans": [{"Node Type": "ReadFromStorage", "Description": "SystemTables"}],
    }
}


@pytest.fixture
def instance_with_dbm():
    return {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {
            'enabled': True,
            'collection_interval': 10,
            'samples_per_hour_per_query': 15,
            'seen_samples_cache_maxsize': 10000,
            'max_samples_per_collection': 1000,
            'explained_queries_per_hour_per_query': 1,
            'explained_queries_cache_maxsize': 5000,
            'run_sync': False,
        },
        'tags': ['test:clickhouse'],
    }


@pytest.fixture
def check_with_dbm(instance_with_dbm):
    return ClickhouseCheck('clickhouse', {}, [instance_with_dbm])


@pytest.fixture
def explain_plans(check_with_dbm):
    """Return the ClickhouseExplainPlans instance from the check's query completions."""
    return check_with_dbm.query_completions._explain_plans


def test_explain_plans_initialized(check_with_dbm):
    """ClickhouseExplainPlans is initialized when query_completions is enabled."""
    assert check_with_dbm.query_completions is not None
    assert check_with_dbm.query_completions._explain_plans is not None
    assert isinstance(check_with_dbm.query_completions._explain_plans, ClickhouseExplainPlans)


@pytest.mark.parametrize(
    "statement,expected",
    [
        ("SELECT * FROM users", True),
        ("select count() FROM system.tables", True),
        ("INSERT INTO events VALUES (?)", True),
        ("WITH cte AS (SELECT 1) SELECT * FROM cte", True),
        ("UPDATE users SET name = ?", False),
        ("DELETE FROM users WHERE id = 1", False),
        ("CREATE TABLE foo (id Int64)", False),
        ("DROP TABLE foo", False),
        ("", False),
    ],
)
def test_can_explain_statement(explain_plans, statement, expected):
    assert explain_plans._can_explain_statement(statement) is expected


def test_run_explain_safe_no_plans_possible(explain_plans):
    """Unsupported statement types return no_plans_possible without running EXPLAIN."""
    row = {
        'query': 'UPDATE users SET name = ?',
        'statement': 'UPDATE users SET name = ?',
        'query_signature': 'abc123',
    }
    plan_dict, error_code, error_msg = explain_plans._run_explain_safe(row)
    assert plan_dict is None
    assert error_code == DBExplainError.no_plans_possible
    assert error_msg is None


def test_run_explain_safe_database_error(explain_plans):
    """Database errors from EXPLAIN are caught and returned as database_error."""
    explain_plans._execute_query_fn = mock.MagicMock(side_effect=Exception("ClickHouse error"))

    row = {
        'query': 'SELECT * FROM users',
        'statement': 'SELECT * FROM users',
        'query_signature': 'abc123',
    }
    plan_dict, error_code, error_msg = explain_plans._run_explain_safe(row)
    assert plan_dict is None
    assert error_code == DBExplainError.database_error
    assert error_msg is not None


def test_run_explain_safe_success(explain_plans):
    """A successful EXPLAIN call returns the parsed plan dict."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    row = {
        'query': 'SELECT * FROM system.tables',
        'statement': 'SELECT * FROM system.tables',
        'query_signature': 'abc123',
    }
    plan_dict, error_code, error_msg = explain_plans._run_explain_safe(row)
    assert plan_dict == SAMPLE_PLAN
    assert error_code is None
    assert error_msg is None


def test_collect_plan_for_statement_no_plans_possible(explain_plans):
    """Statements that cannot be explained return None."""
    row = {
        'query': 'UPDATE users SET x = 1',
        'statement': 'UPDATE users SET x = ?',
        'query_signature': 'abc123',
    }
    result = explain_plans._collect_plan_for_statement(row, ['test:tag'])
    assert result is None


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_plan_event_structure(mock_agent, explain_plans):
    """A successful plan event has the required fields and correct dbm_type."""
    mock_agent.get_version.return_value = '7.64.0'
    mock_agent.obfuscate_sql_exec_plan.return_value = json.dumps(SAMPLE_PLAN)

    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    row = {
        'query': 'SELECT * FROM system.tables',
        'statement': 'SELECT * FROM system.tables',
        'query_signature': 'sig001',
        'databases': 'default',
        'user': 'default_user',
        'query_kind': 'Select',
        'query_duration_ms': 100.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': ['tables'],
        'dd_commands': ['SELECT'],
    }
    event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    assert event['dbm_type'] == 'plan'
    assert event['ddsource'] == 'clickhouse'
    assert event['ddagentversion'] == '7.64.0'
    assert event['host'] is not None
    assert event['database_instance'] is not None
    assert event['timestamp'] == 1746205423150500 / 1000
    assert event['ddtags'] == 'test:tag'

    db = event['db']
    assert db['query_signature'] == 'sig001'
    assert db['statement'] == 'SELECT * FROM system.tables'
    assert db['plan']['definition'] is not None
    assert db['plan']['signature'] is not None
    assert db['metadata']['tables'] == ['tables']
    assert db['metadata']['commands'] == ['SELECT']

    ch = event['clickhouse']
    assert ch['user'] == 'default_user'
    assert ch['query_kind'] == 'Select'
    assert ch['query_duration_ms'] == 100.0


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plans_rate_limiting(mock_agent, explain_plans):
    """The same query_signature is only explained once within the rate-limit TTL."""
    mock_agent.get_version.return_value = '7.64.0'
    mock_agent.obfuscate_sql_exec_plan.return_value = json.dumps(SAMPLE_PLAN)

    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    rows = [
        {
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'same_sig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 50.0,
            'event_time_microseconds': 1746205423150500,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        },
        {
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'same_sig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 60.0,
            'event_time_microseconds': 1746205423200000,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        },
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))

    # Only one plan emitted despite two rows with the same query_signature
    assert len(plans) == 1
    # EXPLAIN was also only called once
    assert explain_plans._execute_query_fn.call_count == 1


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plans_skips_missing_signature(mock_agent, explain_plans):
    """Rows without a query_signature are skipped."""
    mock_agent.get_version.return_value = '7.64.0'

    rows = [
        {
            'query': 'SELECT 1',
            'statement': 'SELECT ?',
            'query_signature': '',  # missing
            'databases': 'default',
        }
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))
    assert len(plans) == 0


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plans_error_event(mock_agent, explain_plans):
    """When EXPLAIN fails, the error is recorded in collection_errors."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(side_effect=Exception("DB error"))

    rows = [
        {
            'query': 'SELECT * FROM users',
            'statement': 'SELECT * FROM users',
            'query_signature': 'errorsig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 10.0,
            'event_time_microseconds': 1746205423150500,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        }
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))

    assert len(plans) == 1
    plan_event = plans[0]
    assert plan_event['dbm_type'] == 'plan'
    assert plan_event['db']['plan']['definition'] is None
    assert plan_event['db']['plan']['signature'] is None
    errors = plan_event['db']['plan']['collection_errors']
    assert errors is not None
    assert len(errors) == 1
    assert errors[0]['code'] == DBExplainError.database_error.value


def test_default_config_values(instance_with_dbm):
    """Default config values for explain plans are applied correctly."""
    instance = {
        'server': 'localhost',
        'port': 9000,
        'username': 'default',
        'password': '',
        'db': 'default',
        'dbm': True,
        'query_completions': {'enabled': True},
        'tags': ['test:clickhouse'],
    }
    check = ClickhouseCheck('clickhouse', {}, [instance])
    cfg = check._config.query_completions

    assert cfg.explained_queries_per_hour_per_query == 1
    assert cfg.explained_queries_cache_maxsize == 5000
