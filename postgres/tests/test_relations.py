# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import psycopg2
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.postgres.relationsmanager import (
    IDX_METRICS,
    REL_METRICS,
    SIZE_METRICS,
    STATIO_METRICS,
    RelationsManager,
)

from .common import DB_NAME, HOST, PORT

INDEX_FROM_REL_METRICS = ['postgresql.index_rel_scans', 'postgresql.index_rel_rows_fetched']
INDEX_FROM_STATIO_METRICS = ['postgresql.index_blocks_read', 'postgresql.index_blocks_hit']


def _get_metric_names(scope):
    for metric_name, _ in scope['metrics'].values():
        yield metric_name


def _get_oid_of_relation(relation):
    oid = 0
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute("select oid from pg_class where relname='{}'".format(relation))
            oid = cur.fetchall()[0][0]
    return oid


def _check_relation_metrics(aggregator, pg_instance, relation):
    relation = relation.lower()
    base_tags = pg_instance['tags'] + ['port:{}'.format(pg_instance['port']), 'db:%s' % pg_instance['dbname']]
    expected_tags = base_tags + [
        'table:{}'.format(relation),
        'schema:public',
    ]

    oid = _get_oid_of_relation(relation)
    expected_toast_tags = base_tags + [
        'toast_of:{}'.format(relation),
        'table:pg_toast_{}'.format(oid),
        'schema:pg_toast',
    ]
    expected_toast_index_tags = base_tags + [
        'toast_of:{}'.format(relation),
        'table:pg_toast_{}'.format(oid),
        'index:pg_toast_{}_index'.format(oid),
        'schema:pg_toast',
    ]

    for name in _get_metric_names(REL_METRICS):
        if name in INDEX_FROM_REL_METRICS:
            aggregator.assert_metric(name, count=0, tags=expected_tags)
        else:
            aggregator.assert_metric(name, count=1, tags=expected_tags)
        aggregator.assert_metric(name, count=1, tags=expected_toast_tags)

    for name in _get_metric_names(STATIO_METRICS):
        if name in INDEX_FROM_STATIO_METRICS:
            aggregator.assert_metric(name, count=0, tags=expected_tags)
        else:
            aggregator.assert_metric(name, count=1, tags=expected_tags)
        # statio table already provides toast specific metrics
        aggregator.assert_metric(name, count=0, tags=expected_toast_tags)

    for name in _get_metric_names(IDX_METRICS):
        # 'persons' db don't have any indexes
        aggregator.assert_metric(name, count=0, tags=expected_tags)
        # toast table are always indexed
        aggregator.assert_metric(name, count=1, tags=expected_toast_index_tags)

    for name in _get_metric_names(SIZE_METRICS):
        aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['persons']
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)
    _check_relation_metrics(aggregator, pg_instance, 'persons')


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

    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    base_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'db:%s' % pg_instance['dbname'],
        'table:pg_index',
        'schema:pg_catalog',
    ]

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
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    for relation in relations:
        _check_relation_metrics(aggregator, pg_instance, relation)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_toast_relation_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['test_toast']
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    oid = _get_oid_of_relation('test_toast')
    expected_toast_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'db:%s' % pg_instance['dbname'],
        'toast_of:test_toast',
        'table:pg_toast_{}'.format(oid),
        'schema:pg_toast',
    ]
    expected_toast_index_tags = expected_toast_tags + [
        'index:pg_toast_{}_index'.format(oid),
    ]
    # 5000 iterations * 32 bytes / 1996 bytes per page = 80.16032064128257
    aggregator.assert_metric('postgresql.seq_scans', count=1, value=1, tags=expected_toast_tags)
    aggregator.assert_metric('postgresql.index_rel_scans', count=1, value=3, tags=expected_toast_tags)
    aggregator.assert_metric('postgresql.live_rows', count=1, value=81, tags=expected_toast_tags)
    aggregator.assert_metric('postgresql.rows_inserted', count=1, value=81, tags=expected_toast_tags)
    aggregator.assert_metric('postgresql.index_rel_rows_fetched', count=1, value=81 * 2, tags=expected_toast_tags)

    aggregator.assert_metric('postgresql.index_rows_read', count=1, value=81 * 2, tags=expected_toast_index_tags)
    aggregator.assert_metric('postgresql.index_rows_fetched', count=1, value=81 * 2, tags=expected_toast_index_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_max_relations(aggregator, integration_check, pg_instance):
    pg_instance.update({'relations': [{'relation_regex': '.*'}], 'max_relations': 1})
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    for name in _get_metric_names(REL_METRICS):
        relation_metrics = []
        for m in aggregator._metrics[name]:
            if any(['table:' in tag for tag in m.tags]):
                relation_metrics.append(m)
        if name in INDEX_FROM_REL_METRICS:
            assert len(relation_metrics) == 1
        else:
            assert len(relation_metrics) == 2

    for name in _get_metric_names(SIZE_METRICS):
        relation_metrics = []
        for m in aggregator._metrics[name]:
            if any(['table:' in tag for tag in m.tags]):
                relation_metrics.append(m)
        assert len(relation_metrics) == 1


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_index_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['breed']
    pg_instance['dbname'] = 'dogs'

    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'port:{}'.format(pg_instance['port']),
        'db:dogs',
        'table:breed',
        'index:breed_names',
        'schema:public',
    ]

    for name in _get_metric_names(IDX_METRICS):
        aggregator.assert_metric(name, count=1, tags=expected_tags)


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
                'port:{}'.format(PORT),
                'db:datadog_test',
                'lock_mode:AccessExclusiveLock',
                'lock_type:relation',
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
        expected_tags = pg_instance['tags'] + tags
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
