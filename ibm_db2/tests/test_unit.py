# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from time import sleep
from typing import Any

import mock
import pytest
from requests import ConnectionError

from datadog_checks.ibm_db2 import IbmDb2Check, queries
from datadog_checks.ibm_db2.utils import hadr_status_to_service_check, scrub_connection_string

pytestmark = pytest.mark.unit


def row_from_columns(columns: tuple[str, ...], default: Any = 1) -> dict[str, Any]:
    row = {}
    for column in columns:
        key = column.split(' AS ')[-1] if ' AS ' in column else column
        row[key] = default
    return row


def test_metric_family_config_gates(instance: dict[str, Any]) -> None:
    instance.update(
        {
            'collect_table_metrics': True,
            'table_metrics_limit': 12,
            'collect_index_metrics': True,
            'index_metrics_limit': 34,
            'collect_connection_metrics': True,
            'connection_metrics_limit': 56,
            'collect_fcm_metrics': True,
            'collect_fcm_connection_metrics': True,
            'collect_cf_metrics': True,
            'collect_group_bufferpool_metrics': True,
        }
    )

    check = IbmDb2Check('ibm_db2', {}, [instance])

    assert check._config.collect_table_metrics is True
    assert check._config.table_metrics_limit == 12
    assert check._config.collect_index_metrics is True
    assert check._config.index_metrics_limit == 34
    assert check._config.collect_connection_metrics is True
    assert check._config.connection_metrics_limit == 56
    assert check._config.collect_fcm_metrics is True
    assert check._config.collect_fcm_connection_metrics is True
    assert check._config.collect_cf_metrics is True
    assert check._config.collect_group_bufferpool_metrics is True


def test_dbm_connection_cache_is_locked(instance: dict[str, Any]) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    barrier = Barrier(3)
    connection = object()

    def connect() -> object:
        sleep(0.05)
        return connection

    def get_connection() -> object:
        barrier.wait()
        return check.connection.get_connection('dbm-test-')

    check.connection._connect = mock.Mock(side_effect=connect)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(get_connection), executor.submit(get_connection)]
        barrier.wait()

    assert [result.result() for result in results] == [connection, connection]
    check.connection._connect.assert_called_once_with()


class TestPasswordScrubber:
    def test_start(self):
        s = 'pwd=password;...'

        assert scrub_connection_string(s) == 'pwd=********;...'

    def test_end(self):
        s = '...;pwd=password'

        assert scrub_connection_string(s) == '...;pwd=********'

    def test_no_match_within_value(self):
        s = '...pwd=password;...'

        assert scrub_connection_string(s) == s


def test_retry_connection(aggregator, instance):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    conn1 = mock.MagicMock()
    ibmdb2._conn = conn1

    def mock_exception(*args, **kwargs):
        raise ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', return_value=mock.MagicMock()):
            with pytest.raises(ConnectionError, match='CLI0106E  Connection is closed. SQLSTATE=08003'):
                ibmdb2.check(instance)
        # new connection made
        assert ibmdb2._conn != conn1
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.OK)


def test_fails_to_reconnect(aggregator, instance):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    conn1 = mock.MagicMock()
    ibmdb2._conn = conn1

    def mock_exception(*args, **kwargs):
        raise ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', side_effect=mock_exception):
            with pytest.raises(ConnectionError, match='Unable to create new connection'):
                ibmdb2.check(instance)
        # new connection could not be made
        assert ibmdb2._conn is None
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.CRITICAL)


def test_ok_service_check_is_emitted_on_every_check_run(instance, aggregator):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._conn = mock.MagicMock()
    with mock.patch('ibm_db.exec_immediate'):
        ibmdb2.check(instance)
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.OK)


def test_query_function_error(aggregator, instance):
    exception_msg = (
        '[IBM][CLI Driver][DB2/NT64] SQL0440N  No authorized routine named "MON_GET_INSTANCE" of type '
        '"FUNCTION" having compatible arguments was found.  SQLSTATE=42884'
    )

    def query_instance(*args, **kwargs):
        raise Exception(exception_msg)

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2.log = mock.MagicMock()
    ibmdb2._conn = mock.MagicMock()
    ibmdb2.get_connection = mock.MagicMock()
    ibmdb2.query_instance = query_instance

    with pytest.raises(Exception):
        ibmdb2.query_instance()
        ibmdb2.log.warning.assert_called_with('Encountered error running `%s`: %s', 'query_instance', exception_msg)


def test_non_connection_errors_are_ignored(aggregator, instance):
    erroring_query = mock.Mock(side_effect=Exception("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._conn = mock.MagicMock()
    ibmdb2.get_connection = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    ibmdb2.check(instance)
    for query_method in ibmdb2._query_methods:
        query_method.assert_called()


def test_connection_errors_stops_execution(aggregator, instance):
    erroring_query = mock.Mock(side_effect=ConnectionError("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._conn = mock.MagicMock()
    ibmdb2.get_connection = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    with pytest.raises(ConnectionError):
        ibmdb2.check(instance)

    ibmdb2._query_methods[0].assert_called()
    ibmdb2._query_methods[1].assert_called()
    ibmdb2._query_methods[2].assert_not_called()


def test_parse_version(instance):
    raw_version = '11.01.0202'
    check = IbmDb2Check('ibm_db2', {}, [instance])
    expected = {
        'major': '11',
        'minor': '1',
        'mod': '2',
        'fix': '2',
    }
    assert check.parse_version(raw_version) == expected


def test_get_connection_data(instance):
    check = IbmDb2Check('ibm_db2', {}, [instance])

    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1'
    assert (expected, '', '') == check.get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, None)

    expected = (
        'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;'
        'security=ssl;sslservercertificate=/path/cert'
    )
    assert (expected, '', '') == check.get_connection_data(
        'db1', 'user1', 'pass1', 'host1', 1000, 'none', '/path/cert', None
    )

    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;connecttimeout=1'
    assert (expected, '', '') == check.get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, 1)


def test_dbm_connection_uses_uncommitted_read_isolation(instance: dict[str, Any]) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    connection = mock.MagicMock()

    with (
        mock.patch('ibm_db.connect', return_value=connection) as connect,
        mock.patch('ibm_db.exec_immediate') as exec_immediate,
    ):
        assert check.connection.get_connection('dbm-test-') is connection

    connect.assert_called_once()
    exec_immediate.assert_called_once_with(connection, 'SET CURRENT ISOLATION UR')


def test_dbm_connection_query_supports_bound_parameters(instance: dict[str, Any]) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    connection = mock.MagicMock()
    cursor = mock.MagicMock()
    check.connection._connections['dbm-test-'] = connection

    with (
        mock.patch('ibm_db.prepare', return_value=cursor) as prepare,
        mock.patch('ibm_db.execute', return_value=True) as execute,
        mock.patch('ibm_db.num_fields', return_value=2),
        mock.patch('ibm_db.field_name', side_effect=['name', 'value']),
        mock.patch('ibm_db.fetch_assoc', side_effect=[{'name': 'mon_act_metrics', 'value': 'BASE'}, False]),
        mock.patch('ibm_db.free_result') as free_result,
    ):
        rows, columns = check.connection.query(
            'dbm-test-',
            'SELECT NAME, VALUE FROM SYSIBMADM.DBCFG WHERE NAME <> ?',
            params=['skip_me'],
        )

    prepare.assert_called_once_with(connection, 'SELECT NAME, VALUE FROM SYSIBMADM.DBCFG WHERE NAME <> ?')
    execute.assert_called_once_with(cursor, ('skip_me',))
    assert rows == [{'name': 'mon_act_metrics', 'value': 'BASE'}]
    assert columns == ['name', 'value']
    free_result.assert_called_once_with(cursor)


def test_database_instance_metadata(instance: dict[str, Any], aggregator: Any) -> None:
    instance.update(
        {
            'dbm': True,
            'reported_hostname': 'db2.example.com',
            'database_identifier': {'template': '$resolved_hostname:$db'},
        }
    )
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '12.01.0400'

    check._send_database_instance_metadata()

    events = aggregator.get_event_platform_events('dbm-metadata')
    event = next(event for event in events if event['kind'] == 'database_instance')
    assert event['host'] == 'db2.example.com'
    assert event['database_hostname'] == 'db2.example.com'
    assert event['database_instance'] == 'db2.example.com:datadog'
    assert event['dbms'] == 'db2'
    assert event['dbms_version'] == '12.01.0400'
    assert event['metadata'] == {'dbm': True, 'connection_host': instance['host']}
    assert 'database_hostname:db2.example.com' in event['tags']
    assert 'database_instance:db2.example.com:datadog' in event['tags']
    assert 'dd.internal.resource:database_instance:db2.example.com:datadog' in event['tags']

    aggregator.reset()
    check._send_database_instance_metadata()

    assert not aggregator.get_event_platform_events('dbm-metadata')


def test_statement_metrics_payload(instance: dict[str, Any], aggregator: Any) -> None:
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
            (
                [
                    {
                        'name': 'mon_act_metrics',
                        'value': 'BASE',
                    }
                ],
                [],
            ),
            (
                [
                    {
                        'executable_id': 'A',
                        'member': 0,
                        'num_exec_with_metrics': 1,
                        'total_cpu_time': 1000,
                        'stmt_exec_time': 10,
                        'rows_read': 5,
                    },
                    {
                        'executable_id': 'B',
                        'member': 0,
                        'num_exec_with_metrics': 4,
                        'total_cpu_time': 2000,
                        'stmt_exec_time': 20,
                        'rows_read': 8,
                    },
                ],
                [],
            ),
            (
                [
                    {
                        'executable_id': 'A',
                        'member': 0,
                        'num_exec_with_metrics': 3,
                        'total_cpu_time': 3000,
                        'stmt_exec_time': 15,
                        'rows_read': 10,
                    },
                    {
                        'executable_id': 'B',
                        'member': 0,
                        'num_exec_with_metrics': 7,
                        'total_cpu_time': 8000,
                        'stmt_exec_time': 30,
                        'rows_read': 20,
                    },
                ],
                [],
            ),
            (
                [{'executable_id': 'A', 'stmt_text': 'select * from orders where id = 1', 'stmt_text_length': 33}],
                [],
            ),
            (
                [{'executable_id': 'B', 'stmt_text': 'select * from orders where id = 1', 'stmt_text_length': 33}],
                [],
            ),
        ]
    )

    check.statement_metrics.run_job()
    assert not aggregator.get_event_platform_events('dbm-metrics')

    check.statement_metrics.run_job()

    metrics_events = aggregator.get_event_platform_events('dbm-metrics')
    assert len(metrics_events) == 1
    metrics_event = metrics_events[0]
    assert metrics_event['host'] == 'db2.example.com'
    assert metrics_event['database_instance'] == 'db2.example.com:datadog'
    assert metrics_event['db2_version'] == '12.01.0400'
    assert metrics_event['tags'] == [
        'foo:bar',
        'database_hostname:db2.example.com',
        'database_instance:db2.example.com:datadog',
    ]
    assert len(metrics_event['db2_rows']) == 1
    row = metrics_event['db2_rows'][0]
    assert row['num_exec_with_metrics'] == 5
    assert row['total_cpu_time'] == 8
    assert row['stmt_exec_time'] == 15
    assert row['rows_read'] == 17
    assert row['db'] == 'datadog'
    assert row['query'] == 'select * from orders where id = 1'
    assert 'query_signature' in row
    assert 'stmt_text' not in row

    sample_events = aggregator.get_event_platform_events('dbm-samples')
    assert len(sample_events) == 1
    sample_event = sample_events[0]
    assert sample_event['dbm_type'] == 'fqt'
    assert sample_event['ddsource'] == 'db2'
    assert sample_event['database_instance'] == 'db2.example.com:datadog'
    assert sample_event['db']['instance'] == 'datadog'
    assert sample_event['db']['statement'] == row['query']
    assert sample_event['db']['query_signature'] == row['query_signature']
    assert sample_event['db']['query_truncated'] == 'not_truncated'
    assert sample_event['db2']['member'] == 0


def test_query_instance_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    now = datetime(2026, 6, 15, 12, 0, 0)
    row = row_from_columns(queries.INSTANCE_TABLE_COLUMNS)
    row.update(
        {
            'current_time': now,
            'db2start_time': now - timedelta(seconds=30),
            'total_connections': 2,
            'agents_registered': 3,
            'agents_registered_top': 4,
            'idle_agents': 5,
            'num_coord_agents': 6,
            'coord_agents_top': 7,
            'agents_from_pool': 8,
            'agents_created_empty_pool': 9,
            'con_local_dbases': 10,
            'member': 0,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_instance()

    aggregator.assert_metric('ibm_db2.connection.active', value=2, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.uptime', value=30, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.agent.created_empty_pool', value=9, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.databases.active', value=10, metric_type=aggregator.GAUGE)


def test_query_database_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    now = datetime(2026, 6, 15, 12, 0, 0)
    row = row_from_columns(queries.DATABASE_TABLE_COLUMNS)
    row.update(
        {
            'current_time': now,
            'last_backup': now - timedelta(seconds=60),
            'db_status': 'ACTIVE',
            'lock_wait_time': 50,
            'lock_waits': 5,
            'lock_list_in_use': 8192,
            'total_app_commits': 11,
            'total_app_rollbacks': 12,
            'rows_inserted': 13,
            'rows_updated': 14,
            'rows_deleted': 15,
            'direct_reads': 16,
            'sort_overflows': 17,
            'total_hash_joins': 18,
            'member': 0,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_database()

    aggregator.assert_metric('ibm_db2.transaction.commits', value=11, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.transaction.rollbacks', value=12, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.row.inserted.total', value=13, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.direct.reads', value=16, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.sort.overflows', value=17, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.hash.joins.total', value=18, metric_type=aggregator.MONOTONIC_COUNT)


def test_query_memory_pool_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = {
        'member': 0,
        'db_name': 'DATADOG',
        'memory_set_type': 'DATABASE',
        'memory_pool_type': 'LOCKMGR',
        'application_handle': None,
        'edu_id': None,
        'memory_pool_used': 4096,
        'memory_pool_used_hwm': 8192,
    }
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_memory_pool()

    tags = ['memory_set:database', 'member:0', 'db:datadog', 'foo:bar', 'memory_pool:lockmgr']
    aggregator.assert_metric('ibm_db2.memory.pool.used', value=4096, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.memory.pool.used_hwm', value=8192, tags=tags, metric_type=aggregator.GAUGE)


def test_query_memory_pool_skips_per_application_pools(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = {
        'member': 0,
        'memory_set_type': 'APPLICATION',
        'memory_pool_type': 'APP_GROUP',
        'application_handle': 123,
        'edu_id': None,
        'memory_pool_used': 4096,
        'memory_pool_used_hwm': 8192,
    }
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_memory_pool()

    aggregator.assert_metric('ibm_db2.memory.pool.used', count=0)


def test_query_memory_set_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = {
        'member': 0,
        'db_name': 'DATADOG',
        'memory_set_type': 'DATABASE',
        'memory_set_committed': 16384,
        'memory_set_used': 8192,
        'memory_set_used_hwm': 12288,
        'additional_committed': 2048,
        'memory_set_size': 32768,
    }
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_memory_set()

    tags = ['memory_set:database', 'member:0', 'db:datadog', 'foo:bar']
    aggregator.assert_metric('ibm_db2.memory.set.committed', value=16384, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.memory.set.used', value=8192, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.memory.set.used_hwm', value=12288, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'ibm_db2.memory.set.additional_committed', value=2048, tags=tags, metric_type=aggregator.GAUGE
    )
    aggregator.assert_metric('ibm_db2.memory.set.size', value=32768, tags=tags, metric_type=aggregator.GAUGE)


def test_query_wlm_workload_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.WLM_WORKLOAD_TABLE_COLUMNS)
    row.update(
        {
            'workload_name': 'SYSDEFAULTUSERWORKLOAD',
            'workload_id': 1,
            'member': 0,
            'total_cpu_time': 1000,
            'act_completed_total': 2,
            'total_wait_time': 3,
            'lock_waits': 4,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_wlm_workload()

    tags = ['workload_name:sysdefaultuserworkload', 'workload_id:1', 'member:0', 'db:datadog', 'foo:bar']
    aggregator.assert_metric(
        'ibm_db2.wlm.total_cpu_time', value=1000, tags=tags, metric_type=aggregator.MONOTONIC_COUNT
    )
    aggregator.assert_metric(
        'ibm_db2.wlm.activities.completed', value=2, tags=tags, metric_type=aggregator.MONOTONIC_COUNT
    )
    aggregator.assert_metric('ibm_db2.wlm.total_wait_time', value=3, tags=tags, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.wlm.lock_waits', value=4, tags=tags, metric_type=aggregator.MONOTONIC_COUNT)


def test_query_wlm_service_class_metrics_disabled(instance: dict[str, Any]) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.iter_rows = mock.Mock()

    check.query_wlm_service_class()

    check.iter_rows.assert_not_called()


def test_query_wlm_service_class_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    instance['collect_wlm_service_class_metrics'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.WLM_SERVICE_SUBCLASS_TABLE_COLUMNS)
    row.update(
        {
            'service_superclass_name': 'SYSDEFAULTUSERCLASS',
            'service_subclass_name': 'SYSDEFAULTSUBCLASS',
            'service_class_id': 12,
            'member': 0,
            'total_cpu_time': 1000,
            'act_completed_total': 2,
            'total_wait_time': 3,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_wlm_service_class()

    tags = [
        'service_superclass:sysdefaultuserclass',
        'service_subclass:sysdefaultsubclass',
        'service_class_id:12',
        'member:0',
        'db:datadog',
        'foo:bar',
    ]
    aggregator.assert_metric(
        'ibm_db2.wlm.total_cpu_time', value=1000, tags=tags, metric_type=aggregator.MONOTONIC_COUNT
    )
    aggregator.assert_metric(
        'ibm_db2.wlm.activities.completed', value=2, tags=tags, metric_type=aggregator.MONOTONIC_COUNT
    )
    aggregator.assert_metric('ibm_db2.wlm.total_wait_time', value=3, tags=tags, metric_type=aggregator.MONOTONIC_COUNT)


def test_query_buffer_pool_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.BUFFER_POOL_TABLE_COLUMNS)
    row.update(
        {
            'bp_name': 'IBMDEFAULTBP',
            'pool_col_gbp_l_reads': 0,
            'pool_data_gbp_l_reads': 0,
            'pool_index_gbp_l_reads': 0,
            'pool_xda_gbp_l_reads': 0,
            'pool_data_writes': 2,
            'pool_index_writes': 3,
            'pool_xda_writes': 4,
            'pool_col_writes': 5,
            'pool_read_time': 6,
            'bp_cur_buffsz': 7,
            'member': 0,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_buffer_pool()

    tags = ['bufferpool:IBMDEFAULTBP', 'member:0', 'db:datadog', 'foo:bar']
    aggregator.assert_metric('ibm_db2.bufferpool.data.writes', value=2, tags=tags)
    aggregator.assert_metric('ibm_db2.bufferpool.writes.total', value=14, tags=tags)
    aggregator.assert_metric('ibm_db2.bufferpool.read_time', value=6, tags=tags)
    aggregator.assert_metric('ibm_db2.bufferpool.pages.configured', value=7, tags=tags)


def test_query_table_space_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.TABLE_SPACE_TABLE_COLUMNS)
    row.update(
        {
            'tbsp_name': 'USERSPACE1',
            'tbsp_state': 'NORMAL',
            'tbsp_page_size': 4096,
            'tbsp_total_pages': 10,
            'tbsp_usable_pages': 8,
            'tbsp_used_pages': 4,
            'tbsp_free_pages': 4,
            'tbsp_page_top': 5,
            'tbsp_pending_free_pages': 2,
            'tbsp_max_size': 32768,
            'tbsp_initial_size': 16384,
            'tbsp_increase_size': 4096,
            'tbsp_num_containers': 3,
            'tbsp_last_resize_failed': 0,
            'tbsp_type': 'DMS',
            'tbsp_content_type': 'ANY',
            'storage_group_name': 'IBMSTOGROUP',
            'member': 0,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_table_space()

    tags = [
        'tablespace:USERSPACE1',
        'tablespace_type:dms',
        'tablespace_content_type:any',
        'storage_group:IBMSTOGROUP',
        'member:0',
        'db:datadog',
        'foo:bar',
    ]
    aggregator.assert_metric('ibm_db2.tablespace.free', value=16384, tags=tags)
    aggregator.assert_metric('ibm_db2.tablespace.high_water_mark', value=20480, tags=tags)
    aggregator.assert_metric('ibm_db2.tablespace.max_utilized', value=50, tags=tags)
    aggregator.assert_metric('ibm_db2.tablespace.online', value=1, tags=tags)


def test_query_container_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    instance['collect_container_metrics'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.CONTAINER_TABLE_COLUMNS)
    row.update(
        {
            'tbsp_name': 'USERSPACE1',
            'container_name': '/database/data/db2inst1/NODE0000/DATADOG/T0000002/C0000000.LRG',
            'container_id': 2,
            'member': 0,
            'container_type': 'FILE',
            'total_pages': 10,
            'usable_pages': 8,
            'accessible': 1,
            'fs_total_size': 100000,
            'fs_used_size': 60000,
            'tbsp_page_size': 4096,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_container()

    tags = [
        'tablespace:userspace1',
        'container:/database/data/db2inst1/node0000/datadog/t0000002/c0000000.lrg',
        'container_id:2',
        'container_type:file',
        'member:0',
        'db:datadog',
        'foo:bar',
    ]
    aggregator.assert_metric('ibm_db2.container.fs_total', value=100000, tags=tags)
    aggregator.assert_metric('ibm_db2.container.fs_used', value=60000, tags=tags)
    aggregator.assert_metric('ibm_db2.container.total', value=40960, tags=tags)
    aggregator.assert_metric('ibm_db2.container.usable', value=32768, tags=tags)
    aggregator.assert_metric('ibm_db2.container.accessible', value=1, tags=tags)


def test_query_container_metrics_disabled(instance: dict[str, Any]) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.iter_rows = mock.Mock()

    check.query_container()

    check.iter_rows.assert_not_called()


def test_query_transaction_log_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    row = row_from_columns(queries.TRANSACTION_LOG_TABLE_COLUMNS)
    row.update(
        {
            'total_log_used': 2048,
            'total_log_available': 4096,
            'num_log_buffer_full': 2,
            'log_hadr_waits_total': 3,
            'log_hadr_wait_time': 4,
            'tot_log_used_top': 8192,
            'member': 0,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_transaction_log()

    aggregator.assert_metric('ibm_db2.log.space.used', value=2048, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.log.space.available', value=4096, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.log.buffer_full', value=2, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.hadr.log_wait.count', value=3, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.hadr.log_wait.time', value=4, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('ibm_db2.log.space.used.max', value=8192, metric_type=aggregator.GAUGE)


@pytest.mark.parametrize(
    'hadr_state,connect_status,expected_status',
    [
        ('PEER', 'CONNECTED', IbmDb2Check.OK),
        ('REMOTE_CATCHUP', 'CONNECTED', IbmDb2Check.WARNING),
        ('REMOTE_CATCHUP_PENDING', 'CONNECTED', IbmDb2Check.WARNING),
        ('PEER', 'CONGESTED', IbmDb2Check.WARNING),
        ('DISCONNECTED_PEER', 'DISCONNECTED', IbmDb2Check.CRITICAL),
        ('UNKNOWN_STATE', 'UNKNOWN', IbmDb2Check.UNKNOWN),
    ],
)
def test_hadr_status_to_service_check(hadr_state: str, connect_status: str, expected_status: int) -> None:
    assert hadr_status_to_service_check(hadr_state, connect_status) == expected_status


def test_query_hadr_standard_database(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.iter_rows = mock.Mock(return_value=iter([]))

    check.query_hadr()

    aggregator.assert_metric(
        'ibm_db2.hadr.role',
        value=1,
        tags=['hadr_role:standard', 'db:datadog', 'foo:bar'],
        metric_type=aggregator.GAUGE,
    )
    aggregator.assert_metric(
        'ibm_db2.hadr.standby.count',
        value=0,
        tags=['db:datadog', 'foo:bar'],
        metric_type=aggregator.GAUGE,
    )


def test_query_hadr_expanded_metrics(instance: dict[str, Any], aggregator: Any) -> None:
    check = IbmDb2Check('ibm_db2', {}, [instance])
    now = datetime(2026, 6, 15, 12, 0, 0)
    row = row_from_columns(queries.HADR_TABLE_COLUMNS)
    row.update(
        {
            'current_time': now,
            'hadr_connect_status': 'CONNECTED',
            'hadr_flags': 'STANDBY_RECV_BLOCKED',
            'hadr_log_gap': 1024,
            'hadr_role': 'PRIMARY',
            'hadr_state': 'PEER',
            'hadr_syncmode': 'NEARSYNC',
            'hadr_timeout': 120,
            'heartbeat_expected': 10,
            'heartbeat_interval': 30,
            'heartbeat_missed': 1,
            'log_hadr_wait_cur': 2,
            'log_stream_id': 0,
            'peer_window': 60,
            'peer_window_end': now + timedelta(seconds=45),
            'primary_log_pos': 5000,
            'primary_log_time': now,
            'sock_recv_buf_actual': 4096,
            'sock_send_buf_actual': 8192,
            'standby_id': 1,
            'standby_log_pos': 4500,
            'standby_member_host': 'standby.example.com',
            'standby_recv_buf_percent': 25,
            'standby_recv_buf_size': 32,
            'standby_recv_replay_gap': 128,
            'standby_replay_log_pos': 4000,
            'standby_replay_log_time': now - timedelta(seconds=5),
            'standby_replay_only_window_tran_count': 3,
            'standby_spool_limit': 64,
            'standby_spool_percent': 10,
            'takeover_app_remaining_primary': 4,
            'takeover_app_remaining_standby': 5,
            'time_since_last_recv': 6,
        }
    )
    check.iter_rows = mock.Mock(return_value=iter([row]))

    check.query_hadr()

    tags = [
        'hadr_role:primary',
        'standby_id:1',
        'log_stream:0',
        'standby_host:standby.example.com',
        'db:datadog',
        'foo:bar',
    ]
    aggregator.assert_metric('ibm_db2.hadr.role', value=1, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.log_gap', value=1024, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.log_wait.current', value=2, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.send_recv_gap', value=500, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.replay_lag', value=5, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.peer_window_remaining', value=45, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.recv_blocked', value=1, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('ibm_db2.hadr.standby.count', value=1, tags=['db:datadog', 'foo:bar'])
    aggregator.assert_metric_has_tag('ibm_db2.hadr.state', 'hadr_state:peer')
    aggregator.assert_metric_has_tag('ibm_db2.hadr.connected', 'connect_status:connected')
    aggregator.assert_metric_has_tag('ibm_db2.hadr.syncmode', 'syncmode:nearsync')
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_HADR_STATUS, status=IbmDb2Check.OK)
