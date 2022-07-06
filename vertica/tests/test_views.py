# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.vertica import views


def test_make_projection_storage_queries():
    queries = views.make_projection_storage_queries(9)

    assert 'per_projection' in queries
    assert 'per_table' in queries
    assert 'per_node' in queries
    assert 'total' in queries

    assert queries['per_projection'] == (
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
    )
