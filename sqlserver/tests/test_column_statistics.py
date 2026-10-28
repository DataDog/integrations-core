# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import copy

import mock
import pytest

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.column_statistics import derive_column_statistics, group_by_table
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
    columns = {c['name']: c for c in tables[0]['columns']}
    assert set(columns) == {'id', 'customer_id', 'status', 'note', 'unused_num'}

    # One customer has 30% of the rows and the other 349 have 0.2% each. The statistics were read in full, so as in
    # Postgres, every repeated value the histogram has an exact count for is kept, up to 100.
    assert columns['customer_id']['n_distinct'] == 350
    customer_freqs = columns['customer_id']['most_common_freqs']
    assert customer_freqs[0] == pytest.approx(0.302)
    assert 1 < len(customer_freqs) <= 100
    assert customer_freqs[1:] == [pytest.approx(0.002)] * (len(customer_freqs) - 1)
    # Every value is distinct, which Postgres sends as -1, a share of the rows.
    assert columns['id']['n_distinct'] == -1
    assert columns['id']['most_common_freqs'] == []
    assert columns['status']['n_distinct'] == 2
    assert columns['status']['null_frac'] == pytest.approx(0.1)
    assert columns['status']['most_common_freqs'] == [pytest.approx(0.7), pytest.approx(0.2)]
    # Its histogram has no steps at all.
    assert columns['unused_num']['null_frac'] == 1
    assert columns['unused_num']['n_distinct'] == 0
    assert columns['unused_num']['most_common_freqs'] == []
    # 'pending' and 'shipped' are 7 bytes each. As in pg_stats, the NULLs don't pull the average down.
    assert columns['status']['avg_width'] == 7
    # nvarchar values of 20 to 40 characters average 60 bytes.
    assert columns['note']['avg_width'] == 60
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


@pytest.mark.unit
def test_group_by_table():
    def row(table, column, stats_age):
        return {
            'schema_name': 'dbo',
            'table_name': table,
            'column_name': column,
            'stats_age': stats_age,
            'n_distinct': 3.0,
            'null_frac': 0.0,
            'avg_width': 4.0,
            'most_common_freqs': [],
        }

    tables = group_by_table('db', [row('a', 'x', 10), row('a', 'y', 50), row('b', 'z', 5)])

    assert [(t['table'], [c['name'] for c in t['columns']]) for t in tables] == [('a', ['x', 'y']), ('b', ['z'])]
    assert tables[0]['stats_age'] == 50, "a table is as stale as its oldest column statistics"


def step(equal_rows, range_rows=0.0, distinct_range_rows=0.0, is_null=0):
    return {
        'is_null': is_null,
        'equal_rows': equal_rows,
        'range_rows': range_rows,
        'distinct_range_rows': distinct_range_rows,
    }


def column(rows, steps, is_nullable=True, rows_sampled=None, fixed_width=4.0, avg_width=None, is_unique=False):
    stats = {
        'schema_name': 'dbo',
        'table_name': 't',
        'column_name': 'c',
        'is_nullable': is_nullable,
        'is_unique': is_unique,
        'rows': rows,
        'rows_sampled': rows_sampled or rows,
        'stats_age': 0,
        'fixed_width': fixed_width,
        'avg_width': avg_width,
    }
    return derive_column_statistics(stats, steps)


@pytest.mark.unit
@pytest.mark.parametrize(
    'steps,is_nullable,rows_sampled,null_frac',
    [
        pytest.param([step(400), step(600, is_null=1)], True, None, 0.6, id='NULL step'),
        pytest.param([step(400, range_rows=300, distinct_range_rows=3)], True, None, 0.3, id='no NULL step'),
        pytest.param([], True, None, 1.0, id='every value NULL'),
        # Steps scaled up from a sample cover slightly fewer rows than the table has.
        pytest.param([step(399.99, range_rows=599.99, distinct_range_rows=9)], False, 20, 0.0, id='NOT NULL'),
    ],
)
def test_derive_null_frac(steps, is_nullable, rows_sampled, null_frac):
    assert column(1000, steps, is_nullable, rows_sampled)['null_frac'] == null_frac


@pytest.mark.unit
@pytest.mark.parametrize(
    'steps,n_distinct',
    [
        pytest.param([step(500, range_rows=450, distinct_range_rows=49)], 50, id='count'),
        pytest.param([step(1, range_rows=998, distinct_range_rows=998), step(1)], -1, id='unique'),
        pytest.param([step(1, range_rows=499, distinct_range_rows=499), step(500, is_null=1)], -0.5, id='share'),
        pytest.param([], 0, id='every value NULL'),
    ],
)
def test_derive_n_distinct(steps, n_distinct):
    # Like ANALYZE, more distinct values than 10% of the rows are sent as a negative share of the rows.
    assert column(1000, steps)['n_distinct'] == n_distinct


@pytest.mark.unit
@pytest.mark.parametrize(
    'steps,is_nullable,n_distinct',
    [
        # A 67% sample estimates only 930 of 1000 distinct values, and its scaled-up counts look repeated.
        pytest.param([step(1.5, range_rows=997, distinct_range_rows=928), step(1.5)], False, -1, id='sampled'),
        pytest.param(
            [step(1, range_rows=898, distinct_range_rows=898), step(1), step(100, is_null=1)], True, -0.9, id='NULLs'
        ),
    ],
)
def test_derive_unique(steps, is_nullable, n_distinct):
    # As in Postgres, every non-NULL value of a unique column is distinct, and none is common.
    stats = column(1000, steps, is_nullable, rows_sampled=670, is_unique=True)
    assert stats['n_distinct'] == pytest.approx(n_distinct)
    assert stats['most_common_freqs'] == []


@pytest.mark.unit
def test_derive_avg_width_excludes_nulls():
    # DBCC averages 3 bytes over all rows; the half that isn't NULL averages 6, as pg_stats reports.
    stats = column(1000, [step(500), step(500, is_null=1)], fixed_width=None, avg_width=3.0)
    assert stats['avg_width'] == 6


@pytest.mark.unit
@pytest.mark.parametrize(
    'steps,rows_sampled,freqs',
    [
        pytest.param([step(700), step(200), step(100)], None, [0.7, 0.2, 0.1], id='all values'),
        pytest.param([step(1), step(998, range_rows=1, distinct_range_rows=1)], None, [0.998], id='only repeated'),
        pytest.param(
            [step(300, range_rows=200, distinct_range_rows=99)] + [step(5)] * 100,
            None,
            [0.3] + [0.005] * 99,
            id='read in full',
        ),
        # The sample has 10 or 11 rows of each of 100 values: their differences are noise.
        pytest.param(
            [step(10_000 + 1_000 * (i % 2), range_rows=9_000, distinct_range_rows=1) for i in range(50)],
            0.01,
            [],
            id='sampled uniform',
        ),
        pytest.param(
            [step(300_000)] + [step(7_000, range_rows=7_000, distinct_range_rows=1) for _ in range(50)],
            0.01,
            [0.3],
            id='sampled skewed',
        ),
    ],
)
def test_derive_most_common_freqs(steps, rows_sampled, freqs):
    rows = sum(s['equal_rows'] + s['range_rows'] for s in steps)
    sampled = rows * rows_sampled if rows_sampled else None
    assert column(rows, steps, rows_sampled=sampled)['most_common_freqs'] == [pytest.approx(f) for f in freqs]


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
    'period,elapsed,due',
    [
        # The work before column statistics ran faster this tick, so the tick came slightly under an hour later.
        pytest.param(3600, 3599.5, True, id='interval equal to the period'),
        pytest.param(600, 3000, False, id='before the interval'),
        pytest.param(600, 3599.5, True, id='tick nearest the interval'),
    ],
)
def test_metadata_job_runs_column_statistics_each_interval(dbm_instance, period, elapsed, due):
    dbm_instance['collect_settings'] = {'enabled': True, 'collection_interval': period}
    metadata = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata
    with mock.patch.object(metadata._column_statistics_collector, 'collect') as collect:
        with mock.patch('datadog_checks.sqlserver.metadata.time.time', return_value=1_000_000):
            metadata.collect_column_statistics()
        with mock.patch('datadog_checks.sqlserver.metadata.time.time', return_value=1_000_000 + elapsed):
            metadata.collect_column_statistics()
    assert collect.call_count == (2 if due else 1)


@pytest.mark.unit
def test_column_statistics_failure_does_not_stop_metadata_job(dbm_instance):
    metadata = SQLServer(CHECK_NAME, {}, [dbm_instance]).sql_metadata
    with mock.patch.object(metadata._column_statistics_collector, 'collect', side_effect=Exception('connection lost')):
        metadata.collect_column_statistics()
