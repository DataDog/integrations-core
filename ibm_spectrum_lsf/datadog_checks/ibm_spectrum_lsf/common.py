# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def transform_status(status):
    return int(status == "ok")


def transform_int(val):
    if val == "-":
        return -1
    else:
        return int(val)


LSCLUSTERS = {
    'name': 'lsclusters',
    'expected_columns': 6,
    'tags': [
        {'name': 'lsf_cluster', 'id': 0},
        {'name': 'lsf_management_host', 'id': 2},
        {'name': 'lsf_admin', 'id': 3},
    ],
    'metrics': [
        {'name': 'cluster.status', 'id': 1, 'transform': transform_status},
        {'name': 'cluster.hosts', 'id': 4, 'transform': transform_int},
        {'name': 'cluster.servers', 'id': 5, 'transform': transform_int},
    ],
}
BHOSTS = {
    'name': 'bhosts',
    'expected_columns': 9,
    'tags': [
        {
            'name': 'lsf_host',
            'id': 0,
        }
    ],
    'metrics': [
        {'name': 'server.status', 'id': 1, 'transform': transform_status},
        {'name': 'server.slots_per_user', 'id': 2, 'transform': transform_int},
        {'name': 'server.max_jobs', 'id': 3, 'transform': transform_int},
        {'name': 'server.num_jobs', 'id': 4, 'transform': transform_int},
        {'name': 'server.running', 'id': 5, 'transform': transform_int},
        {'name': 'server.suspended', 'id': 6, 'transform': transform_int},
        {'name': 'server.user_suspended', 'id': 7, 'transform': transform_int},
        {'name': 'server.reserved', 'id': 8, 'transform': transform_int},
    ],
}
