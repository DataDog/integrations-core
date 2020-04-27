# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import psycopg2
import pytest

from .common import DB_NAME, HOST, PORT

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
        {'relation_regex': '.*', 'schemas': ['hello', 'hello2']},
        # Empty schemas means all schemas, even though the first relation matches first.
        {'relation_regex': r'[pP]ersons[-_]?(dup\d)?'},
    ]
    relations = ['persons', 'personsdup1', 'Personsdup2']
    posgres_check = integration_check(pg_instance)
    posgres_check.check(pg_instance)

    expected_tags = {}
    expected_size_tags = {}
    for relation in relations:
        expected_tags[relation] = pg_instance['tags'] + [
            'server:{}'.format(pg_instance['host']),
            'port:{}'.format(pg_instance['port']),
            'db:%s' % pg_instance['dbname'],
            'table:{}'.format(relation.lower()),
            'schema:public',
        ]
        expected_size_tags[relation] = pg_instance['tags'] + [
            'server:{}'.format(pg_instance['host']),
            'port:{}'.format(pg_instance['port']),
            'db:%s' % pg_instance['dbname'],
            'table:{}'.format(relation.lower()),
            'schema:public',
        ]

    for relation in relations:
        for name in RELATION_METRICS:
            aggregator.assert_metric(name, count=1, tags=expected_tags[relation])

        # 'persons' db don't have any indexes
        for name in RELATION_INDEX_METRICS:
            aggregator.assert_metric(name, count=0, tags=expected_tags[relation])

        for name in RELATION_SIZE_METRICS:
            aggregator.assert_metric(name, count=1, tags=expected_size_tags[relation])


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


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_locks_metrics(aggregator, integration_check, pg_instance):
    pg_instance['relations'] = ['persons']
    pg_instance['query_timeout'] = 1000  # One of the relation queries waits for the table to not be locked

    check = integration_check(pg_instance)
    with psycopg2.connect(host=HOST, dbname=DB_NAME, user="postgres", password="datad0g") as conn:
        with conn.cursor() as cur:
            cur.execute('LOCK persons')
            check.check(pg_instance)

    expected_tags = pg_instance['tags'] + [
        'server:{}'.format(HOST),
        'port:{}'.format(PORT),
        'db:datadog_test',
        'lock_mode:AccessExclusiveLock',
        'lock_type:relation',
        'table:persons',
        'schema:public',
    ]

    aggregator.assert_metric('postgresql.locks', count=1, tags=expected_tags)
