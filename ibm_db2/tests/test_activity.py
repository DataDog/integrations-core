# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta
from typing import Any

import mock
import pytest

from datadog_checks.ibm_db2 import IbmDb2Check
from datadog_checks.ibm_db2.statement_samples import ACTIVITY_QUERY, APPLICATION_HANDLE_QUERY

pytestmark = pytest.mark.unit


def _dbm_check(instance: dict[str, Any]) -> IbmDb2Check:
    instance.update(
        {
            'dbm': True,
            'query_activity': {'run_sync': True, 'collection_interval': 0.1},
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'
    return check


def test_query_activity_payload(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    now = datetime(2026, 1, 1, 12, 0, 2)
    check.connection.query = mock.Mock(
        side_effect=[
            ([{'application_handle': 100}], []),
            (
                [
                    {
                        'now': now,
                        'application_handle': 200,
                        'application_id': 'app-id',
                        'application_name': 'orders-app',
                        'session_auth_id': 'DATADOG',
                        'client_applname': 'pytest',
                        'uow_id': 7,
                        'activity_id': 9,
                        'coord_member': 0,
                        'local_start_time': now - timedelta(seconds=2),
                        'activity_state': 'EXECUTING',
                        'activity_type': 'CALL',
                        'executable_id': 'ABC',
                        'stmt_pkg_cache_id': 123,
                        'total_act_time': 1500,
                        'total_act_wait_time': 500,
                        'total_cpu_time': 1000,
                        'query_cost_estimate': 42,
                        'rows_read': 10,
                        'rows_returned': 1,
                        'effective_isolation': 'UR',
                        'stmt_text': 'CALL DBMS_LOCK.SLEEP(5)',
                        'stmt_text_length': 23,
                    }
                ],
                [],
            ),
            (
                [
                    {
                        'application_handle': 200,
                        'uow_id': 7,
                        'workload_occurrence_state': 'UOWEXEC',
                        'uow_start_time': now - timedelta(seconds=3),
                        'total_rqst_time': 3000,
                        'total_wait_time': 500,
                        'total_app_commits': 1,
                        'total_app_rollbacks': 0,
                    }
                ],
                [],
            ),
            ([{'application_name': 'orders-app', 'user': 'DATADOG', 'state': 'UOWEXEC', 'connections': 1}], []),
        ]
    )

    check.statement_samples.run_job()

    event = aggregator.get_event_platform_events('dbm-activity')[0]
    assert event['host'] == 'db2.example.com'
    assert event['database_instance'] == 'db2.example.com:datadog'
    assert event['ddsource'] == 'db2'
    assert event['dbm_type'] == 'activity'
    assert event['db2_version'] == '12.01.0400'
    assert 'db:datadog' in event['ddtags']
    assert event['db2_connections'] == [
        {'application_name': 'orders-app', 'user': 'DATADOG', 'state': 'UOWEXEC', 'connections': 1}
    ]
    assert len(event['db2_activity']) == 1

    row = event['db2_activity'][0]
    assert row['application_handle'] == 200
    assert row['elapsed_time_msec'] == 2000
    assert row['workload_occurrence_state'] == 'UOWEXEC'
    assert row['statement'] == 'CALL DBMS_LOCK.SLEEP(5)'
    assert row['query_truncated'] == 'not_truncated'
    assert 'query_signature' in row
    assert 'stmt_text' not in row

    assert check.connection.query.call_args_list[0].args[1] == APPLICATION_HANDLE_QUERY
    assert check.connection.query.call_args_list[1].args[1] == ACTIVITY_QUERY.format(
        stmt_text_limit=16384, row_limit=3500
    )
    assert check.connection.query.call_args_list[1].kwargs['params'] == [100]
    assert check.connection.query.call_args_list[2].kwargs['params'] == [100]
    assert check.connection.query.call_args_list[3].kwargs['params'] == [100]


def test_query_activity_obfuscation_errors_are_handled(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.connection.query = mock.Mock(
        side_effect=[
            ([{'application_handle': 100}], []),
            ([{'application_handle': 200, 'uow_id': 1, 'stmt_text': 'SELECT 1', 'stmt_text_length': 8}], []),
            ([], []),
            ([], []),
        ]
    )

    with mock.patch(
        'datadog_checks.ibm_db2.statement_samples.obfuscate_sql_with_metadata',
        side_effect=RuntimeError('obfuscator failed'),
    ):
        check.statement_samples.run_job()

    event = aggregator.get_event_platform_events('dbm-activity')[0]
    assert event['db2_activity'] == []
    aggregator.assert_metric_has_tag('dd.db2.query_activity.error', 'error:obfuscate-query-RuntimeError')


def test_query_activity_database_errors_are_handled(instance: dict[str, Any], aggregator: Any) -> None:
    check = _dbm_check(instance)
    check.statement_samples.log = mock.MagicMock()
    check.connection.query = mock.Mock(side_effect=Exception('missing activity grant'))

    check.statement_samples.run_job()

    check.statement_samples.log.warning.assert_called_once_with('Unable to collect Db2 query activity: %s', mock.ANY)
    aggregator.assert_metric_has_tag('dd.db2.query_activity.error', 'error:database-Exception')
    assert not aggregator.get_event_platform_events('dbm-activity')
