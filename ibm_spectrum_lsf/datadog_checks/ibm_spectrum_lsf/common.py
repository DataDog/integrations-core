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
        val = val.rstrip(string.ascii_letters + string.punctuation)
        return float(val)


def transform_runtime(val):
    if val == "UNLIMITED":
        return -1
    else:
        return transform_float(val)


def transform_active(val):
    _, active = val.split(":")
    return active.lower() == "Active"


def transform_open(val):
    is_open, _ = val.split(":")
    return is_open.lower() == "Open"


def transform_job_id(val):
    parts = val.split("[")
    job_id = parts[0]
    return job_id


def transform_task_id(val):
    parts = val.split("[")
    if len(parts) > 1:
        second_part = parts[1].split("]")
        task_id = second_part[0]
        return task_id
    return None


def transform_tag(val):
    if val == "-":
        return None
    else:
        return val


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

LSLOAD = {
    'name': 'lsload',
    'prefix': 'load',
    'expected_columns': 13,
    'tags': [
        {
            'name': 'lsf_host',
            'id': 0,
        }
    ],
    'metrics': [
        {'name': 'status', 'id': 1, 'transform': transform_status},
        {'name': 'cpu.run_queue_length.15s', 'id': 2, 'transform': transform_float},
        {'name': 'cpu.run_queue_length.1m', 'id': 3, 'transform': transform_float},
        {'name': 'cpu.run_queue_length.15m', 'id': 4, 'transform': transform_float},
        {'name': 'cpu.utilization', 'id': 5, 'transform': transform_float},
        {'name': 'mem.paging_rate', 'id': 6, 'transform': transform_float},
        {'name': 'disk.io', 'id': 7, 'transform': transform_float},
        {'name': 'login_users', 'id': 8, 'transform': transform_float},
        {'name': 'idle_time', 'id': 9, 'transform': transform_float},
        {'name': 'mem.free', 'id': 10, 'transform': transform_float},
        {'name': 'mem.available_swap', 'id': 11, 'transform': transform_float},
        {'name': 'mem.available_ram', 'id': 12, 'transform': transform_float},
    ],
}

BSLOTS = {
    'name': 'bslots',
    'prefix': 'slots',
    'expected_columns': 2,
    'metrics': [
        {'name': 'backfill.available', 'id': 0, 'transform': transform_float},
        {'name': 'runtime_limit', 'id': 1, 'transform': transform_runtime},
    ],
}

BQUEUES = {
    'name': 'bqueues',
    'prefix': 'queue',
    'expected_columns': 11,
    'tags': [
        {
            'name': 'queue_name',
            'id': 0,
        }
    ],
    'metrics': [
        {'name': 'priority', 'id': 1, 'transform': transform_float},
        {'name': 'is_open', 'id': 2, 'transform': transform_open},
        {'name': 'is_active', 'id': 2, 'transform': transform_active},
        {'name': 'max_jobs', 'id': 3, 'transform': transform_float},
        {'name': 'max_jobs_per_user', 'id': 4, 'transform': transform_float},
        {'name': 'max_jobs_per_processor', 'id': 5, 'transform': transform_float},
        {'name': 'max_jobs_per_host', 'id': 6, 'transform': transform_float},
        {'name': 'num_job_slots', 'id': 7, 'transform': transform_float},
        {'name': 'pending', 'id': 8, 'transform': transform_float},
        {'name': 'running', 'id': 9, 'transform': transform_float},
        {'name': 'suspended', 'id': 10, 'transform': transform_float},
    ],
}

BJOBS = {
    'name': 'bjobs',
    'prefix': 'job',
    'expected_columns': 12,
    'tags': [
        {'name': 'job_id', 'id': 0, 'transform': transform_job_id},
        {'name': 'task_id', 'id': 0, 'transform': transform_task_id},
        {
            'name': 'full_job_id',
            'id': 0,
        },
        {
            'name': 'queue',
            'id': 2,
        },
        {
            'name': 'from_host',
            'id': 3,
        },
        {
            'name': 'exec_host',
            'id': 4,
        },
    ],
    'metrics': [
        {'name': 'run_time', 'id': 5, 'transform': transform_float},
        {'name': 'cpu_used', 'id': 6, 'transform': transform_float},
        {'name': 'mem', 'id': 7, 'transform': transform_float},
        {'name': 'time_left', 'id': 8, 'transform': transform_float},
        {'name': 'swap', 'id': 9, 'transform': transform_float},
        {'name': 'idle_factor', 'id': 10, 'transform': transform_float},
        {'name': 'percent_complete', 'id': 11, 'transform': transform_float},
    ],
}
