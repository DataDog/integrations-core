# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.vertica.queries import build_projection_storage_queries, build_storage_containers_queries


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
    queries = build_projection_storage_queries(version)

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

    queries = build_storage_containers_queries(version)

    assert len(queries) == 3

    assert queries[0]['name'] == 'storage_containers_per_projection'
    assert queries[0]['query'] == expected_per_projection_query
    assert queries[0]['columns'][-1] == {'name': 'projection.delete_vectors', 'type': 'gauge'}
