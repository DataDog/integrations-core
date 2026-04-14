# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from unittest import mock

import pytest

from datadog_checks.clickhouse import ClickhouseCheck
from datadog_checks.clickhouse.explain_plans import (
    ClickhouseExplainPlans,
    DBExplainError,
    _normalize_clickhouse_plan,
    _obfuscate_clickhouse_plan,
)

pytestmark = pytest.mark.unit

SAMPLE_PLAN = {
    "Plan": {
        "Node Type": "Expression",
        "Node Id": "Expression_1",
        "Description": "Project names + Projection",
        "Plans": [
            {
                "Node Type": "Expression",
                "Node Id": "Expression_0",
                "Description": "WHERE + Change column names to column identifiers",
                "Plans": [
                    {
                        "Node Type": "ReadFromMergeTree",
                        "Node Id": "ReadFromMergeTree_0",
                        "Description": "default.inventory_items",
                    }
                ],
            }
        ],
    }
}

SAMPLE_PLAN_WITH_INDEXES = {
    "Plan": {
        "Node Type": "Expression",
        "Node Id": "Expression_1",
        "Description": "Project names + Projection",
        "Plans": [
            {
                "Node Type": "ReadFromMergeTree",
                "Node Id": "ReadFromMergeTree_0",
                "Description": "default.orders",
                "Indexes": [
                    {
                        "Type": "PrimaryKey",
                        "Keys": ["order_date"],
                        "Condition": "(order_date in [2024-01-01, +Inf))",
                        "Parts": 3,
                        "Granules": 12,
                    }
                ],
            }
        ],
    }
}

SAMPLE_PLAN_WITH_ACTIONS = {
    "Plan": {
        "Node Type": "Expression",
        "Node Id": "Expression_1",
        "Description": "Project names + Projection",
        "Actions": {
            "Inputs": [{"Name": "order_id", "Type": "UInt64"}, {"Name": "amount", "Type": "Float64"}],
            "Actions": [
                {"Type": "INPUT", "Result Name": "order_id", "Result Type": "UInt64", "Arguments": []},
                {"Type": "INPUT", "Result Name": "amount", "Result Type": "Float64", "Arguments": []},
            ],
            "Outputs": [{"Name": "order_id", "Type": "UInt64"}, {"Name": "amount", "Type": "Float64"}],
        },
        "Plans": [
            {
                "Node Type": "ReadFromMergeTree",
                "Node Id": "ReadFromMergeTree_0",
                "Description": "default.orders",
            }
        ],
    }
}

SAMPLE_PLAN_WITH_STATS = {
    "Plan": {
        "Node Type": "Expression",
        "Node Id": "Expression_1",
        "Description": "Project names + Projection",
        "Estimated Rows": 1000,
        "Estimated Cost": 42.5,
        "Plans": [
            {
                "Node Type": "ReadFromMergeTree",
                "Node Id": "ReadFromMergeTree_0",
                "Description": "default.inventory_items",
                "Estimated Rows": 1000,
                "Estimated Total Rows": 50000,
            }
        ],
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
            'explained_queries_per_hour_per_query': 60,
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
        ("INSERT INTO events VALUES (?)", False),
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


def test_run_explain_safe_success_array_wrapped(explain_plans):
    """Some ClickHouse versions wrap the plan in a top-level JSON array; it is unwrapped."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps([SAMPLE_PLAN]),)])

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
def test_collect_plans_skips_cte_insert(mock_agent, explain_plans):
    """WITH ... INSERT queries pass _can_explain_statement but are skipped via query_kind."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    rows = [
        {
            'query': 'WITH foo AS (SELECT 1) INSERT INTO t SELECT * FROM foo',
            'statement': 'WITH foo AS (SELECT ?) INSERT INTO t SELECT * FROM foo',
            'query_signature': 'cte_insert_sig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Insert',
            'query_duration_ms': 10.0,
            'event_time_microseconds': 1746205423150500,
            'dd_tables': [],
            'dd_commands': ['INSERT'],
        }
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))

    assert len(plans) == 0
    explain_plans._execute_query_fn.assert_not_called()


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


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plans_unsupported_statements_skip_rate_limiter(mock_agent, explain_plans):
    """Unsupported statements are skipped before acquiring a rate limit slot."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    # Fill the cache with DDL queries up to maxsize so any further acquire would fail
    maxsize = explain_plans._explained_statements_ratelimiter.maxsize
    for i in range(maxsize):
        explain_plans._explained_statements_ratelimiter.acquire(('db', f'ddl_sig_{i}'))

    rows = [
        {
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'select_sig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 10.0,
            'event_time_microseconds': 1746205423150500,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        },
        {
            'query': 'DELETE FROM users WHERE id = 1',
            'statement': 'DELETE FROM users WHERE id = ?',
            'query_signature': 'delete_sig',
            'databases': 'default',
            'user': 'default',
            'query_kind': 'Delete',
            'query_duration_ms': 5.0,
            'event_time_microseconds': 1746205423160000,
            'dd_tables': [],
            'dd_commands': ['DELETE'],
        },
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))

    # The DDL row is skipped before touching the rate limiter; SELECT is also blocked since cache is full
    assert len(plans) == 0
    # EXPLAIN was never called for the DDL row
    explain_plans._execute_query_fn.assert_not_called()


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plans_different_databases_explained_separately(mock_agent, explain_plans):
    """Same query_signature in different databases each get an EXPLAIN."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    rows = [
        {
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'same_sig',
            'databases': 'db_a',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 10.0,
            'event_time_microseconds': 1746205423150500,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        },
        {
            'query': 'SELECT * FROM system.tables',
            'statement': 'SELECT * FROM system.tables',
            'query_signature': 'same_sig',
            'databases': 'db_b',
            'user': 'default',
            'query_kind': 'Select',
            'query_duration_ms': 10.0,
            'event_time_microseconds': 1746205423160000,
            'dd_tables': [],
            'dd_commands': ['SELECT'],
        },
    ]

    plans = list(explain_plans._collect_plans(rows, ['test:tag']))

    assert len(plans) == 2
    assert explain_plans._execute_query_fn.call_count == 2


def test_run_explain_uses_indexes_and_actions(explain_plans):
    """EXPLAIN query includes json=1, indexes=1, and actions=1."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    explain_plans._run_explain("SELECT * FROM orders")

    call_args = explain_plans._execute_query_fn.call_args[0][0]
    assert "json = 1" in call_args
    assert "indexes = 1" in call_args
    assert "actions = 1" in call_args


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_plan_definition_preserves_indexes(mock_agent, explain_plans):
    """Plan definition keeps Indexes fields intact."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN_WITH_INDEXES),)])

    row = {
        'query': 'SELECT * FROM orders WHERE order_date > ?',
        'statement': 'SELECT * FROM orders WHERE order_date > ?',
        'query_signature': 'idx_sig',
        'databases': 'default',
        'user': 'default',
        'query_kind': 'Select',
        'query_duration_ms': 5.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': ['orders'],
        'dd_commands': ['SELECT'],
    }
    event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    definition = json.loads(event['db']['plan']['definition'])
    read_node = definition['Plan']['Plans'][0]
    assert 'Indexes' in read_node
    assert read_node['Indexes'][0]['Type'] == 'PrimaryKey'
    assert read_node['Indexes'][0]['Keys'] == ['order_date']


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_plan_definition_preserves_actions(mock_agent, explain_plans):
    """Plan definition keeps Actions fields intact."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN_WITH_ACTIONS),)])

    row = {
        'query': 'SELECT order_id, amount FROM orders',
        'statement': 'SELECT order_id, amount FROM orders',
        'query_signature': 'act_sig',
        'databases': 'default',
        'user': 'default',
        'query_kind': 'Select',
        'query_duration_ms': 5.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': ['orders'],
        'dd_commands': ['SELECT'],
    }
    event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    definition = json.loads(event['db']['plan']['definition'])
    top_plan = definition['Plan']
    assert 'Actions' in top_plan
    assert top_plan['Actions']['Inputs'][0]['Name'] == 'order_id'
    assert top_plan['Actions']['Outputs'][1]['Name'] == 'amount'


def test_normalize_clickhouse_plan_preserves_indexes_and_actions():
    """_normalize_clickhouse_plan does not strip Indexes or Actions — they are structural."""
    normalized_with_indexes = _normalize_clickhouse_plan(SAMPLE_PLAN_WITH_INDEXES)
    read_node = normalized_with_indexes['Plan']['Plans'][0]
    assert 'Indexes' in read_node
    assert read_node['Indexes'][0]['Type'] == 'PrimaryKey'

    normalized_with_actions = _normalize_clickhouse_plan(SAMPLE_PLAN_WITH_ACTIONS)
    assert 'Actions' in normalized_with_actions['Plan']
    assert normalized_with_actions['Plan']['Actions']['Inputs'][0]['Name'] == 'order_id'


def test_normalize_clickhouse_plan_strips_stats():
    """_normalize_clickhouse_plan removes cost/stats keys but keeps structural fields."""
    normalized = _normalize_clickhouse_plan(SAMPLE_PLAN_WITH_STATS)
    plan = normalized['Plan']
    assert 'Estimated Rows' not in plan
    assert 'Estimated Cost' not in plan
    assert plan['Description'] == 'Project names + Projection'
    child = plan['Plans'][0]
    assert 'Estimated Rows' not in child
    assert 'Estimated Total Rows' not in child
    assert child['Description'] == 'default.inventory_items'


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_plan_definition_preserves_descriptions(mock_agent, explain_plans):
    """Plan definition keeps ClickHouse Description fields intact (not replaced with '?')."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    row = {
        'query': 'SELECT * FROM inventory_items WHERE sku = ?',
        'statement': 'SELECT * FROM inventory_items WHERE sku = ?',
        'query_signature': 'desc_sig',
        'databases': 'default',
        'user': 'default',
        'query_kind': 'Select',
        'query_duration_ms': 5.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': ['inventory_items'],
        'dd_commands': ['SELECT'],
    }
    event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    definition = json.loads(event['db']['plan']['definition'])
    top_plan = definition['Plan']
    assert top_plan['Description'] == 'Project names + Projection'
    assert top_plan['Plans'][0]['Description'] == 'WHERE + Change column names to column identifiers'
    assert top_plan['Plans'][0]['Plans'][0]['Description'] == 'default.inventory_items'


def test_obfuscate_clickhouse_plan_redacts_filter_column():
    """Filter Column containing a predicate expression is redacted."""
    plan = {
        'Plan': {
            'Node Type': 'Filter',
            'Node Id': 'Filter_1',
            'Description': 'WHERE',
            'Filter Column': "notLike(query, '%secret%'_String)",
            'Plans': [],
        }
    }
    result = _obfuscate_clickhouse_plan(plan)
    assert result['Plan']['Filter Column'] == '?'
    assert result['Plan']['Description'] == 'WHERE'
    assert result['Plan']['Node Type'] == 'Filter'


def test_obfuscate_clickhouse_plan_redacts_index_condition():
    """Condition in Index nodes containing a predicate expression is redacted."""
    plan = {
        'Plan': {
            'Node Type': 'ReadFromMergeTree',
            'Node Id': 'ReadFromMergeTree_0',
            'Description': 'default.orders',
            'Indexes': [
                {
                    'Type': 'PrimaryKey',
                    'Condition': 'equals(user_id, 12345)',
                    'Initial Parts': 4,
                    'Selected Parts': 1,
                }
            ],
        }
    }
    result = _obfuscate_clickhouse_plan(plan)
    assert result['Plan']['Indexes'][0]['Condition'] == '?'
    assert result['Plan']['Indexes'][0]['Type'] == 'PrimaryKey'
    assert result['Plan']['Indexes'][0]['Initial Parts'] == 4


def test_obfuscate_clickhouse_plan_redacts_join_clauses():
    """Clauses in Join nodes is redacted."""
    plan = {
        'Plan': {
            'Node Type': 'Join',
            'Node Id': 'Join_1',
            'Description': 'JOIN FillRightFirst',
            'Clauses': '[(__table1.sku) = (__table2.sku)]',
        }
    }
    result = _obfuscate_clickhouse_plan(plan)
    assert result['Plan']['Clauses'] == '?'
    assert result['Plan']['Description'] == 'JOIN FillRightFirst'


def test_obfuscate_clickhouse_plan_redacts_column_and_function_result_names():
    """Result Name in COLUMN and FUNCTION action nodes is redacted; INPUT/ALIAS are kept."""
    plan = {
        'Plan': {
            'Node Type': 'Expression',
            'Expression': {
                'Actions': [
                    {'Node Type': 'INPUT', 'Result Name': 'user_id', 'Result Type': 'UInt64'},
                    {'Node Type': 'COLUMN', 'Result Name': "'%secret%'_String", 'Result Type': 'String'},
                    {
                        'Node Type': 'FUNCTION',
                        'Result Name': "notLike(query, '%secret%'_String)",
                        'Result Type': 'UInt8',
                    },
                    {'Node Type': 'ALIAS', 'Result Name': 'filtered_query', 'Result Type': 'UInt8'},
                ]
            },
        }
    }
    result = _obfuscate_clickhouse_plan(plan)
    actions = result['Plan']['Expression']['Actions']
    assert actions[0]['Result Name'] == 'user_id'  # INPUT kept
    assert actions[1]['Result Name'] == '?'  # COLUMN redacted
    assert actions[2]['Result Name'] == '?'  # FUNCTION redacted
    assert actions[3]['Result Name'] == 'filtered_query'  # ALIAS kept


def test_obfuscate_clickhouse_plan_redacts_expression_names_in_outputs():
    """Name in Inputs/Outputs is redacted when it contains a quote (string literal) or paren (expression)."""
    plan = {
        'Plan': {
            'Node Type': 'Expression',
            'Expression': {
                'Inputs': [
                    {'Name': 'user_id', 'Type': 'UInt64'},
                    {'Name': "notLike(query, '%secret%'_String)", 'Type': 'UInt8'},
                    {'Name': 'equals(user_id, 12345)', 'Type': 'UInt8'},
                ],
                'Outputs': [
                    {'Name': 'user_id', 'Type': 'UInt64'},
                    {'Name': "notLike(query, '%secret%'_String)", 'Type': 'UInt8'},
                ],
            },
        }
    }
    result = _obfuscate_clickhouse_plan(plan)
    inputs = result['Plan']['Expression']['Inputs']
    assert inputs[0]['Name'] == 'user_id'  # plain column name, kept
    assert inputs[1]['Name'] == '?'  # string literal in expression, redacted
    assert inputs[2]['Name'] == '?'  # numeric literal in expression (has paren), redacted

    outputs = result['Plan']['Expression']['Outputs']
    assert outputs[0]['Name'] == 'user_id'
    assert outputs[1]['Name'] == '?'


def test_obfuscate_clickhouse_plan_preserves_structural_fields():
    """Structural fields (Node Type, Node Id, Description, numeric values) are untouched."""
    result = _obfuscate_clickhouse_plan(SAMPLE_PLAN_WITH_INDEXES)
    plan = result['Plan']
    assert plan['Node Type'] == 'Expression'
    assert plan['Node Id'] == 'Expression_1'
    assert plan['Description'] == 'Project names + Projection'
    read_node = plan['Plans'][0]
    assert read_node['Description'] == 'default.orders'
    # Condition is redacted, but other index fields are kept
    assert read_node['Indexes'][0]['Type'] == 'PrimaryKey'
    assert read_node['Indexes'][0]['Condition'] == '?'
    assert read_node['Indexes'][0]['Parts'] == 3
    assert read_node['Indexes'][0]['Granules'] == 12


@pytest.mark.parametrize(
    "query,expected",
    [
        ("SELECT * FROM orders FORMAT JSON", "SELECT * FROM orders"),
        ("SELECT 1 FORMAT TabSeparated", "SELECT 1"),
        ("SELECT 1   FORMAT TSV  ", "SELECT 1"),
        ("select * from t format JSONEachRow", "select * from t"),
        ("SELECT * FROM orders", "SELECT * FROM orders"),
        ("SELECT FORMAT FROM t", "SELECT FORMAT FROM t"),
    ],
)
def test_strip_format_clause(explain_plans, query, expected):
    assert explain_plans._strip_format_clause(query) == expected


def test_run_explain_empty_rows(explain_plans):
    """_run_explain raises ValueError when the query returns no rows."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[])
    with pytest.raises(ValueError, match="no rows"):
        explain_plans._run_explain("SELECT 1")


def test_run_explain_empty_json_array(explain_plans):
    """_run_explain raises ValueError when the JSON response is an empty array."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[('[]',)])
    with pytest.raises(ValueError, match="empty JSON array"):
        explain_plans._run_explain("SELECT 1")


def test_run_explain_invalid_json(explain_plans):
    """_run_explain raises an error when the response is not valid JSON."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[('not valid json',)])
    with pytest.raises(Exception):
        explain_plans._run_explain("SELECT 1")


def test_run_explain_safe_captures_empty_rows_as_database_error(explain_plans):
    """Empty rows from EXPLAIN are surfaced as database_error via _run_explain_safe."""
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[])
    row = {'query': 'SELECT 1', 'statement': 'SELECT ?', 'query_signature': 'sig'}
    plan_dict, error_code, error_msg = explain_plans._run_explain_safe(row)
    assert plan_dict is None
    assert error_code == DBExplainError.database_error


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plan_for_statement_serialization_failure(mock_agent, explain_plans):
    """A serialization failure during plan obfuscation is recorded as invalid_result."""
    mock_agent.get_version.return_value = '7.64.0'

    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    row = {
        'query': 'SELECT * FROM system.tables',
        'statement': 'SELECT * FROM system.tables',
        'query_signature': 'serial_sig',
        'databases': 'default',
        'user': 'default',
        'query_kind': 'Select',
        'query_duration_ms': 10.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': [],
        'dd_commands': ['SELECT'],
    }

    with mock.patch('datadog_checks.clickhouse.explain_plans.json') as mock_json:
        mock_json.loads.return_value = SAMPLE_PLAN
        mock_json.dumps.side_effect = Exception("serialization failed")
        event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    errors = event['db']['plan']['collection_errors']
    assert errors is not None
    assert len(errors) == 1
    assert errors[0]['code'] == DBExplainError.invalid_result.value
    assert event['db']['plan']['definition'] is None
    assert event['db']['plan']['signature'] is None


@mock.patch('datadog_checks.clickhouse.explain_plans.datadog_agent')
def test_collect_plan_for_statement_no_collection_errors_on_success(mock_agent, explain_plans):
    """collection_errors is None (not an empty list) when the plan is collected successfully."""
    mock_agent.get_version.return_value = '7.64.0'
    explain_plans._execute_query_fn = mock.MagicMock(return_value=[(json.dumps(SAMPLE_PLAN),)])

    row = {
        'query': 'SELECT * FROM system.tables',
        'statement': 'SELECT * FROM system.tables',
        'query_signature': 'ok_sig',
        'databases': 'default',
        'user': 'default',
        'query_kind': 'Select',
        'query_duration_ms': 10.0,
        'event_time_microseconds': 1746205423150500,
        'dd_tables': [],
        'dd_commands': ['SELECT'],
    }
    event = explain_plans._collect_plan_for_statement(row, ['test:tag'])

    assert event is not None
    assert event['db']['plan']['collection_errors'] is None


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

    assert cfg.explained_queries_per_hour_per_query == 60
    assert cfg.explained_queries_cache_maxsize == 5000
