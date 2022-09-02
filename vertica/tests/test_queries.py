# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from datadog_checks.vertica.queries import QueryBuilder
from datadog_checks.vertica.vertica import VerticaClient

from . import common
from .db import BASE_DB_OPTIONS


@pytest.mark.parametrize(
    'version, expected_per_projection_query',
    [
        (
            9,
            (
                'SELECT '
                'anchor_table_name, '
                'node_name, '
                'projection_name, '
                'sum(ros_count) as ros_count, '
                'sum(row_count) as row_count, '
                'sum(used_bytes) as used_bytes, '
                'sum(ros_row_count) as ros_row_count, '
                'sum(wos_row_count) as wos_row_count, '
                'sum(ros_used_bytes) as ros_used_bytes, '
                'sum(wos_used_bytes) as wos_used_bytes '
                'FROM v_monitor.projection_storage GROUP BY anchor_table_name, node_name, projection_name'
            ),
        ),
        (
            11,
            (
                'SELECT '
                'anchor_table_name, '
                'node_name, '
                'projection_name, '
                'sum(ros_count) as ros_count, '
                'sum(row_count) as row_count, '
                'sum(used_bytes) as used_bytes '
                'FROM v_monitor.projection_storage GROUP BY anchor_table_name, node_name, projection_name'
            ),
        ),
    ],
)
def test_build_projection_storage_queries(version, expected_per_projection_query):
    queries = QueryBuilder(version).build_projection_storage_queries()

    assert len(queries) == 4

    assert queries[0]['name'] == 'projection_storage_per_projection'
    assert queries[0]['query'] == expected_per_projection_query
    assert queries[0]['columns'][0] == {'name': 'table_name', 'type': 'tag'}
    assert queries[0]['columns'][3] == {'name': 'projection.ros.containers', 'type': 'gauge'}


@pytest.mark.parametrize(
    'version, expected_per_projection_query',
    [
        (
            9,
            (
                'SELECT '
                'node_name, '
                'projection_name, '
                'storage_type, '
                'sum(delete_vector_count) '
                'FROM v_monitor.storage_containers '
                'GROUP BY node_name, projection_name, storage_type'
            ),
        ),
        (
            11,
            (
                'SELECT '
                'node_name, '
                'projection_name, '
                'sum(delete_vector_count) '
                'FROM v_monitor.storage_containers '
                'GROUP BY node_name, projection_name'
            ),
        ),
    ],
)
def test_build_storage_containers_queries(version, expected_per_projection_query):
    queries = QueryBuilder(version).build_storage_containers_queries()

    assert len(queries) == 3

    assert queries[0]['name'] == 'storage_containers_per_projection'
    assert queries[0]['query'] == expected_per_projection_query
    assert queries[0]['columns'][-1] == {'name': 'projection.delete_vectors', 'type': 'gauge'}


@pytest.fixture
def client():
    client = VerticaClient(BASE_DB_OPTIONS)
    with client.connect():
        yield client


@pytest.fixture
def builder():
    yield QueryBuilder(
        common.VERTICA_MAJOR_VERSION,
        catalog_schema='fake_v_catalog',
        monitor_schema='fake_v_monitor',
    )


def one_day_from_now():
    return datetime.utcnow() + timedelta(days=1)


def one_day_ago():
    return datetime.utcnow() - timedelta(days=1)


def approx_a_day_in_seconds(t, margin=60):
    return 86400 - margin <= t <= 86400 + margin


@pytest.mark.usefixtures('dd_environment')
def test_licenses_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_catalog',
        table_name='licenses',
        schema=[('LICENSETYPE', 'VARCHAR'), ('END_DATE', 'VARCHAR')],
        data='\n'.join(
            [
                'Community Edition,Perpetual',
                'Premium Edition,',
                'Superpremium Edition,{}'.format(one_day_from_now()),
            ]
        ),
    )

    query = builder.build_licenses_queries()[0]['query']

    results = list(client.query(query))

    assert results[0] == ['Community Edition', -1]
    assert results[1] == ['Premium Edition', -1]
    assert approx_a_day_in_seconds(results[2][1])


@pytest.mark.usefixtures('dd_environment')
def test_license_audits_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_catalog',
        table_name='license_audits',
        schema=[
            ('DATABASE_SIZE_BYTES', 'INTEGER'),
            ('LICENSE_SIZE_BYTES', 'INTEGER'),
            ('AUDIT_START_TIMESTAMP', 'TIMESTAMPTZ'),
            ('AUDITED_DATA', 'VARCHAR'),
        ],
        data='\n'.join(
            [
                '500,500,,Total',
                '200,300,{},Total'.format(one_day_ago() - timedelta(days=1)),
                '100,1000,{},Total'.format(one_day_ago()),
                '100,200,{},External'.format(one_day_ago() - timedelta(days=2)),
            ]
        ),
    )

    query = builder.build_license_audits_queries()[0]['query']

    results = list(client.query(query))

    assert len(results) == 1
    assert approx_a_day_in_seconds(results[0][0])
    assert results[0][1:] == [1000, 100, 900, 10]


@pytest.mark.usefixtures('dd_environment')
def test_system_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='system',
        schema=[
            ('CURRENT_EPOCH', 'INTEGER'),
            ('AHM_EPOCH', 'INTEGER'),
            ('LAST_GOOD_EPOCH', 'INTEGER'),
            ('DESIGNED_FAULT_TOLERANCE', 'INTEGER'),
            ('NODE_COUNT', 'INTEGER'),
            ('NODE_DOWN_COUNT', 'INTEGER'),
            ('CURRENT_FAULT_TOLERANCE', 'INTEGER'),
        ],
        data='30,20,10,2,40,5,1',
    )

    # The system query uses some data from the `licenses` table
    setup_db_tables(
        schema_name='fake_v_catalog_1',
        table_name='licenses',
        schema=[('NODE_RESTRICTION', 'VARCHAR')],
        data='100\n',
    )

    builder.catalog_schema = 'fake_v_catalog_1'
    query = builder.build_system_queries()[0]['query']

    results = list(client.query(query))

    assert results == [[40, 5, 1, 2, 20, 30, 10, 100, 60]]

    # When allowed_nodes is NULL
    setup_db_tables(
        schema_name='fake_v_catalog_2',
        table_name='licenses',
        schema=[('NODE_RESTRICTION', 'VARCHAR')],
        data=',\n',
    )

    builder.catalog_schema = 'fake_v_catalog_2'
    query = builder.build_system_queries()[0]['query']

    results = list(client.query(query))

    assert results == [[40, 5, 1, 2, 20, 30, 10, None, None]]


@pytest.mark.usefixtures('dd_environment')
def test_projections_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_catalog',
        table_name='projections',
        schema=[
            ('IS_UP_TO_DATE', 'BOOLEAN'),
            ('IS_SEGMENTED', 'BOOLEAN'),
        ],
        data='\n'.join(
            [
                'false,false',
                'false,true',
                'false,true',
                'true,true',
                'true,false',
            ]
        ),
    )

    query = builder.build_projections_queries()[0]['query']

    results = list(client.query(query))

    assert results == [[5, 2, 3, 40, 60]]


@pytest.mark.usefixtures('dd_environment')
def test_projections_query_handles_zeros(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_catalog',
        table_name='projections',
        schema=[
            ('IS_UP_TO_DATE', 'BOOLEAN'),
            ('IS_SEGMENTED', 'BOOLEAN'),
        ],
        data='',
    )

    query = builder.build_projections_queries()[0]['query']

    results = list(client.query(query))

    assert results == [[0, 0, 0, 0, 0]]


@pytest.mark.skipif(common.VERTICA_MAJOR_VERSION >= 11, reason='Requires Vertica < 11')
@pytest.mark.usefixtures('dd_environment')
def test_projection_storage_queries_pre_11(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='projection_storage',
        schema=[
            ('NODE_NAME', 'VARCHAR'),
            ('PROJECTION_NAME', 'VARCHAR'),
            ('ROW_COUNT', 'INTEGER'),
            ('USED_BYTES', 'INTEGER'),
            ('WOS_ROW_COUNT', 'INTEGER'),
            ('WOS_USED_BYTES', 'INTEGER'),
            ('ROS_ROW_COUNT', 'INTEGER'),
            ('ROS_USED_BYTES', 'INTEGER'),
            ('ROS_COUNT', 'INTEGER'),
            ('ANCHOR_TABLE_NAME', 'VARCHAR'),
        ],
        data='\n'.join(
            [
                'node_a,proj_a,3,10,1,4,2,6,20,table_a',
                'node_a,proj_a,30,100,10,40,20,60,200,table_a',
                'node_a,proj_b,4,11,2,5,2,6,21,table_a',
                'node_a,proj_c,5,12,2,6,3,6,30,table_b',
                'node_b,proj_d,6,13,3,4,3,9,40,table_c',
            ]
        ),
    )

    queries = [q['query'] for q in builder.build_projection_storage_queries()]

    results = [list(client.query(query)) for query in queries]

    per_projection, per_table, per_node, total = results

    assert sorted(per_projection) == sorted(
        [
            ['table_a', 'node_a', 'proj_a', 220, 33, 110, 22, 11, 66, 44],
            ['table_a', 'node_a', 'proj_b', 21, 4, 11, 2, 2, 6, 5],
            ['table_b', 'node_a', 'proj_c', 30, 5, 12, 3, 2, 6, 6],
            ['table_c', 'node_b', 'proj_d', 40, 6, 13, 3, 3, 9, 4],
        ]
    )
    assert sorted(per_table) == sorted(
        [
            ['table_a', 'node_a', 241, 37, 121, 24, 13, 72, 49],
            ['table_b', 'node_a', 30, 5, 12, 3, 2, 6, 6],
            ['table_c', 'node_b', 40, 6, 13, 3, 3, 9, 4],
        ]
    )
    assert sorted(per_node) == sorted(
        [
            ['node_a', 271, 42, 133, 27, 15, 78, 55],
            ['node_b', 40, 6, 13, 3, 3, 9, 4],
        ]
    )
    assert total == [[311, 48, 146, 30, 18, 87, 59]]


@pytest.mark.skipif(common.VERTICA_MAJOR_VERSION < 11, reason='Requires Vertica >= 11')
@pytest.mark.usefixtures('dd_environment')
def test_projection_storage_queries_11_plus(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='projection_storage',
        schema=[
            ('NODE_NAME', 'VARCHAR'),
            ('PROJECTION_NAME', 'VARCHAR'),
            ('ROW_COUNT', 'INTEGER'),
            ('USED_BYTES', 'INTEGER'),
            ('ROS_COUNT', 'INTEGER'),
            ('ANCHOR_TABLE_NAME', 'VARCHAR'),
        ],
        data='\n'.join(
            [
                'node_a,proj_a,3,10,20,table_a',
                'node_a,proj_a,30,100,200,table_a',
                'node_a,proj_b,4,11,21,table_a',
                'node_a,proj_c,5,12,30,table_b',
                'node_b,proj_d,6,13,40,table_c',
            ]
        ),
    )

    queries = [q['query'] for q in builder.build_projection_storage_queries()]

    results = [list(client.query(query)) for query in queries]

    per_projection, per_table, per_node, total = results

    assert sorted(per_projection) == sorted(
        [
            ['table_a', 'node_a', 'proj_a', 220, 33, 110],
            ['table_a', 'node_a', 'proj_b', 21, 4, 11],
            ['table_b', 'node_a', 'proj_c', 30, 5, 12],
            ['table_c', 'node_b', 'proj_d', 40, 6, 13],
        ]
    )
    assert sorted(per_table) == sorted(
        [
            ['table_a', 'node_a', 241, 37, 121],
            ['table_b', 'node_a', 30, 5, 12],
            ['table_c', 'node_b', 40, 6, 13],
        ]
    )
    assert sorted(per_node) == sorted(
        [
            ['node_a', 271, 42, 133],
            ['node_b', 40, 6, 13],
        ]
    )
    assert total == [[311, 48, 146]]


@pytest.mark.skipif(common.VERTICA_MAJOR_VERSION >= 11, reason='Requires Vertica < 11')
@pytest.mark.usefixtures('dd_environment')
def test_storage_containers_queries_pre_11(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='storage_containers',
        schema=[
            ('NODE_NAME', 'VARCHAR'),
            ('PROJECTION_NAME', 'VARCHAR'),
            ('STORAGE_TYPE', 'VARCHAR'),
            ('DELETE_VECTOR_COUNT', 'INTEGER'),
        ],
        data='\n'.join(
            [
                'node_a,proj_a,ROS,1',
                'node_a,proj_a,WOS,2',
                'node_a,proj_b,ROS,3',
                'node_b,proj_c,ROS,4',
            ]
        ),
    )

    queries = [q['query'] for q in builder.build_storage_containers_queries()]

    results = [list(client.query(query)) for query in queries]

    per_projection, per_node, total = results

    assert sorted(per_projection) == sorted(
        [
            ['node_a', 'proj_a', 'ROS', 1],
            ['node_a', 'proj_a', 'WOS', 2],
            ['node_a', 'proj_b', 'ROS', 3],
            ['node_b', 'proj_c', 'ROS', 4],
        ]
    )
    assert sorted(per_node) == sorted(
        [
            ['node_a', 6],
            ['node_b', 4],
        ]
    )
    assert total == [[10]]


@pytest.mark.skipif(common.VERTICA_MAJOR_VERSION < 11, reason='Requires Vertica >= 11')
@pytest.mark.usefixtures('dd_environment')
def test_storage_containers_queries_11_plus(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='storage_containers',
        schema=[('NODE_NAME', 'VARCHAR'), ('PROJECTION_NAME', 'VARCHAR'), ('DELETE_VECTOR_COUNT', 'INTEGER')],
        data='\n'.join(
            [
                'node_a,proj_a,2',
                'node_a,proj_b,3',
                'node_b,proj_c,4',
            ]
        ),
    )

    queries = [q['query'] for q in builder.build_storage_containers_queries()]

    results = [list(client.query(query)) for query in queries]

    per_projection, per_node, total = results

    assert sorted(per_projection) == sorted(
        [
            ['node_a', 'proj_a', 2],
            ['node_a', 'proj_b', 3],
            ['node_b', 'proj_c', 4],
        ]
    )
    assert sorted(per_node) == sorted(
        [
            ['node_a', 5],
            ['node_b', 4],
        ]
    )
    assert total == [[9]]


@pytest.mark.usefixtures('dd_environment')
def test_host_resources_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='host_resources',
        schema=[
            ('HOST_NAME', 'VARCHAR'),
            ('OPEN_FILES_LIMIT', 'INTEGER'),
            ('THREADS_LIMIT', 'INTEGER'),
            ('PROCESSOR_COUNT', 'INTEGER'),
            ('PROCESSOR_CORE_COUNT', 'INTEGER'),
            ('OPENED_FILE_COUNT', 'INTEGER'),
            ('OPENED_SOCKET_COUNT', 'INTEGER'),
            ('TOTAL_MEMORY_BYTES', 'INTEGER'),
            ('TOTAL_MEMORY_FREE_BYTES', 'INTEGER'),
            ('TOTAL_SWAP_MEMORY_BYTES', 'INTEGER'),
            ('TOTAL_SWAP_MEMORY_FREE_BYTES', 'INTEGER'),
        ],
        data='\n'.join(
            [
                'host_a,40,20,30,60,10,50,300,30,200,50',
                'host_b,0,0,0,0,0,0,0,0,0,0',
            ]
        ),
    )

    query = builder.build_host_resources_queries()[0]['query']

    results = list(client.query(query))

    assert results == [
        ['host_a', 30, 60, 40, 10, 50, 20, 300, 30, 270, 90, 200, 50, 150, 75],
        ['host_b', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]


@pytest.mark.usefixtures('dd_environment')
def test_disk_storage_query(client, builder, setup_db_tables):
    setup_db_tables(
        schema_name='fake_v_monitor',
        table_name='disk_storage',
        schema=[
            ('NODE_NAME', 'VARCHAR'),
            ('STORAGE_USAGE', 'VARCHAR'),
            ('THROUGHPUT', 'INTEGER'),
            ('LATENCY', 'INTEGER'),
            ('STORAGE_STATUS', 'VARCHAR'),
            ('DISK_BLOCK_SIZE_BYTES', 'INTEGER'),
            ('DISK_SPACE_USED_BLOCKS', 'INTEGER'),
            ('DISK_SPACE_FREE_BLOCKS', 'INTEGER'),
        ],
        data='\n'.join(
            [
                'node_a,DATA,2,5,active,100,9,1',
                'node_b,TEMP,0,0,retired,0,0,0',
            ]
        ),
    )

    query = builder.build_disk_storage_queries()[0]['query']

    results = list(client.query(query))

    assert results == [
        ['node_a', 'active', 'DATA', 100, 900, 1000, 90, 5, 2, Decimal('0.2'), Decimal('0.5'), Decimal('0.7')],
        ['node_b', 'retired', 'TEMP', 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
