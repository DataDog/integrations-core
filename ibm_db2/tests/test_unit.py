# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json as stdlib_json
from datetime import datetime

import mock
import pytest
from cachetools import TTLCache

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db.query_metrics import ObfuscationResult
from datadog_checks.ibm_db2 import IbmDb2Check, query_metrics
from datadog_checks.ibm_db2.connection import Db2ConnectionError, get_connection_data
from datadog_checks.ibm_db2.utils import scrub_connection_string

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('as_bytes', [False, True])
def test_query_metrics_payload_batches(instance: dict, monkeypatch: pytest.MonkeyPatch, as_bytes: bool):
    """Splitting respects encoded byte limits without losing rows, counters, or collection metadata."""
    instance['dbm'] = True
    collector = IbmDb2Check('ibm_db2', {}, [instance])._query_metrics
    wrapper = {'host': 'db2-test', 'database_instance': 'db2-test', 'timestamp': 1234, 'min_collection_interval': 10}
    rows = [
        {'query': 'SELECT "' + '表' * 60 + '"', 'query_signature': str(i), 'count': i + 1, 'time': (i + 1) * 1000}
        for i in range(4)
    ]

    def serialize(value: dict, **kwargs) -> str | bytes:
        text = stdlib_json.JSONEncoder(ensure_ascii=False, **kwargs).encode(value)
        return text.encode('utf-8') if as_bytes else text

    monkeypatch.setattr(query_metrics, 'METRICS_PAYLOAD_MAX_BYTES', 700)
    with mock.patch.object(query_metrics.json, 'dumps', side_effect=serialize):
        payloads = list(collector._get_query_metrics_payloads(wrapper, rows))
    assert len(payloads) > 1
    decoded_rows = []
    for payload in payloads:
        assert len(payload.encode('utf-8') if isinstance(payload, str) else payload) < 700
        decoded = stdlib_json.loads(payload)
        decoded_rows.extend(decoded.pop('ibm_db2_rows'))
        assert decoded == wrapper
    assert decoded_rows == rows


def test_query_metrics_oversized_row(instance: dict, monkeypatch: pytest.MonkeyPatch, aggregator: AggregatorStub):
    """An oversized row is dropped without losing its neighboring rows or logging SQL text."""
    instance['dbm'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    rows = [{'query': 'SELECT A', 'count': 1}, {'query': 'X' * 1000, 'count': 2}, {'query': 'SELECT B', 'count': 3}]
    monkeypatch.setattr(query_metrics, 'METRICS_PAYLOAD_MAX_BYTES', 200)
    with mock.patch.object(check.log, 'warning') as warning:
        payloads = list(check._query_metrics._get_query_metrics_payloads({'host': 'db2-test'}, rows))
    actual = [row for payload in payloads for row in stdlib_json.loads(payload)['ibm_db2_rows']]
    assert actual == [rows[0], rows[2]]
    warning.assert_called_once()
    assert rows[1]['query'] not in str(warning.call_args)
    aggregator.assert_metric(
        'dd.ibm_db2.statement_metrics.rows_dropped',
        value=1,
        hostname=check.reported_hostname,
        tags=check.debug_stats_kwargs(tags=['reason:payload_too_large'])['tags'],
    )


@pytest.mark.parametrize('enabled', [True, False])
def test_query_metrics_collection_controls(instance: dict, monkeypatch: pytest.MonkeyPatch, enabled: bool):
    """Disabling metrics prevents collection; enabled jobs respect the configured cadence."""
    monkeypatch.setenv('DBM_THREADED_JOB_RUN_SYNC', 'true')
    instance.update(dbm=True, query_metrics={'enabled': enabled, 'collection_interval': 30})
    collector = IbmDb2Check('ibm_db2', {}, [instance])._query_metrics
    with (
        mock.patch.object(collector, 'run_job') as collect,
        mock.patch('datadog_checks.base.utils.db.utils.time.time', return_value=100) as clock,
    ):
        collector.run_job_loop([])
        assert collect.call_count == int(enabled)
        clock.return_value = 129
        collector.run_job_loop([])
        assert collect.call_count == int(enabled)
        clock.return_value = 130
        collector.run_job_loop([])
        assert collect.call_count == 2 * int(enabled)


@pytest.mark.parametrize('timeout', [None, 7])
def test_query_metrics_statement_timeout(instance: dict, timeout: int | None):
    """Both counter scans and text lookups apply the default or configured driver timeout."""
    instance['dbm'] = True
    if timeout is not None:
        instance['query_metrics'] = {'query_timeout': timeout}
    collector = IbmDb2Check('ibm_db2', {}, [instance])._query_metrics
    with (
        mock.patch.object(collector._connection, 'ensure_connected'),
        mock.patch('ibm_db.prepare') as prepare,
        mock.patch('ibm_db.execute'),
        mock.patch('ibm_db.fetch_assoc', return_value=False),
        mock.patch('ibm_db.free_stmt'),
    ):
        collector.run_job()
        collector._fetch_statement_texts({(0, '01', datetime(2026, 1, 1))})
    assert len(prepare.call_args_list) == 2
    for call in prepare.call_args_list:
        assert call.args[2] == {query_metrics.ibm_db.SQL_ATTR_QUERY_TIMEOUT: timeout or 10}


def test_query_metrics_recover_after_text_lookup_failure(instance: dict, aggregator: AggregatorStub):
    instance['dbm'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    collector = check._query_metrics
    inserted = datetime(2026, 1, 1)
    counters = ('count', 'time', 'cpu_time', 'rows_read', 'rows_returned')

    def snapshot(cached_count: int, uncached_count: int) -> list[dict | bool]:
        return [
            {
                'member': 0,
                'executable_id': executable_id,
                'insert_timestamp': inserted,
                **dict.fromkeys(counters, count),
            }
            for executable_id, count in ((b'\x01', cached_count), (b'\x02', uncached_count))
        ] + [False]

    with (
        mock.patch.object(collector._connection, 'ensure_connected'),
        mock.patch('ibm_db.prepare'),
        mock.patch('ibm_db.execute'),
        mock.patch('ibm_db.free_stmt'),
        mock.patch(
            'ibm_db.fetch_assoc',
            side_effect=snapshot(10, 10) + snapshot(12, 10) + snapshot(15, 15) + snapshot(18, 18),
        ),
        mock.patch.object(
            collector,
            '_fetch_statement_texts',
            side_effect=[
                {(0, '01', inserted): 'SELECT A FROM T'},
                Db2ConnectionError('text lookup failed'),
                {(0, '02', inserted): 'SELECT B FROM T'},
            ],
        ),
    ):
        collector.run_job()
        collector.run_job()
        assert len(aggregator.get_event_platform_events('dbm-metrics')) == 1

        with pytest.raises(Db2ConnectionError, match='text lookup failed'):
            collector.run_job()
        assert len(aggregator.get_event_platform_events('dbm-metrics')) == 1

        collector.run_job()

    payloads = aggregator.get_event_platform_events('dbm-metrics')
    assert len(payloads) == 2
    aggregator.assert_metric('dd.ibm_db2.operation.error', value=1, hostname=check.reported_hostname)
    aggregator.assert_metric('dd.ibm_db2.operation.time', hostname=check.reported_hostname)
    for name in ('hits', 'misses', 'fetched'):
        aggregator.assert_metric(f'dd.ibm_db2.statement_metrics.lookup.{name}', value=1)
    rows = {row['query']: row for row in payloads[-1]['ibm_db2_rows']}
    assert set(rows) == {'SELECT A FROM T', 'SELECT B FROM T'}
    for query, expected in (('SELECT A FROM T', 6), ('SELECT B FROM T', 8)):
        row = rows[query]
        assert row['count'] == expected
        assert row['time'] == expected * 1_000_000
        assert row['cpu_time'] == expected * 1_000
        assert row['rows_read'] == expected
        assert row['rows_returned'] == expected


def test_full_query_text_refresh(instance: dict, aggregator: AggregatorStub):
    """Text events retain query identity and metadata, suppress repeats, and refresh after the TTL."""
    instance.update(dbm=True, service='db2-test', tags=['team:dbm', 'dd.internal.secret:test'])
    clock = mock.Mock(return_value=0)
    with mock.patch.object(query_metrics, 'TTLCache', side_effect=lambda **kwargs: TTLCache(timer=clock, **kwargs)):
        check = IbmDb2Check('ibm_db2', {}, [instance])
    statement = ObfuscationResult(
        obfuscated_query='SELECT ID FROM APP.ORDERS WHERE ID > ?',
        query_signature='test-signature',
        tables=['APP.ORDERS'],
        commands=['SELECT'],
        comments=None,
    )
    check._query_metrics._submit_full_query_text(statement)
    check._query_metrics._submit_full_query_text(statement)
    events = aggregator.get_event_platform_events('dbm-samples')
    assert len(events) == 1
    event = events[0]
    assert event['dbm_type'] == 'fqt'
    assert event['ddsource'] == 'ibm_db2'
    assert event['database_instance'] == check.database_identifier
    assert event['host'] == check.reported_hostname
    assert event['service'] == 'db2-test'
    assert event['ddagentversion'] == check.agent_version
    assert event['timestamp'] > 0
    assert set(event['ddtags'].split(',')) == {'team:dbm', f"db:{instance['db']}"}
    assert event['db'] == {
        'instance': instance['db'],
        'query_signature': 'test-signature',
        'statement': 'SELECT ID FROM APP.ORDERS WHERE ID > ?',
        'metadata': {'tables': ['APP.ORDERS'], 'commands': ['SELECT']},
    }
    clock.return_value = query_metrics.FULL_QUERY_TEXT_REFRESH_INTERVAL
    check._query_metrics._submit_full_query_text(statement)
    assert len(aggregator.get_event_platform_events('dbm-samples')) == 2


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
    ibmdb2._connection.conn = conn1

    def mock_exception(*args, **kwargs):
        raise Db2ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', return_value=mock.MagicMock()):
            with pytest.raises(Db2ConnectionError, match='CLI0106E  Connection is closed. SQLSTATE=08003'):
                ibmdb2.check(instance)
        # new connection made
        assert ibmdb2._connection.conn != conn1
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.OK)


def test_fails_to_reconnect(aggregator, instance):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    conn1 = mock.MagicMock()
    ibmdb2._connection.conn = conn1

    def mock_exception(*args, **kwargs):
        raise Db2ConnectionError("[IBM][CLI Driver] CLI0106E  Connection is closed. SQLSTATE=08003")

    with mock.patch('ibm_db.exec_immediate', side_effect=mock_exception):
        with mock.patch('ibm_db.connect', side_effect=mock_exception):
            with pytest.raises(Db2ConnectionError, match='Unable to create new connection'):
                ibmdb2.check(instance)
        # new connection could not be made
        assert ibmdb2._connection.conn is None
    aggregator.assert_service_check(IbmDb2Check.SERVICE_CHECK_CONNECT, IbmDb2Check.CRITICAL)


def test_ok_service_check_is_emitted_on_every_check_run(instance, aggregator):
    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
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
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2.query_instance = query_instance

    with pytest.raises(Exception):
        ibmdb2.query_instance()
        ibmdb2.log.warning.assert_called_with('Encountered error running `%s`: %s', 'query_instance', exception_msg)


def test_non_connection_errors_are_ignored(aggregator, instance):
    erroring_query = mock.Mock(side_effect=Exception("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    ibmdb2.check(instance)
    for query_method in ibmdb2._query_methods:
        query_method.assert_called()


def test_connection_errors_stops_execution(aggregator, instance):
    erroring_query = mock.Mock(side_effect=Db2ConnectionError("I'm broken"))
    erroring_query.__name__ = 'Erroring query'

    ibmdb2 = IbmDb2Check('ibm_db2', {}, [instance])
    ibmdb2._connection.conn = mock.MagicMock()
    ibmdb2._connection.connect = mock.MagicMock()
    ibmdb2._query_methods = (mock.Mock(), erroring_query, mock.Mock())

    with pytest.raises(Db2ConnectionError):
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


def test_get_connection_data():
    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1'
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, None)

    expected = (
        'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;'
        'security=ssl;sslservercertificate=/path/cert'
    )
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', '/path/cert', None)

    expected = 'database=db1;hostname=host1;port=1000;protocol=tcpip;uid=user1;pwd=pass1;connecttimeout=1'
    assert (expected, '', '') == get_connection_data('db1', 'user1', 'pass1', 'host1', 1000, 'none', None, 1)


def test_cancel_closes_check_and_custom_query_connections(instance):
    instance['custom_queries'] = [{'metric_prefix': 'ibm_db2', 'query': 'SELECT 1', 'columns': [{}]}]
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check_conn = mock.MagicMock()
    job_conn = mock.MagicMock()
    check._connection.conn = check_conn
    check._custom_metrics._connection.conn = job_conn

    with mock.patch('ibm_db.close') as close:
        check.cancel()

    close.assert_has_calls([mock.call(job_conn), mock.call(check_conn)], any_order=True)
