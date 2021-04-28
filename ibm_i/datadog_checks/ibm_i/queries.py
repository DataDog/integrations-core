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
        {'name': 'disk.unit_storage_capacity', 'type': 'gauge'},
        {'name': 'disk.unit_space_available', 'type': 'gauge'},
        {'name': 'disk.percent_used', 'type': 'gauge'},
    ],
}

CPUUsage = {
    'name': 'cpu_usage',
    'query': (
        'SELECT AVERAGE_CPU_UTILIZATION FROM QSYS2.SYSTEM_STATUS_INFO'
    ),
    'columns': [
        {'name': 'ibmi.system.cpu_usage', 'type': 'gauge'},
    ],
}

JobStatus = {
    'name': 'job_status',
    'query': (
        'SELECT JOB_NAME, JOB_STATUS, ELAPSED_CPU_PERCENTAGE FROM '
        'TABLE(QSYS2.ACTIVE_JOB_INFO(\'NO\', \'\', \'\', \'\'))'
    ),
    'columns': [
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'job_status', 'type': 'tag'},
        {'name': 'ibmi.job.cpu_usage', 'type': 'gauge'},
    ],
}

SubsystemInfo = {
    'name': 'subsystem',
    'query': (
        'SELECT SUBSYSTEM_DESCRIPTION, STATUS, CURRENT_ACTIVE_JOBS FROM QSYS2.SUBSYSTEM_INFO'
    ),
    'columns': [
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'subsystem_status', 'type': 'tag'},
        {'name': 'ibmi.subsystem.active_jobs', 'type': 'gauge'},
    ],
}