# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime
from typing import Any

import mock
import pytest

from datadog_checks.base.utils.serialization import json
from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.execution_plans import _assemble_plan

pytestmark = pytest.mark.unit


def _dbm_check(instance: dict[str, Any]) -> IbmDb2Check:
    instance.update(
        {
            'dbm': True,
            'query_metrics': {'enabled': False, 'run_sync': True},
            'query_samples': {'enabled': True, 'run_sync': True, 'explain_schema': 'DATADOG'},
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'
    return check


def test_assemble_plan_tree_from_operators_and_streams() -> None:
    plan = _assemble_plan(
        {'total_cost': 1.2, 'query_degree': 1},
        [
            {'operator_id': 1, 'operator_type': 'RETURN', 'total_cost': 1.2, 'buffers': 0},
            {'operator_id': 2, 'operator_type': 'TBSCAN', 'total_cost': 1.0, 'buffers': 4},
        ],
        [
            {
                'stream_id': 1,
                'source_type': 'D',
                'source_id': -1,
                'target_type': 'O',
                'target_id': 2,
                'object_schema': 'APP',
                'object_name': 'ORDERS',
                'stream_count': 10,
            },
            {
                'stream_id': 2,
                'source_type': 'O',
                'source_id': 2,
                'target_type': 'O',
                'target_id': 1,
                'stream_count': 10,
            },
        ],
        [{'operator_id': 2, 'predicate_id': 1, 'predicate_text': 'ID = 1'}],
    )

    assert plan['Node Type'] == 'RETURN'
    assert plan['Total Cost'] == 1.2
    assert plan['Plans'][0]['Node Type'] == 'TBSCAN'
    assert plan['Plans'][0]['Relation Name'] == 'ORDERS'
    assert plan['Plans'][0]['Schema'] == 'APP'
    assert plan['Plans'][0]['Predicate'] == 'ID = 1'


def test_plan_event_payload(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.tags = ['foo:bar', 'db:datadog']
    check.statement_metrics._tags_no_db = ['foo:bar']
    explain_time = datetime(2026, 6, 15, 12, 0, 0)
    check.connection.query = mock.Mock(
        side_effect=[
            ([], []),
            ([{'explain_started_at': explain_time}], []),
            (
                [
                    {
                        'explain_requester': 'DATADOG',
                        'explain_time': explain_time,
                        'source_name': 'SYSSH200',
                        'source_schema': 'NULLID',
                        'source_version': '',
                        'explain_level': 'S',
                        'stmtno': 1,
                        'sectno': 1,
                        'statement_text': 'VALUES 1',
                        'total_cost': 1.2,
                        'query_degree': 1,
                    }
                ],
                [],
            ),
            (
                [
                    {'operator_id': 1, 'operator_type': 'RETURN', 'total_cost': 1.2, 'buffers': 0},
                    {'operator_id': 2, 'operator_type': 'TBSCAN', 'total_cost': 1.0, 'buffers': 4},
                ],
                [],
            ),
            (
                [
                    {
                        'stream_id': 1,
                        'source_type': 'D',
                        'source_id': -1,
                        'target_type': 'O',
                        'target_id': 2,
                        'object_schema': 'SYSIBM',
                        'object_name': 'GENROW',
                        'stream_count': 1,
                    },
                    {
                        'stream_id': 2,
                        'source_type': 'O',
                        'source_id': 2,
                        'target_type': 'O',
                        'target_id': 1,
                        'stream_count': 1,
                    },
                ],
                [],
            ),
            ([], []),
        ]
    )
    check.connection.callproc = mock.Mock(
        return_value=(object(), b'\xaa', 'M', None, 0, 'DATADOG', 'DATADOG', explain_time, 'SYSSH200', 'NULLID', '')
    )
    check.connection.execute = mock.Mock()
    row = {
        'db': 'datadog',
        'stmt_text': 'VALUES 246813579',
        'query': 'VALUES ?',
        'query_signature': 'query-signature',
        'dd_tables': [],
        'dd_commands': ['SELECT'],
        'dd_comments': [],
        'query_truncated': 'not_truncated',
        'executable_id': 'A' * 64,
        'section_type': 'D',
        'member': 0,
    }

    check.statement_metrics._submit_query_plan_events([row])

    events = aggregator.get_event_platform_events('dbm-samples')
    assert len(events) == 1
    event = events[0]
    assert event['dbm_type'] == 'plan'
    assert event['ddsource'] == 'db2'
    assert event['ddtags'] == 'foo:bar,db:datadog,member:0'
    assert event['db']['plan']['signature']
    assert event['db']['plan']['collection_errors'] is None
    assert json.loads(event['db']['plan']['definition'])['Plan']['Plans'][0]['Node Type'] == 'TBSCAN'
    assert event['db2']['executable_id'] == 'A' * 64
    assert event['db2']['explain_schema'] == 'DATADOG'
    assert event['db2']['explain_level'] == 'S'
    check.connection.callproc.assert_any_call(
        'dbm-query-plans-',
        'SYSPROC.EXPLAIN_FROM_SECTION',
        (bytes.fromhex('A' * 64), 'M', None, 0, 'DATADOG', None, None, None, None, None),
    )
    assert check.connection.query.call_args_list[2].kwargs['params'] == [
        'DATADOG',
        explain_time,
        'SYSSH200',
        'NULLID',
        '',
    ]
    assert check.connection.execute.call_count == 11
    assert (
        "OBJECT_METRICS WHERE EXECUTABLE_ID = x'{}'".format('A' * 64)
        in check.connection.execute.call_args_list[-1].args[1]
    )


def test_raw_plan_event_payload(instance: dict[str, Any], aggregator: Any) -> None:
    instance['collect_raw_query_statement'] = {'enabled': True}
    check = _dbm_check(instance)
    check.statement_metrics.tags = ['foo:bar']
    check.statement_metrics._tags_no_db = ['foo:bar']
    check.statement_metrics._execution_plans._collect_plan = mock.Mock(
        return_value={
            'raw_plan': '{"Plan":{"Node Type":"RETURN"}}',
            'raw_statement': 'VALUES 12345',
            'obfuscated_plan': '{"Plan":{"Node Type":"RETURN"}}',
            'plan_signature': 'plan-signature',
            'raw_plan_signature': 'raw-plan-signature',
            'plan_key': {'explain_level': 'S'},
            'error_code': None,
            'error_message': None,
        }
    )

    check.statement_metrics._submit_query_plan_events(
        [
            {
                'db': 'datadog',
                'query': 'VALUES ?',
                'query_signature': 'query-signature',
                'executable_id': 'A' * 64,
            }
        ]
    )

    events = aggregator.get_event_platform_events('dbm-samples')
    assert [event['dbm_type'] for event in events] == ['plan', 'rqp']
    assert events[0]['db']['plan']['raw_signature'] == 'raw-plan-signature'
    assert events[1]['db']['statement'] == 'VALUES 12345'
    assert events[1]['db']['plan']['definition'] == '{"Plan":{"Node Type":"RETURN"}}'
    assert events[1]['db']['plan']['raw_signature'] == 'raw-plan-signature'


def test_plan_event_for_invalid_executable_id(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.tags = ['foo:bar']
    check.statement_metrics._tags_no_db = ['foo:bar']

    check.statement_metrics._submit_query_plan_events(
        [
            {
                'db': 'datadog',
                'query': 'VALUES ?',
                'query_signature': 'query-signature',
                'executable_id': None,
            }
        ]
    )

    events = aggregator.get_event_platform_events('dbm-samples')
    assert len(events) == 1
    assert events[0]['db']['plan']['definition'] is None
    assert events[0]['db']['plan']['signature'] is None
    assert events[0]['db']['plan']['collection_errors'] == [
        {'code': 'invalid_executable_id', 'message': 'executable_id is missing or invalid'}
    ]


def test_plan_event_uses_recent_statement_fallback_when_run_key_is_missing(
    instance: dict[str, Any], aggregator: Any
) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.tags = ['foo:bar']
    check.statement_metrics._tags_no_db = ['foo:bar']
    explain_time = datetime(2026, 6, 15, 12, 0, 0)
    check.connection.query = mock.Mock(
        side_effect=[
            ([], []),
            ([{'explain_started_at': explain_time}], []),
            (
                [
                    {
                        'explain_requester': 'DATADOG',
                        'explain_time': explain_time,
                        'source_name': 'SYSSH200',
                        'source_schema': 'NULLID',
                        'source_version': '',
                        'explain_level': 'S',
                        'stmtno': 1,
                        'sectno': 1,
                        'statement_text': 'VALUES 1',
                        'total_cost': 1.2,
                        'query_degree': 1,
                    }
                ],
                [],
            ),
            (
                [
                    {'operator_id': 1, 'operator_type': 'RETURN', 'total_cost': 1.2, 'buffers': 0},
                ],
                [],
            ),
            ([], []),
            ([], []),
        ]
    )
    check.connection.callproc = mock.Mock(return_value=())
    check.connection.execute = mock.Mock()

    check.statement_metrics._submit_query_plan_events(
        [
            {
                'db': 'datadog',
                'stmt_text': 'VALUES 1',
                'query': 'VALUES ?',
                'query_truncated': 'not_truncated',
                'query_signature': 'query-signature',
                'executable_id': 'A' * 64,
            }
        ]
    )

    events = aggregator.get_event_platform_events('dbm-samples')
    assert len(events) == 1
    assert events[0]['db']['plan']['definition']
    assert events[0]['db']['plan']['signature']
    assert events[0]['db']['plan']['collection_errors'] is None
    fallback_call = check.connection.query.call_args_list[2]
    fallback_query = fallback_call.args[1]
    assert 'FROM DATADOG.EXPLAIN_INSTANCE I' in fallback_query
    assert 'RTRIM(I.EXPLAIN_REQUESTER) = CURRENT USER' in fallback_query
    assert 'I.EXPLAIN_TIME >= ?' in fallback_query
    assert 'T.STATEMENT_TEXT = ?' in fallback_query
    assert fallback_call.kwargs['params'] == [explain_time, 'VALUES 1']
