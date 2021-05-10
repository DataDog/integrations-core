# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

DiskUsage = {
    'name': 'disk_usage',
    'query': (
        'SELECT ASP_NUMBER, UNIT_NUMBER, UNIT_TYPE, UNIT_STORAGE_CAPACITY, '
        'UNIT_SPACE_AVAILABLE, PERCENT_USED FROM QSYS2.SYSDISKSTAT'
    ),
    'columns': [
        {'name': 'asp_number', 'type': 'tag'},
        {'name': 'unit_number', 'type': 'tag'},
        {'name': 'unit_type', 'type': 'tag'},
        {'name': 'ibmi.asp.unit_storage_capacity', 'type': 'gauge'},
        {'name': 'ibmi.asp.unit_space_available', 'type': 'gauge'},
        {'name': 'ibmi.asp.percent_used', 'type': 'gauge'},
    ],
}

CPUUsage = {
    'name': 'cpu_usage',
    'query': 'SELECT AVERAGE_CPU_UTILIZATION FROM QSYS2.SYSTEM_STATUS_INFO',
    'columns': [
        {'name': 'ibmi.system.cpu_usage', 'type': 'gauge'},
    ],
}

JobStatus = {
    'name': 'job_status',
    'query': (
        # CPU_TIME is in milliseconds
        # -> / 1000 to convert into seconds
        # -> * 100 to convert the resulting rate into a percentage
        # TODO: figure out why there a x4 difference with the value
        # given by ELAPSED_CPU_PERCENTAGE
        'SELECT JOB_NAME, JOB_STATUS, CPU_TIME / 10, 1 FROM '
        'TABLE(QSYS2.ACTIVE_JOB_INFO(\'NO\', \'\', \'\', \'\'))'
    ),
    'columns': [
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'job_status', 'type': 'tag'},
        {'name': 'ibmi.job.cpu_usage', 'type': 'rate'},
        {'name': 'ibmi.job.active', 'type': 'gauge'}
    ],
}

JobMemoryUsage = {
    'name': 'job_memory_usage',
    'query': (
        'SELECT JOB_NAME, JOB_STATUS, MEMORY_POOL, TEMPORARY_STORAGE FROM '
        'TABLE(QSYS2.ACTIVE_JOB_INFO(\'NO\', \'\', \'\', \'\'))'
    ),
    'columns': [
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'job_status', 'type': 'tag'},
        {'name': 'memory_pool_name', 'type': 'tag'},
        {'name': 'ibmi.job.temp_storage', 'type': 'gauge'},
    ],
}

MemoryInfo = {
    'name': 'memory_info',
    'query': (
        'SELECT POOL_NAME, SUBSYSTEM_NAME, CURRENT_SIZE, RESERVED_SIZE, DEFINED_SIZE FROM '
        'QSYS2.MEMORY_POOL_INFO'
    ),
    'columns': [
        {'name': 'pool_name', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibmi.pool.size', 'type': 'gauge'},
        {'name': 'ibmi.pool.reserved_size', 'type': 'gauge'},
        {'name': 'ibmi.pool.defined_size', 'type': 'gauge'}
    ],
}

SubsystemInfo = {
    'name': 'subsystem',
    'query': (
        'SELECT SUBSYSTEM_DESCRIPTION, CASE WHEN STATUS = \'ACTIVE\' THEN '
        '1 ELSE 0 END, CURRENT_ACTIVE_JOBS FROM QSYS2.SUBSYSTEM_INFO'
    ),
    'columns': [
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibmi.subsystem.active', 'type': 'gauge'},
        {'name': 'ibmi.subsystem.active_jobs', 'type': 'gauge'},
    ],
}

JobQueueInfo = {
    'name': 'job_queue',
    'query':  (
        'SELECT JOB_QUEUE_NAME, JOB_QUEUE_STATUS, SUBSYSTEM_NAME,'
        'NUMBER_OF_JOBS, RELEASED_JOBS, SCHEDULED_JOBS, HELD_JOBS '
        'FROM QSYS2.JOB_QUEUE_INFO'
    ),
    'columns': [
        {'name': 'job_queue_name', 'type': 'tag'},
        {'name': 'job_queue_status', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibmi.job_queue.size', 'type': 'gauge'},
        {'name': 'ibmi.job_queue.released_size', 'type': 'gauge'},
        {'name': 'ibmi.job_queue.scheduled_size', 'type': 'gauge'},
        {'name': 'ibmi.job_queue.held_size', 'type': 'gauge'},
    ],
}
