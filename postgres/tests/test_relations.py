# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import psycopg2
import pytest
from flaky import flaky

from datadog_checks.base import ConfigurationError
from datadog_checks.postgres.relationsmanager import QUERY_PG_CLASS, RelationsManager

from .common import DB_NAME, HOST, _get_expected_tags, _iterate_metric_name, assert_metric_at_least
from .utils import _get_superconn, _wait_for_value, requires_over_11

RELATION_METRICS = [
    'postgresql.seq_scans',
    'postgresql.seq_rows_read',
    'postgresql.rows_inserted',
    'postgresql.rows_updated',
    'postgresql.rows_deleted',
    'postgresql.rows_hot_updated',
    'postgresql.live_rows',
    'postgresql.dead_rows',
    'postgresql.heap_blocks_read',
    'postgresql.heap_blocks_hit',
    'postgresql.toast_blocks_read',
    'postgresql.toast_blocks_hit',
    'postgresql.toast_index_blocks_read',
    'postgresql.toast_index_blocks_hit',
    'postgresql.vacuumed',
    'postgresql.autovacuumed',
    'postgresql.analyzed',
    'postgresql.autoanalyzed',
]

RELATION_INDEX_METRICS = [
    'postgresql.index_scans',
    'postgresql.index_rows_fetched',  # deprecated
    'postgresql.index_rel_rows_fetched',
    'postgresql.index_blocks_read',
    'postgresql.index_blocks_hit',
    'postgresql.individual_index_size',
]

IDX_METRICS = ['postgresql.index_scans', 'postgresql.index_rows_read', 'postgresql.index_rows_fetched']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['persons']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db=pg_instance['dbname'], table='persons', schema='public')

    for name in RELATION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
    # 'persons' db don't have any indexes
    for name in RELATION_INDEX_METRICS:
        aggregator.assert_metric(name, count=0, tags=expected_tags)
    for name in _iterate_metric_name(QUERY_PG_CLASS):
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics_access_exclusive_lock(aggregator, integration_check, pg_instance):
    '''
    This test is an edge case where we want to make sure that relations metrics query does
    not timeout when a relation is locked with an AccessExclusiveLock.
    To do so, we lock the `persons` table with an AccessExclusiveLock and then run the check.
    '''
    pg_instance['relations'] = ['persons']
    check = integration_check(pg_instance)

    conn = _get_superconn(pg_instance)
    cursor = conn.cursor()
    # Lock the persons table with an AccessExclusiveLock
    cursor.execute('BEGIN')  # must be in a transaction to lock a table
    cursor.execute('LOCK persons IN ACCESS EXCLUSIVE MODE')

    # verify that the lock is in place
    cursor.execute(
        '''
        SELECT mode, locktype, granted FROM pg_locks
        WHERE relation = (SELECT oid FROM pg_class WHERE relname = 'persons')
        '''
    )
    row = cursor.fetchone()
    assert row is not None
    assert row == ('AccessExclusiveLock', 'relation', True)

    check.check(pg_instance)
    expected_tags = _get_expected_tags(check, pg_instance, db=pg_instance['dbname'], table='persons', schema='public')

    for name in _iterate_metric_name(QUERY_PG_CLASS):
        # Expect no relation metrics to be collected for persons table
        # because locked relations are skipped in the query
        aggregator.assert_metric(name, count=0, tags=expected_tags)

    # Release the lock
    cursor.execute('COMMIT')
    cursor.close()
    conn.close()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@requires_over_11
def test_partition_relation(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = [
        {'relation_regex': 'test_.*'},
    ]

    check = integration_check(pg_instance)
    check.check(pg_instance)

    part_1_tags = _get_expected_tags(
        check, pg_instance, db=pg_instance['dbname'], table='test_part1', partition_of='test_part', schema='public'
    )
    aggregator.assert_metric('postgresql.relation.pages', value=3, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.relation.tuples', value=499, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.relation.all_visible', value=3, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.table_size', value=24576, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.relation_size', value=24576, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.index_size', value=65536, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.toast_size', value=0, count=1, tags=part_1_tags)
    aggregator.assert_metric('postgresql.total_size', value=90112, count=1, tags=part_1_tags)

    part_2_tags = _get_expected_tags(
        check, pg_instance, db=pg_instance['dbname'], table='test_part2', partition_of='test_part', schema='public'
    )
    aggregator.assert_metric('postgresql.relation.pages', value=8, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.relation.tuples', value=1502, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.relation.all_visible', value=8, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.table_size', value=73728, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.relation_size', value=65536, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.index_size', value=98304, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.toast_size', value=8192, count=1, tags=part_2_tags)
    aggregator.assert_metric('postgresql.total_size', value=172032, count=1, tags=part_2_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'collect_bloat_metrics, expected_count',
    [
        pytest.param(True, 1, id='bloat enabled'),
        pytest.param(False, 0, id='bloat disabled'),
    ],
)
def test_bloat_metrics(aggregator, collect_bloat_metrics, expected_count, integration_check, pg_instance):
    pg_instance['relations'] = ['pg_index']
    pg_instance['collect_bloat_metrics'] = collect_bloat_metrics

    check = integration_check(pg_instance)
    check.check(pg_instance)

    base_tags = _get_expected_tags(check, pg_instance, db=pg_instance['dbname'], table='pg_index', schema='pg_catalog')
    aggregator.assert_metric('postgresql.table_bloat', count=expected_count, tags=base_tags)

    indices = ['pg_index_indrelid_index', 'pg_index_indexrelid_index']
    for index in indices:
        expected_tags = base_tags + ['index:{}'.format(index)]
        aggregator.assert_metric('postgresql.index_bloat', count=expected_count, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics_regex(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = [
        {'relation_regex': '.*', 'schemas': ['hello', 'hello2']},
        # Empty schemas means all schemas, even though the first relation matches first.
        {'relation_regex': r'[pP]ersons[-_]?(dup\d)?'},
    ]
    relations = ['persons', 'personsdup1', 'Personsdup2']
    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = {}
    for relation in relations:
        expected_tags[relation] = _get_expected_tags(
            check, pg_instance, db=pg_instance['dbname'], table=relation.lower(), schema='public'
        )

    for relation in relations:
        for name in RELATION_METRICS:
            aggregator.assert_metric(name, count=1, tags=expected_tags[relation])

        # 'persons' db don't have any indexes
        for name in RELATION_INDEX_METRICS:
            aggregator.assert_metric(name, count=0, tags=expected_tags[relation])

    for name in _iterate_metric_name(QUERY_PG_CLASS):
        aggregator.assert_metric(name, count=1, tags=expected_tags[relation])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_max_relations(aggregator, integration_check, pg_instance):
    pg_instance.update({'relations': [{'relation_regex': '.*'}], 'max_relations': 1})
    check = integration_check(pg_instance)
    check.check(pg_instance)

    for name in RELATION_METRICS:
        relation_metrics = []
        for m in aggregator._metrics[name]:
            if any('table:' in tag for tag in m.tags):
                relation_metrics.append(m)
        assert len(relation_metrics) == 1

    for name in _iterate_metric_name(QUERY_PG_CLASS):
        relation_metrics = []
        for m in aggregator._metrics[name]:
            if any('table:' in tag for tag in m.tags):
                relation_metrics.append(m)
        assert len(relation_metrics) == 1


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_index_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['breed']
    pg_instance['dbname'] = 'dogs'

    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(
        check, pg_instance, db='dogs', table='breed', index='breed_names', schema='public'
    )
    for name in IDX_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@flaky(max_runs=5)
def test_vacuum_age(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['persons']
    pg_instance['dbname'] = 'datadog_test'

    conn = _get_superconn(pg_instance)
    with conn.cursor() as cur:
        cur.execute('select pg_stat_reset()')
        cur.execute('VACUUM ANALYZE persons')
    conn.close()

    _wait_for_value(
        pg_instance,
        lower_threshold=0,
        query="select count(*) from pg_stat_user_tables where relname='persons' and vacuum_count > 0;",
    )

    check = integration_check(pg_instance)
    check.check(pg_instance)

    expected_tags = _get_expected_tags(check, pg_instance, db='datadog_test', table='persons', schema='public')
    for name in ['postgresql.last_vacuum_age', 'postgresql.last_analyze_age']:
        assert_metric_at_least(
            aggregator,
            name,
            lower_bound=0,
            higher_bound=100,
            tags=expected_tags,
            count=1,
        )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'relations, lock_count, lock_table_name, tags',
    [
        pytest.param(
            ['persons'],
            1,
            'persons',
            [
                'db:datadog_test',
                'lock_mode:AccessExclusiveLock',
                'lock_type:relation',
                'granted:True',
                'fastpath:False',
                'table:persons',
                'schema:public',
            ],
            id="test with single table lock should return 1",
        ),
        pytest.param(
            [{'relation_regex': 'perso.*', 'relkind': ['r']}],
            1,
            'persons',
            None,
            id="test with matching relkind should return 1",
        ),
        pytest.param(
            [{'relation_regex': 'perso.*', 'relkind': ['i']}],
            0,
            'persons',
            None,
            id="test without matching relkind should return 0",
        ),
        pytest.param(
            ['pgtable'],
            1,
            'pgtable',
            None,
            id="pgtable should be included in lock metrics",
        ),
        pytest.param(
            ['pg_newtable'],
            0,
            'pg_newtable',
            None,
            id="pg_newtable should be excluded from query since it starts with `pg_`",
        ),
    ],
)
def test_locks_metrics(aggregator, integration_check, pg_instance, relations, lock_count, lock_table_name, tags):
    pg_instance['relations'] = relations
    pg_instance['query_timeout'] = 1000  # One of the relation queries waits for the table to not be locked

    check = integration_check(pg_instance)
    check_with_lock(check, pg_instance, lock_table_name)

    if tags is not None:
        expected_tags = _get_expected_tags(check, pg_instance) + tags
        aggregator.assert_metric('postgresql.locks', count=lock_count, tags=expected_tags)
    else:
        aggregator.assert_metric('postgresql.locks', count=lock_count)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def check_with_lock(check, instance, lock_table=None):
    lock_statement = 'LOCK persons'
    if lock_table is not None:
        lock_statement = 'LOCK {}'.format(lock_table)
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute(lock_statement)
            check.check(instance)


@pytest.mark.unit
def test_relations_validation_accepts_list_of_str_and_dict():
    RelationsManager.validate_relations_config(
        [
            'alert_cycle_keys_aggregate',
            'api_keys',
            {'relation_regex': 'perso.*', 'relkind': ['i']},
            {'relation_name': 'person', 'relkind': ['i']},
            {'relation_name': 'person', 'schemas': ['foo']},
        ]
    )


@pytest.mark.unit
def test_relations_validation_fails_if_no_relname_or_regex():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{'relkind': ['i']}])


@pytest.mark.unit
def test_relations_validation_fails_if_schemas_is_wrong_type():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{'relation_name': 'person', 'schemas': 'foo'}])


@pytest.mark.unit
def test_relations_validation_fails_if_relkind_is_wrong_type():
    with pytest.raises(ConfigurationError):
        RelationsManager.validate_relations_config([{'relation_name': 'person', 'relkind': 'foo'}])
