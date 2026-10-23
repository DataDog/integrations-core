# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.column_statistics import group_by_table

from .common import CHECK_NAME


@pytest.fixture
def dbm_instance(instance_docker):
    instance_docker['dbm'] = True
    instance_docker['min_collection_interval'] = 1
    instance_docker['query_metrics'] = {'enabled': False}
    instance_docker['query_activity'] = {'enabled': False}
    instance_docker['procedure_metrics'] = {'enabled': False}
    instance_docker['collect_settings'] = {'enabled': True, 'run_sync': True, 'collection_interval': 0.1}
    instance_docker['collect_column_statistics'] = {'enabled': True}
    return instance_docker


def run_check(dd_run_check, instance):
    check = SQLServer(CHECK_NAME, {}, [instance])
    try:
        dd_run_check(check)
    finally:
        check.cancel()


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
    assert event['collection_interval'] == 3600

    tables = event['column_statistics']
    assert [(t['db'], t['schema'], t['table']) for t in tables] == [('datadog_test_column_stats', 'dbo', 'orders')]
    columns = {c['name']: c for c in tables[0]['columns']}
    assert set(columns) == {'id', 'customer_id', 'status', 'note'}

    # One customer has 30% of the rows; the other 349 share the rest, each below the average count per value.
    assert columns['customer_id']['n_distinct'] == 350
    assert columns['customer_id']['most_common_freqs'] == [pytest.approx(0.302)]
    assert columns['id']['n_distinct'] == 10_000
    assert columns['id']['most_common_freqs'] == []
    # 'pending' (20%) is under the average for the non-NULL rows, so only 'shipped' (70%) counts as common.
    assert columns['status']['n_distinct'] == 2
    assert columns['status']['null_frac'] == pytest.approx(0.1)
    assert columns['status']['most_common_freqs'] == [pytest.approx(0.7)]
    # nvarchar values of 20 to 40 characters average 60 bytes.
    assert columns['note']['avg_width'] == 60


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
    def row(table, column, stats_age, freqs):
        return {
            'schema_name': 'dbo',
            'table_name': table,
            'column_name': column,
            'stats_age': stats_age,
            'n_distinct': 3.0,
            'null_frac': 0.0,
            'avg_width': 6.3,
            'most_common_freqs': freqs,
        }

    tables = group_by_table(
        'db', [row('a', 'x', 10, '7.0e-001,2.0e-001'), row('a', 'y', 50, None), row('b', 'z', 5, None)]
    )

    assert [t['table'] for t in tables] == ['a', 'b']
    assert tables[0]['stats_age'] == 50, "a table is as stale as its oldest column statistics"
    assert tables[0]['columns'][0]['most_common_freqs'] == [0.7, 0.2]
    assert tables[0]['columns'][1]['most_common_freqs'] == []
    assert tables[0]['columns'][0]['avg_width'] == 6
