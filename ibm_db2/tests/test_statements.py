# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import mock
import pytest

from datadog_checks.base.utils.db import utils as db_utils
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.statements import (
    NOT_TRUNCATED,
    PKG_CACHE_INTROSPECTION_QUERY,
    STMT_TEXT_LIMIT,
    TRUNCATED,
    UNKNOWN_TRUNCATED,
    Db2StatementMetrics,
)

pytestmark = pytest.mark.unit


def _dbm_check(instance: dict[str, Any]) -> IbmDb2Check:
    instance.update(
        {
            'dbm': True,
            'query_metrics': {'run_sync': True},
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'
    return check


def _payload_size(
    statement_metrics: Db2StatementMetrics, payload_wrapper: dict[str, Any], rows: list[dict[str, Any]]
) -> int:
    payload = dict(payload_wrapper)
    payload['db2_rows'] = [statement_metrics._to_metrics_payload_row(row) for row in rows]
    return len(json.dumps(payload, default=default_json_event_encoding))


def test_obfuscator_options_default_to_db2(instance: dict[str, Any]) -> None:
    check = _dbm_check(instance)

    obfuscator_options = json.loads(check._config.obfuscator_options)

    assert obfuscator_options['dbms'] == 'db2'
    assert obfuscator_options['return_json_metadata'] is True
    assert obfuscator_options['table_names'] is True


def test_normalize_queries_passes_db2_options_to_agent(instance: dict[str, Any]) -> None:
    check = _dbm_check(instance)
    obfuscated_statement = json.dumps({'query': 'SELECT * FROM T WHERE ID = ?', 'metadata': {}})

    with mock.patch.object(db_utils.datadog_agent, 'obfuscate_sql', return_value=obfuscated_statement) as obfuscate:
        rows = check.statement_metrics._normalize_queries([{'stmt_text': 'SELECT * FROM T WHERE ID = 1'}])

    assert rows[0]['query'] == 'SELECT * FROM T WHERE ID = ?'
    _, options = obfuscate.call_args.args
    assert json.loads(options)['dbms'] == 'db2'


def test_obfuscation_failures_drop_rows_and_emit_error(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.tags = ['foo:bar']
    check.statement_metrics.log = mock.MagicMock()

    with mock.patch.object(db_utils.datadog_agent, 'obfuscate_sql', side_effect=RuntimeError('obfuscator failed')):
        rows = check.statement_metrics._normalize_queries([{'stmt_text': 'SELECT 1'}])

    assert rows == []
    aggregator.assert_metric_has_tag(
        'dd.db2.statement_metrics.error',
        'error:obfuscate-query-RuntimeError',
    )


def test_missing_required_pkg_cache_stmt_columns_returns_no_events(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.log = mock.MagicMock()
    check.connection.query = mock.Mock(
        return_value=(
            [],
            [
                'executable_id',
                'member',
                'num_exec_with_metrics',
                'total_cpu_time',
            ],
        )
    )

    check.statement_metrics.run_job()

    check.connection.query.assert_called_once_with('dbm-query-metrics-', PKG_CACHE_INTROSPECTION_QUERY)
    check.statement_metrics.log.warning.assert_called_once_with(
        'Unable to collect Db2 statement metrics because required columns are unavailable: %s',
        'stmt_text',
    )
    assert not aggregator.get_event_platform_events('dbm-metrics')
    assert not aggregator.get_event_platform_events('dbm-samples')


def test_statement_metrics_query_errors_are_handled(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.log = mock.MagicMock()
    check.connection.query = mock.Mock(side_effect=Exception('missing package cache grant'))

    check.statement_metrics.run_job()

    check.statement_metrics.log.warning.assert_called_once_with('Unable to collect Db2 statement metrics: %s', mock.ANY)
    aggregator.assert_metric_has_tag(
        'dd.db2.statement_metrics.error',
        'error:database-Exception',
    )
    assert not aggregator.get_event_platform_events('dbm-metrics')
    assert not aggregator.get_event_platform_events('dbm-samples')


def test_statement_metrics_query_orders_before_limit(instance: dict[str, Any]) -> None:
    check = _dbm_check(instance)
    check.connection.query = mock.Mock(
        side_effect=[
            (
                [],
                [
                    'executable_id',
                    'stmt_text',
                    'member',
                    'num_exec_with_metrics',
                    'total_cpu_time',
                ],
            ),
            ([{'name': 'mon_act_metrics', 'value': 'BASE'}], []),
            ([], []),
        ]
    )

    check.statement_metrics.run_job()

    query = check.connection.query.call_args_list[2].args[1]
    assert 'ORDER BY NUM_EXEC_WITH_METRICS DESC FETCH FIRST 10000 ROWS ONLY' in query
    assert 'STMT_TEXT' not in query


def test_statement_metrics_drops_timing_columns_when_monitor_metrics_disabled(instance: dict[str, Any]) -> None:
    check = _dbm_check(instance)
    check.statement_metrics.log = mock.MagicMock()
    check.connection.query = mock.Mock(
        side_effect=[
            (
                [],
                [
                    'executable_id',
                    'stmt_text',
                    'member',
                    'num_exec_with_metrics',
                    'total_cpu_time',
                    'stmt_exec_time',
                    'rows_read',
                ],
            ),
            ([{'name': 'mon_act_metrics', 'value': 'NONE'}], []),
            ([], []),
        ]
    )

    check.statement_metrics.run_job()

    query = check.connection.query.call_args_list[2].args[1]
    assert 'total_cpu_time' not in query
    assert 'stmt_exec_time' not in query
    assert 'rows_read' in query
    check.statement_metrics.log.warning.assert_called_once_with(
        'Db2 statement timing metrics are disabled because mon_act_metrics is NONE. '
        'Set mon_act_metrics to BASE or EXTENDED to collect timing metrics.'
    )


@pytest.mark.parametrize(
    'stmt_text, stmt_text_length, expected',
    [
        ('select 1', 8, NOT_TRUNCATED),
        ('select 1', STMT_TEXT_LIMIT, NOT_TRUNCATED),
        ('select 1', STMT_TEXT_LIMIT + 1, TRUNCATED),
        ('select 1', None, UNKNOWN_TRUNCATED),
        ('x' * STMT_TEXT_LIMIT, 'not-a-length', TRUNCATED),
        ('select 1', 'not-a-length', UNKNOWN_TRUNCATED),
        (None, 'not-a-length', UNKNOWN_TRUNCATED),
    ],
    ids=[
        'known-short',
        'known-at-limit',
        'known-over-limit',
        'missing-length',
        'invalid-length-full-text',
        'invalid-length-short-text',
        'invalid-length-missing-text',
    ],
)
def test_query_truncated_states(stmt_text: str | None, stmt_text_length: int | str | None, expected: str) -> None:
    assert Db2StatementMetrics._query_truncated(stmt_text, stmt_text_length) == expected


def test_query_metrics_payloads_split_for_small_batch_content_size(instance: dict[str, Any]) -> None:
    statement_metrics = _dbm_check(instance).statement_metrics
    payload_wrapper = {'host': 'db2.example.com', 'kind': 'query_metrics'}
    rows = [
        {
            'query_signature': 'signature-{}'.format(index),
            'query': 'select * from orders where id = {}'.format(index),
            'stmt_text': 'select * from orders where id = {}'.format(index),
            'stmt_text_length': 39,
            'num_exec_with_metrics': index,
        }
        for index in range(1, 5)
    ]
    max_single_payload_size = max(_payload_size(statement_metrics, payload_wrapper, [row]) for row in rows)
    statement_metrics.batch_max_content_size = max_single_payload_size + 1

    payloads = statement_metrics._get_query_metrics_payloads(payload_wrapper, rows)

    assert len(payloads) > 1
    assert all(len(payload) < statement_metrics.batch_max_content_size for payload in payloads)
    payload_rows = [row for payload in payloads for row in json.loads(payload)['db2_rows']]
    assert {row['query_signature'] for row in payload_rows} == {row['query_signature'] for row in rows}
    assert all('stmt_text' not in row for row in payload_rows)
    assert all('stmt_text_length' not in row for row in payload_rows)


def test_query_metrics_payloads_drop_single_oversized_row(instance: dict[str, Any]) -> None:
    statement_metrics = _dbm_check(instance).statement_metrics
    statement_metrics.log = mock.MagicMock()
    statement_metrics.batch_max_content_size = 1
    row = {
        'query_signature': 'oversized',
        'query': 'select * from oversized_table',
        'num_exec_with_metrics': 1,
    }

    payloads = statement_metrics._get_query_metrics_payloads({'kind': 'query_metrics'}, [row])

    assert payloads == []
    statement_metrics.log.warning.assert_called_once_with(
        'A single Db2 query metrics row is too large to send to Datadog. This row will be dropped.'
    )
