# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from copy import copy
from datetime import datetime, timedelta, timezone

import mock
import pytest

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.column_statistics import (
    TABLE_MAX_BYTES,
    column_statistics,
    fit_table,
    read_tables,
)
from datadog_checks.sqlserver.health import SqlServerHealthEvent

from .common import CHECK_NAME


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    # Column statistics run in the metadata job, which takes run_sync from the settings options.
    instance_docker['collect_settings'] = {'enabled': False, 'run_sync': True}
    instance_docker['collect_column_statistics'] = {'enabled': True}
    return copy(instance_docker)


def run_check(dd_run_check, instance):
    check = SQLServer(CHECK_NAME, {}, [instance])
    try:
        dd_run_check(check)
    finally:
        check.cancel()
    return check


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_collects_column_statistics(aggregator, dd_run_check, dbm_instance):
    # setup.sql seeds datadog_test_column_stats with deterministic data the datadog user can't read directly, so the
    # statistics can only have come through the procedure.
    dbm_instance['database'] = 'datadog_test_column_stats'
    run_check(dd_run_check, dbm_instance)

    events = aggregator.get_event_platform_events("dbm-column-statistics")
    assert len(events) == 1
    event = events[0]
    assert event['ddsource'] == 'sqlserver'
    assert event['dbm_type'] == 'column_statistics'

    tables = event['column_statistics']
    assert [(t['db'], t['schema'], t['table']) for t in tables] == [('datadog_test_column_stats', 'dbo', 'orders')]
    columns = {c['column_name']: c for c in tables[0]['columns']}
    assert set(columns) == {'id', 'customer_id', 'status', 'note', 'unused_num', 'node'}

    # The statistics are sent as SQL Server reports them, read in full after UPDATE STATISTICS WITH FULLSCAN.
    for column in columns.values():
        assert column['rows'] == column['rows_sampled'] == 10_000
        assert column['modification_counter'] == 0
        # The procedure formats it, so every driver sends the same ISO 8601 text. SQL Server leaves out the fraction
        # of a second when it's zero.
        assert re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{7})?Z', column['last_updated'])
        updated = datetime.fromisoformat(column['last_updated'])
        assert abs(datetime.now(timezone.utc) - updated) < timedelta(days=1), "last_updated is in UTC"
    # The properties count the NULL step, which sys.dm_db_stats_histogram leaves out for an all-NULL column, and on
    # Windows SQL Server 2019 for any column, so only columns without NULLs match.
    for name in ('id', 'customer_id', 'note', 'node'):
        assert columns[name]['steps'] == len(columns[name]['histogram']['equal_rows'])
    identity = columns['id']
    assert identity['stats_name'].startswith('PK__')
    assert (identity['type_name'], identity['max_length'], identity['is_nullable']) == ('int', 4, False)
    assert identity['is_unique']
    # Every value of a fixed-width type takes max_length, so only variable-width columns have an average length.
    assert identity['average_length'] is None
    note = columns['note']
    assert (note['stats_name'], note['user_created'], note['auto_created']) == ('st_note', True, False)
    assert (note['type_name'], note['max_length']) == ('nvarchar', 200)
    # nvarchar values of 20 to 40 characters average 60 bytes, which DBCC reports as a 4-byte float.
    assert note['average_length'] == pytest.approx(60, abs=0.01)

    # A CLR type is named, and variable-width, so it has an average length.
    node = columns['node']
    assert (node['type_name'], node['stats_name']) == ('hierarchyid', 'st_node')
    assert node['average_length'] is not None

    # One customer has 3020 of the 10000 rows, the other 349 have 20 each.
    assert max(columns['customer_id']['histogram']['equal_rows']) == 3020
    assert not columns['customer_id']['is_unique']
    # 1000 NULLs, 2000 'pending' and 7000 'shipped'. Windows SQL Server 2019 builds the histogram without a NULL step.
    status = columns['status']['histogram']
    steps = list(zip(status['range_high_key_is_null'], status['equal_rows']))
    assert sorted(rows for is_null, rows in steps if not is_null) == [2000, 7000]
    assert [rows for is_null, rows in steps if is_null] in ([1000], [])
    # 'pending' and 'shipped' are 7 bytes each; DBCC averages over every row, NULLs as 0 bytes.
    assert columns['status']['average_length'] == pytest.approx(6.3, abs=0.01)
    # Every value is NULL, so no step has a value.
    assert not any(not is_null for is_null in columns['unused_num']['histogram']['range_high_key_is_null'])
    aggregator.assert_metric('dd.sqlserver.column_statistics.payloads_count', value=1)
    # Settings are off, so the metadata job ran only for column statistics.
    assert not [e for e in aggregator.get_event_platform_events("dbm-metadata") if e['kind'] == 'sqlserver_configs']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_skips_databases_that_cant_hold_the_procedure(aggregator, dd_run_check, dbm_instance):
    # The system databases never get the procedure, and unavailable_db is offline, so they'd warn forever.
    dbm_instance['database_autodiscovery'] = True
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    # Shutting the check down releases the collector, so keep hold of it.
    collector = check.sql_metadata._column_statistics_collector
    try:
        dd_run_check(check)
    finally:
        check.cancel()

    events = aggregator.get_event_platform_events("dbm-column-statistics")
    assert {t['db'] for e in events for t in e['column_statistics']} == {'datadog_test_column_stats'}
    missing = collector._failing_dbs[SqlServerHealthEvent.COLUMN_STATISTICS_PROCEDURE_NOT_FOUND]
    assert missing, "user databases without the procedure are still reported"
    assert not missing & {'master', 'msdb', 'tempdb', 'model', 'unavailable_db'}


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_missing_procedure_reports_health_event(aggregator, dd_run_check, dbm_instance):
    dbm_instance['database'] = 'datadog_test_schemas'
    run_check(dd_run_check, dbm_instance)

    assert aggregator.get_event_platform_events("dbm-column-statistics") == []
    health = [
        e for e in aggregator.get_event_platform_events("dbm-health") if e['name'].startswith('column_statistics')
    ]
    assert [(e['name'], e['status']) for e in health] == [('column_statistics_procedure_not_found', 'warning')]


def procedure_row(**overrides):
    row = {
        'schema_name': 'dbo',
        'table_name': 'orders',
        'column_name': 'status',
        'stats_name': 'ix_status',
        'auto_created': 0,
        'user_created': 0,
        'type_name': 'varchar',
        'max_length': 20,
        'is_nullable': 1,
        'is_unique': 0,
        'last_updated': '2026-10-28T14:30:00.0000000Z',
        'rows': 10_000,
        'rows_sampled': 6_700,
        'steps': 3,
        'modification_counter': 12,
        'average_length': 6.3,
        'histogram': '1:1000.00:0.00:0.00:1.0000,0:2000.00:0.00:0.00:1.0000,0:7000.00:0.00:0.00:1.0000',
    }
    row.update(overrides)
    return row


def iter_cursor(rows):
    cursor = mock.MagicMock()
    cursor.description = [(name,) for name in rows[0]]
    cursor.fetchone.side_effect = [tuple(row.values()) for row in rows] + [None]
    return cursor


@pytest.mark.unit
def test_fit_table_drops_largest_histograms_first():
    def column(name, steps):
        packed = ','.join('0:123456789.00:123456789.00:123456789.00:1.2345' for _ in range(steps))
        return column_statistics(procedure_row(column_name=name, histogram=packed))

    # Each 200-step histogram is about 11 KB, so about 80 of them fit in a table event.
    table = {'columns': [column('small', 2)] + [column('wide_{}'.format(i), 200) for i in range(100)]}
    size = fit_table(table)

    assert size <= TABLE_MAX_BYTES
    assert size == len(json.dumps(table))
    dropped = [c['column_name'] for c in table['columns'] if c['histogram'] is None]
    assert 0 < len(dropped) < 100
    assert 'small' not in dropped
    assert all(c['rows'] == 10_000 for c in table['columns']), "a column keeps its other statistics"


@pytest.mark.unit
def test_payloads_split_by_size(dbm_instance):
    # Three tables of two columns each, read as the procedure returns them: ordered by table.
    rows = [procedure_row(table_name=table, column_name=column) for table in 'abc' for column in ('x', 'y')]
    cursor = iter_cursor(rows)
    collector = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata._column_statistics_collector
    # The tables are the same size apart from their names, so a budget of two and a half tables fits two.
    table_bytes = fit_table(next(read_tables(iter_cursor(rows[:2]), list(rows[0]), 'app')))

    with (
        mock.patch('datadog_checks.sqlserver.column_statistics.PAYLOAD_MAX_BYTES', table_bytes * 2.5),
        mock.patch.object(collector, '_submit') as submit,
    ):
        assert collector._collect_database(cursor, 'app') == (3, 6, 2)

    batches = [
        [(t['table'], [c['column_name'] for c in t['columns']]) for t in call.args[0]] for call in submit.call_args_list
    ]
    assert batches == [[('a', ['x', 'y']), ('b', ['x', 'y'])], [('c', ['x', 'y'])]]


@pytest.mark.unit
def test_tables_read_before_an_error_are_sent(dbm_instance):
    rows = [procedure_row(table_name=table, column_name=column) for table in 'abc' for column in ('x', 'y')]
    cursor = iter_cursor(rows)
    # The connection drops after the first of table c's rows, so c is incomplete and isn't sent.
    cursor.fetchone.side_effect = [tuple(row.values()) for row in rows[:5]] + [Exception('Communication link failure')]
    collector = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata._column_statistics_collector
    with mock.patch.object(collector, '_submit') as submit:
        assert collector._collect_database(cursor, 'app') == (2, 4, 1)
    assert [t['table'] for t in submit.call_args.args[0]] == ['a', 'b']


PROCEDURE_NOT_FOUND = SqlServerHealthEvent.COLUMN_STATISTICS_PROCEDURE_NOT_FOUND
INSUFFICIENT_PRIVILEGE = SqlServerHealthEvent.COLUMN_STATISTICS_INSUFFICIENT_PRIVILEGE


@pytest.mark.unit
@pytest.mark.parametrize(
    'message,event',
    [
        pytest.param(
            "('42000', \"[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Could not find stored "
            "procedure 'datadog.column_statistics'. (2812) (SQLExecDirectW)\")",
            PROCEDURE_NOT_FOUND,
            id='pyodbc not found',
        ),
        pytest.param(
            "('42000', \"[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]The EXECUTE permission was "
            "denied on the object 'column_statistics', database 'app', schema 'datadog'. (229) (SQLExecDirectW)\")",
            INSUFFICIENT_PRIVILEGE,
            id='pyodbc denied',
        ),
        pytest.param(
            "(-2147352567, 'Exception occurred.', (0, 'Microsoft OLE DB Driver 19 for SQL Server', \"Could not find "
            "stored procedure 'datadog.column_statistics'.\", None, 0, -2147217900), None)",
            PROCEDURE_NOT_FOUND,
            id='adodbapi not found',
        ),
        pytest.param(
            "(-2147352567, 'Exception occurred.', (0, 'Microsoft OLE DB Driver 19 for SQL Server', 'The EXECUTE "
            "permission was denied on the object \\'column_statistics\\', database \\'app\\', schema "
            "\\'datadog\\'.', None, 0, -2147217911), None)",
            INSUFFICIENT_PRIVILEGE,
            id='adodbapi denied',
        ),
    ],
)
def test_setup_errors_report_health_until_fixed(dbm_instance, message, event):
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    collector = check.sql_metadata._column_statistics_collector
    with mock.patch.object(check.health, 'submit_health_event') as submit:
        # Two databases fail; the warning is sent once, and recovery only once both are fixed.
        collector._handle_error('app', Exception(message))
        collector._handle_error('app', Exception(message))
        collector._handle_error('other', Exception(message))
        collector._handle_recovery('app')
        assert submit.call_args_list == [mock.call(name=event, status=HealthStatus.WARNING)]
        collector._handle_recovery('other')
        assert submit.call_args_list[-1] == mock.call(name=event, status=HealthStatus.OK)


@pytest.mark.unit
def test_setup_error_change_recovers_the_earlier_one(dbm_instance):
    collector = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata._column_statistics_collector
    with mock.patch.object(collector._check.health, 'submit_health_event') as submit:
        collector._handle_error('app', Exception("Could not find stored procedure 'datadog.column_statistics'. (2812)"))
        # The procedure was created, but without the GRANT.
        collector._handle_error('app', Exception("The EXECUTE permission was denied on the object (229)"))
    assert submit.call_args_list == [
        mock.call(name=PROCEDURE_NOT_FOUND, status=HealthStatus.WARNING),
        mock.call(name=PROCEDURE_NOT_FOUND, status=HealthStatus.OK),
        mock.call(name=INSUFFICIENT_PRIVILEGE, status=HealthStatus.WARNING),
    ]


@pytest.mark.unit
def test_outdated_procedure_reports_health_event(dbm_instance):
    # The shape the procedure returned before the Agent derived the statistics itself. It's outdated even in a
    # database where it returns no rows.
    cursor = mock.MagicMock()
    cursor.description = [
        (name,)
        for name in (
            'schema_name',
            'table_name',
            'column_name',
            'stats_age',
            'n_distinct',
            'null_frac',
            'avg_width',
            'most_common_freqs',
        )
    ]
    cursor.fetchone.return_value = None
    check = SQLServer(CHECK_NAME, {}, [dbm_instance])
    with mock.patch.object(check.health, 'submit_health_event') as submit:
        assert check.sql_metadata._column_statistics_collector._collect_database(cursor, 'app') == (0, 0, 0)
    submit.assert_called_once_with(
        name=SqlServerHealthEvent.COLUMN_STATISTICS_PROCEDURE_OUTDATED, status=HealthStatus.WARNING
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    'settings_interval,column_statistics_interval,elapsed,due',
    [
        # Timer jitter brought the tick slightly under an hour later.
        pytest.param(3600, 3600, 3599.5, True, id='interval equal to the period'),
        pytest.param(600, 3600, 3000, False, id='before the interval'),
        pytest.param(600, 3600, 3600, True, id='tick at the interval'),
        pytest.param(600, 900, 600, False, id='never more often than configured'),
        pytest.param(600, 900, 1200, True, id='first tick past the interval'),
    ],
)
def test_metadata_job_runs_column_statistics_each_interval(
    dbm_instance, settings_interval, column_statistics_interval, elapsed, due
):
    dbm_instance['collect_settings'] = {'enabled': True, 'collection_interval': settings_interval}
    dbm_instance['collect_column_statistics'] = {'enabled': True, 'collection_interval': column_statistics_interval}
    metadata = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata
    with mock.patch.object(metadata._column_statistics_collector, 'collect') as collect:
        metadata.collect_column_statistics(1_000_000)
        metadata.collect_column_statistics(1_000_000 + elapsed)
    assert collect.call_count == (2 if due else 1)


@pytest.mark.unit
@pytest.mark.parametrize(
    'settings,schemas,period',
    [
        pytest.param({'enabled': True}, {'enabled': False}, 600, id='settings'),
        # Column statistics alone: the job only needs to run hourly.
        pytest.param({'enabled': False}, {'enabled': False}, 3600, id='column statistics alone'),
        # Schemas keep their 10 minutes though settings are off.
        pytest.param({'enabled': False}, {'enabled': True}, 600, id='schemas'),
        # An interval of 0 runs on every run of the job rather than setting its rate.
        pytest.param({'enabled': True}, {'enabled': True, 'collection_interval': 0}, 600, id='schemas every run'),
    ],
)
def test_metadata_job_runs_as_often_as_its_most_frequent_collection(dbm_instance, settings, schemas, period):
    dbm_instance['collect_settings'] = settings
    dbm_instance['collect_schemas'] = schemas
    metadata = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata
    assert metadata._rate_limiter.period_s == period
    # A run is only reported missed after the job's period, not a shorter collection's interval.
    assert metadata._expected_collection_interval == period


@pytest.mark.unit
def test_column_statistics_failure_does_not_stop_metadata_job(dbm_instance):
    metadata = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata
    with mock.patch.object(metadata._column_statistics_collector, 'collect', side_effect=Exception('connection lost')):
        metadata.collect_column_statistics()
