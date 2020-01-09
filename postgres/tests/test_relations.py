# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

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
]

RELATION_SIZE_METRICS = ['postgresql.table_size', 'postgresql.total_size', 'postgresql.index_size']

RELATION_INDEX_METRICS = [
    'postgresql.index_scans',
    'postgresql.index_rows_fetched',  # deprecated
    'postgresql.index_rel_rows_fetched',
    'postgresql.index_blocks_read',
    'postgresql.index_blocks_hit',
]

IDX_METRICS = ['postgresql.index_scans', 'postgresql.index_rows_read', 'postgresql.index_rows_fetched']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['persons']

    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'server:{}'.format(pg_instance['host']),
        'port:{}'.format(pg_instance['port']),
        'db:%s' % pg_instance['dbname'],
        'table:persons',
        'schema:public',
    ]

    expected_size_tags = pg_instance['tags'] + [
        'server:{}'.format(pg_instance['host']),
        'port:{}'.format(pg_instance['port']),
        'db:%s' % pg_instance['dbname'],
        'table:persons',
        'schema:public',
    ]

    for name in RELATION_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)

    # 'persons' db don't have any indexes
    for name in RELATION_INDEX_METRICS:
        aggregator.assert_metric(name, count=0, tags=expected_tags)

    for name in RELATION_SIZE_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_size_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_relations_metrics2(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = [
        {'relation_regex': r'.*', 'schemas': ['doghouse']},
        # Empty schemas means all schemas, even though the first relation matches first.
        {'relation_regex': r'[pP]ersons[-_]?(dup\d)?'},
    ]
    relations = ['persons', 'personsdup1', 'Personsdup2', 'doghouse.dog']
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    for relation in relations:
        schema, _, table = relation.lower().rpartition('.')
        if not schema:
            schema = 'public'

        expected_tags = pg_instance['tags'] + [
            'server:{}'.format(pg_instance['host']),
            'port:{}'.format(pg_instance['port']),
            'db:%s' % pg_instance['dbname'],
            'table:{}'.format(table),
            'schema:{}'.format(schema),
        ]

        for name in RELATION_METRICS:
            aggregator.assert_metric(name, count=1, tags=expected_tags)

        # None of the tables have indexes.
        for name in RELATION_INDEX_METRICS:
            aggregator.assert_metric(name, count=0, tags=expected_tags)

        for name in RELATION_SIZE_METRICS:
            aggregator.assert_metric(name, count=1, tags=expected_tags)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_index_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['breed']
    pg_instance['dbname'] = 'dogs'

    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'server:{}'.format(pg_instance['host']),
        'port:{}'.format(pg_instance['port']),
        'db:dogs',
        'table:breed',
        'index:breed_names',
        'schema:public',
    ]

    for name in IDX_METRICS:
        aggregator.assert_metric(name, count=1, tags=expected_tags)
