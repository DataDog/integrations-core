# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterator
from datetime import datetime
from threading import Event, Thread
from unittest import mock

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.ibm_db2 import IbmDb2Check, queries, statements
from datadog_checks.ibm_db2.statements import Db2StatementMetrics

pytestmark = pytest.mark.unit


@pytest.fixture
def dbm_check(instance: dict) -> Iterator[IbmDb2Check]:
    instance.update(dbm=True, query_metrics={'run_sync': True})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._dbms_version = '11.01.0202'
    yield check
    check.cancel()


@pytest.fixture
def collector(dbm_check: IbmDb2Check) -> Db2StatementMetrics:
    return dbm_check._async_job_registry['query-metrics']


def snapshot_row(executable_id: str, count: int, duration: int, generation: int = 1) -> dict:
    return {
        'member': 0,
        'executable_id': executable_id,
        'insert_timestamp': datetime(2026, 1, generation),
        'num_exec_with_metrics': count,
        'coord_stmt_exec_time': duration,
    }


def test_query_metrics_deltas_and_cached_text(collector: Db2StatementMetrics, aggregator: AggregatorStub):
    """Evicting one section must not lose another section's deltas or repeat its SQL text lookup."""
    first = [snapshot_row('AA', 10, 100), snapshot_row('BB', 20, 200)]
    second = [snapshot_row('AA', 12, 104), snapshot_row('BB', 23, 209)]
    third = [snapshot_row('AA', 13, 106)]
    normalized = 'SELECT name FROM customers WHERE id = ?'
    texts = [{**row, 'stmt_text': f'SELECT name FROM customers WHERE id = {i}'} for i, row in enumerate(first)]
    with (
        mock.patch.object(collector, '_execute_query', side_effect=[first, second, texts, third]) as execute,
        mock.patch(
            'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
            return_value={'query': normalized, 'metadata': {}},
        ) as obfuscate,
    ):
        for _ in range(3):
            collector.run_job()

    events = aggregator.get_event_platform_events('dbm-metrics')
    assert events[0]['ibm_db2_rows'] == []
    assert events[1]['ibm_db2_rows'] == [
        {'query': normalized, 'query_signature': compute_sql_signature(normalized), 'count': 5, 'time': 13_000_000}
    ]
    assert events[2]['ibm_db2_rows'][0]['count'] == 1
    assert events[2]['ibm_db2_rows'][0]['time'] == 2_000_000
    assert events[1]['kind'] == 'query_metrics'
    assert events[1]['database_instance'] == f'{collector._check.reported_hostname}:50000'
    assert events[1]['host'] == collector._check.reported_hostname
    assert events[1]['ibm_db2_version'] == '11.01.0202'
    assert events[1]['min_collection_interval'] == 10
    assert set(events[1]['tags']) == {'foo:bar', 'db:datadog'}
    assert events[1]['timestamp'] > 1_000_000_000_000
    assert obfuscate.call_count == 2
    text_calls = [call for call in execute.call_args_list if call.args[0] != queries.STATEMENT_METRICS]
    assert len(text_calls) == 1
    assert text_calls[0].args[1] == ('AA', 'BB')


@pytest.mark.parametrize(
    'init_config, service_config, expected',
    [
        ({'service': 'shared-service'}, {}, 'shared-service'),
        ({'service': 'shared-service'}, {'service': 'instance-service'}, 'instance-service'),
        ({'service': 'shared-service'}, {'service': ''}, 'shared-service'),
        ({}, {'service': 'instance-service'}, 'instance-service'),
        ({}, {}, ''),
    ],
)
def test_query_metrics_service(
    instance: dict, aggregator: AggregatorStub, init_config: dict, service_config: dict, expected: str
):
    """DBM payloads must preserve the shared service unless an instance service overrides it."""
    instance.update(dbm=True, query_metrics={'run_sync': True}, **service_config)
    check = IbmDb2Check('ibm_db2', init_config, [instance])
    collector = check._async_job_registry['query-metrics']
    try:
        with mock.patch.object(collector, '_execute_query', return_value=[]):
            collector.run_job()
        assert aggregator.get_event_platform_events('dbm-metrics')[0]['service'] == expected
    finally:
        check.cancel()


@pytest.mark.parametrize('eviction', ['empty', 'recompiled'])
def test_evicted_statement_gets_a_new_baseline(
    collector: Db2StatementMetrics, aggregator: AggregatorStub, eviction: str
):
    """A reused executable ID must not inherit old counters or cached SQL after eviction or recompilation."""
    first = snapshot_row('AA', 10, 100)
    old_text = {**first, 'stmt_text': 'VALUES 1'}
    new = snapshot_row('AA', 50, 500, generation=2 if eviction == 'recompiled' else 1)
    snapshots = [[first], [snapshot_row('AA', 11, 102)], [old_text]]
    if eviction == 'empty':
        snapshots.append([])
    snapshots.extend([[new], [{**new, 'num_exec_with_metrics': 52, 'coord_stmt_exec_time': 503}]])
    snapshots.append([{**new, 'stmt_text': 'SELECT name FROM customers'}])
    with mock.patch.object(collector, '_execute_query', side_effect=snapshots):
        for _ in range(5 if eviction == 'empty' else 4):
            collector.run_job()

    events = aggregator.get_event_platform_events('dbm-metrics')
    assert events[-2]['ibm_db2_rows'] == []
    assert events[-1]['ibm_db2_rows'] == [
        {
            'query': 'SELECT name FROM customers',
            'query_signature': compute_sql_signature('SELECT name FROM customers'),
            'count': 2,
            'time': 3_000_000,
        }
    ]


@pytest.mark.parametrize('reject', ['monitoring', 'obfuscation_error'])
def test_unreportable_text_is_not_sent_or_fetched_repeatedly(
    collector: Db2StatementMetrics, aggregator: AggregatorStub, reject: str
):
    """Monitoring queries and unobfuscatable text must not leak into payloads or trigger repeated text fetches."""
    first = snapshot_row('AA', 10, 100)
    raw_text = '\n/* DDIGNORE */ SELECT 1' if reject == 'monitoring' else "VALUES 'sensitive-value'"
    with (
        mock.patch.object(
            collector,
            '_execute_query',
            side_effect=[
                [first],
                [snapshot_row('AA', 11, 102)],
                [{**first, 'stmt_text': raw_text}],
                [snapshot_row('AA', 12, 104)],
            ],
        ) as execute,
        mock.patch(
            'datadog_checks.base.utils.db.query_metrics.obfuscation.obfuscate_sql_with_metadata',
            side_effect=ValueError('Unsupported SQL'),
        ),
    ):
        for _ in range(3):
            collector.run_job()
    assert all(event['ibm_db2_rows'] == [] for event in aggregator.get_event_platform_events('dbm-metrics'))
    assert execute.call_count == 4


def test_text_lookup_batches_parameters_and_rejects_replaced_sections(collector: Db2StatementMetrics):
    """Text lookup must bind identifiers and ignore a section replaced after the counter snapshot."""
    requested = [snapshot_row(key, 1, 1) for key in ('AA', 'BB', 'CC')]
    replacement = {**snapshot_row('AA', 1, 1, generation=2), 'stmt_text': 'VALUES 1'}
    valid = {**requested[2], 'stmt_text': 'VALUES 2'}
    with (
        mock.patch.object(statements, 'TEXT_FETCH_BATCH_SIZE', 2),
        mock.patch.object(collector, '_execute_query', side_effect=[[replacement], [valid]]) as execute,
    ):
        result = collector._fetch_query_texts({statements.statement_key(row) for row in requested})
    assert result == {statements.statement_key(valid): 'VALUES 2'}
    assert [call.args[1] for call in execute.call_args_list] == [('AA', 'BB'), ('CC',)]
    assert 'IN (?, ?)' in execute.call_args_list[0].args[0]


@pytest.mark.parametrize('fail', [False, True])
def test_native_statement_handles_are_released(collector: Db2StatementMetrics, fail: bool):
    """Successful and failed fetches must release native statement handles on the worker's own connection."""
    connection, statement = object(), object()
    row = snapshot_row('AA', 1, 1)
    with (
        mock.patch.object(collector._check, 'get_connection', return_value=connection),
        mock.patch.object(statements.ibm_db, 'prepare', return_value=statement) as prepare,
        mock.patch.object(statements.ibm_db, 'execute') as execute,
        mock.patch.object(
            statements.ibm_db, 'fetch_assoc', side_effect=RuntimeError('fetch failed') if fail else [row, False]
        ),
        mock.patch.object(statements.ibm_db, 'free_stmt') as free,
        mock.patch.object(statements.ibm_db, 'close'),
    ):
        try:
            if fail:
                with pytest.raises(statements.Db2QueryError, match='fetch failed'):
                    collector._execute_query('SELECT ? FROM SYSIBM.SYSDUMMY1', ('AA',))
            else:
                assert collector._execute_query('SELECT ? FROM SYSIBM.SYSDUMMY1', ('AA',)) == [row]
            prepare.assert_called_once_with(connection, 'SELECT ? FROM SYSIBM.SYSDUMMY1')
            execute.assert_called_once_with(statement, ('AA',))
            free.assert_called_once_with(statement)
            assert collector._check._conn is None
        finally:
            collector._close_connection()


def test_failed_snapshot_does_not_emit_idle_payload(collector: Db2StatementMetrics, aggregator: AggregatorStub):
    """A database failure must not be reported as a successful idle collection and must release its connection."""
    connection = object()
    collector._conn = connection
    with (
        mock.patch.object(collector, '_execute_query', side_effect=RuntimeError('database unavailable')),
        mock.patch.object(statements.ibm_db, 'close') as close,
    ):
        with pytest.raises(RuntimeError, match='database unavailable'):
            collector.run_job()
        close.assert_called_once_with(connection)
    assert aggregator.get_event_platform_events('dbm-metrics') == []


@pytest.mark.parametrize('dbm, enabled', [(False, True), (True, False)])
def test_disabled_collection_does_not_connect_or_submit(
    instance: dict, aggregator: AggregatorStub, dbm: bool, enabled: bool
):
    """Either disabling switch must prevent query collection connections and metering payloads."""
    instance.update(dbm=dbm, query_metrics={'enabled': enabled})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    with mock.patch.object(check, 'get_connection') as connect:
        check.run_async_jobs(check.tags)
        check.cancel()
    connect.assert_not_called()
    assert aggregator.get_event_platform_events('dbm-metrics') == []


@pytest.mark.parametrize('interval', [0, -1, float('inf'), float('nan'), 'invalid', None])
def test_invalid_collection_interval(instance: dict, interval: float | str | None):
    """Invalid intervals must fail configuration before a worker can spin or divide by zero."""
    instance.update(dbm=True, query_metrics={'collection_interval': interval})
    with pytest.raises(ConfigurationError, match='positive finite'):
        IbmDb2Check('ibm_db2', {}, [instance])


def test_dbm_requires_host_without_breaking_cataloged_connections(instance: dict):
    """DBM must reject ambiguous instance identity while ordinary cataloged database configurations stay valid."""
    instance.pop('host')
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check.cancel()
    instance['dbm'] = True
    with pytest.raises(ConfigurationError, match='explicit host'):
        IbmDb2Check('ibm_db2', {}, [instance])


@pytest.mark.parametrize('dbm', [False, True])
def test_monitoring_queries_are_excluded_when_dbm_enabled(instance: dict, dbm: bool):
    """Agent infrastructure and custom queries must not appear as application query metrics."""
    instance['dbm'] = dbm
    check = IbmDb2Check('ibm_db2', {}, [instance])
    with mock.patch.object(statements.ibm_db, 'exec_immediate') as execute:
        assert list(check.iter_rows('VALUES 1', mock.Mock(return_value=False))) == []
    submitted_query = execute.call_args.args[1]
    if dbm:
        assert statements.classify_query_text(submitted_query) == statements.TextKind.EXCLUDED
    else:
        assert submitted_query == 'VALUES 1'
    check.cancel()


@pytest.mark.parametrize('metadata_enabled', [True, False])
def test_check_starts_collector_with_independent_connection(
    instance: dict, aggregator: AggregatorStub, metadata_enabled: bool
):
    """The check must wire DBM submission through a separate connection and close both connections when unscheduled."""
    instance.update(dbm=True, query_metrics={'run_sync': True})
    check = IbmDb2Check('ibm_db2', {}, [instance])
    check._query_methods = ()
    main_connection, worker_connection = object(), object()
    with (
        mock.patch.object(check, 'get_connection', side_effect=[main_connection, worker_connection]) as connect,
        mock.patch.object(check, 'is_metadata_collection_enabled', return_value=metadata_enabled),
        mock.patch.object(statements.ibm_db, 'get_db_info', return_value='11.01.0202'),
        mock.patch.object(statements.ibm_db, 'exec_immediate', return_value=object()) as execute,
        mock.patch.object(statements.ibm_db, 'fetch_assoc', return_value=False),
        mock.patch.object(statements.ibm_db, 'free_stmt'),
        mock.patch.object(statements.ibm_db, 'close') as close,
    ):
        check.check(instance)
        check.cancel()
    assert connect.call_count == 2
    execute.assert_called_once_with(worker_connection, queries.STATEMENT_METRICS)
    assert {call.args[0] for call in close.call_args_list} == {main_connection, worker_connection}
    assert len(close.call_args_list) == 2
    assert aggregator.get_event_platform_events('dbm-metrics')[0]['ibm_db2_version'] == '11.01.0202'


def test_async_cancel_waits_for_native_query(instance: dict, aggregator: AggregatorStub):
    """Unscheduling must wait for the worker's native query before closing its connection."""
    instance['dbm'] = True
    check = IbmDb2Check('ibm_db2', {}, [instance])
    started, release = Event(), Event()
    stopper = Thread(target=check.cancel)
    collector = check._async_job_registry['query-metrics']
    connection = object()

    def fetch(statement: object) -> bool:
        started.set()
        assert release.wait(5)
        return False

    with (
        mock.patch.object(check, 'get_connection', return_value=connection),
        mock.patch.object(statements.ibm_db, 'exec_immediate', return_value=object()),
        mock.patch.object(statements.ibm_db, 'fetch_assoc', side_effect=fetch),
        mock.patch.object(statements.ibm_db, 'free_stmt'),
        mock.patch.object(statements.ibm_db, 'close') as close,
    ):
        try:
            check.run_async_jobs(check.tags)
            assert started.wait(5)
            stopper.start()
            assert collector._cancel_event.wait(5)
            assert stopper.is_alive()
            close.assert_not_called()
        finally:
            release.set()
            if stopper.ident is not None:
                stopper.join(5)
            else:
                check.cancel()
        assert not stopper.is_alive()
        close.assert_called_once_with(connection)
    assert aggregator.get_event_platform_events('dbm-metrics') == []


def test_payload_batching_preserves_metrics(collector: Db2StatementMetrics, aggregator: AggregatorStub):
    """Oversized batches must be split without losing query rows or sending an oversized event."""
    rows = [{'query': 'SELECT 名字 FROM customers', 'query_signature': str(i), 'count': i, 'time': i} for i in range(5)]
    with mock.patch.object(statements, 'MAX_PAYLOAD_SIZE', 240):
        collector._submit_payloads({'kind': 'query_metrics'}, rows)
    events = aggregator.get_event_platform_events('dbm-metrics')
    assert len(events) > 1
    assert [row for event in events for row in event['ibm_db2_rows']] == rows
    assert all(
        len(payload.encode('utf-8')) <= 240
        for payload in aggregator.get_event_platform_events('dbm-metrics', parse_json=False)
    )
