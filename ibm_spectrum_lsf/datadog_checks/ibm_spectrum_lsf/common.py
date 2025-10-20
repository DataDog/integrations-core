# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import string


def is_affirmative(val):
    return "yes" in val.lower()


def transform_status(status):
    return int(status == "ok")


def transform_float(val):
    if val == "-":
        return -1
    else:
        val = val.rstrip(string.ascii_letters)
        return float(val)


LSCLUSTERS = {
    'name': 'lsclusters',
    'prefix': 'cluster',
    'expected_columns': 6,
    'tags': [
        {'name': 'lsf_cluster', 'id': 0},
        {'name': 'lsf_management_host', 'id': 2},
        {'name': 'lsf_admin', 'id': 3},
    ],
    'metrics': [
        {'name': 'status', 'id': 1, 'transform': transform_status},
        {'name': 'hosts', 'id': 4, 'transform': transform_float},
        {'name': 'servers', 'id': 5, 'transform': transform_float},
    ],
}
BHOSTS = {
    'name': 'bhosts',
    'prefix': 'server',
    'expected_columns': 9,
    'tags': [
        {
            'name': 'lsf_host',
            'id': 0,
        }
    ],
    'metrics': [
        {'name': 'status', 'id': 1, 'transform': transform_status},
        {'name': 'slots_per_user', 'id': 2, 'transform': transform_float},
        {'name': 'max_jobs', 'id': 3, 'transform': transform_float},
        {'name': 'num_jobs', 'id': 4, 'transform': transform_float},
        {'name': 'running', 'id': 5, 'transform': transform_float},
        {'name': 'suspended', 'id': 6, 'transform': transform_float},
        {'name': 'user_suspended', 'id': 7, 'transform': transform_float},
        {'name': 'reserved', 'id': 8, 'transform': transform_float},
    ],
}

LSHOSTS = {
    'name': 'lshosts',
    'prefix': 'host',
    'expected_columns': 12,
    'tags': [
        {
            'name': 'lsf_host',
            'id': 0,
        },
        {
            'name': 'host_type',
            'id': 1,
        },
        {
            'name': 'host_model',
            'id': 2,
        },
    ],
    'metrics': [
        {'name': 'cpu_factor', 'id': 3, 'transform': transform_float},
        {'name': 'num_cpus', 'id': 4, 'transform': transform_float},
        {'name': 'max_mem', 'id': 5, 'transform': transform_float},
        {'name': 'max_swap', 'id': 6, 'transform': transform_float},
        {'name': 'is_server', 'id': 7, 'transform': is_affirmative},
        {'name': 'num_procs', 'id': 8, 'transform': transform_float},
        {'name': 'num_cores', 'id': 9, 'transform': transform_float},
        {'name': 'num_threads', 'id': 10, 'transform': transform_float},
        {'name': 'max_temp', 'id': 11, 'transform': transform_float},
    ],
}
