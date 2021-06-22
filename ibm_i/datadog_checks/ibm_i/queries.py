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
        {'name': 'ibm_i.asp.unit_storage_capacity', 'type': 'gauge'},
        {'name': 'ibm_i.asp.unit_space_available', 'type': 'gauge'},
        {'name': 'ibm_i.asp.percent_used', 'type': 'gauge'},
    ],
}

CPUUsage = {
    'name': 'cpu_usage',
    'query': 'SELECT AVERAGE_CPU_UTILIZATION FROM QSYS2.SYSTEM_STATUS_INFO',
    'columns': [
        {'name': 'ibm_i.system.cpu_usage', 'type': 'gauge'},
    ],
}

JobStatus = {
    'name': 'job_status',
    'query': (
        # TODO: try to move the JOB_NAME split logic to Python
        "SELECT SUBSTR(JOB_NAME,1,POSSTR(JOB_NAME,'/')-1) AS JOB_ID, "
        "SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1,POSSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),'/')-1) AS JOB_USER, "
        "SUBSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),POSSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),'/')+1) AS JOB_NAME, "  # noqa:E501
        "JOB_SUBSYSTEM, "
        "CASE WHEN JOB_STATUS = 'ACTIVE' THEN 1 ELSE 0 END "
        "FROM TABLE(QSYS2.JOB_INFO('*ALL', '*ALL', '*ALL', '*ALL', '*ALL'))"
    ),
    'columns': [
        {'name': 'job_id', 'type': 'tag'},
        {'name': 'job_user', 'type': 'tag'},
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibm_i.job.active', 'type': 'gauge'},
    ],

}

JobCPUUsage = {
    'name': 'job_cpu_usage',
    'query': (
        # We prefer using ELAPSED_CPU_TIME / ELAPSED_TIME over ELAPSED_CPU_PERCENTAGE
        # because the latter only has a precision of one decimal.
        # ELAPSED_CPU_TIME is in milliseconds, while ELAPSED_TIME is in seconds
        # -> / 1000 to convert into seconds / seconds
        # -> * 100 to convert the resulting rate into a percentage
        # TODO: figure out why there a x4 difference with the value
        # given by ELAPSED_CPU_PERCENTAGE.
        # TODO: try to move the JOB_NAME split logic to Python
        "SELECT SUBSTR(A.JOB_NAME,1,POSSTR(A.JOB_NAME,'/')-1) AS JOB_ID, "
        "SUBSTR(A.JOB_NAME,POSSTR(A.JOB_NAME,'/')+1,POSSTR(SUBSTR(A.JOB_NAME,POSSTR(A.JOB_NAME,'/')+1),'/')-1) AS JOB_USER, "  # noqa:E501
        "SUBSTR(SUBSTR(A.JOB_NAME,POSSTR(A.JOB_NAME,'/')+1),POSSTR(SUBSTR(A.JOB_NAME,POSSTR(A.JOB_NAME,'/')+1),'/')+1) AS JOB_NAME, "  # noqa:E501
        "A.SUBSYSTEM, A.JOB_STATUS, "
        "CASE WHEN A.ELAPSED_TIME = 0 THEN 0 ELSE A.ELAPSED_CPU_TIME / (10 * A.ELAPSED_TIME) END AS CPU_RATE "
        # Two queries: one to fetch the stats, another to reset them
        "FROM TABLE(QSYS2.ACTIVE_JOB_INFO('NO', '', '', '')) A INNER JOIN TABLE(QSYS2.ACTIVE_JOB_INFO('YES', '', '', '')) B "  # noqa:E501
        # Assumes that INTERNAL_JOB_ID is unique, which should be the case
        "ON A.INTERNAL_JOB_ID = B.INTERNAL_JOB_ID"
    ),
    'columns': [
        {'name': 'job_id', 'type': 'tag'},
        {'name': 'job_user', 'type': 'tag'},
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'job_status', 'type': 'tag'},
        {'name': 'ibm_i.job.cpu_usage', 'type': 'gauge'},
    ],
}

JobMemoryUsage = {
    'name': 'job_memory_usage',
    'query': (
        # TODO: try to move the JOB_NAME split logic to Python
        "SELECT SUBSTR(JOB_NAME,1,POSSTR(JOB_NAME,'/')-1) AS JOB_ID, "
        "SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1,POSSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),'/')-1) AS JOB_USER, "
        "SUBSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),POSSTR(SUBSTR(JOB_NAME,POSSTR(JOB_NAME,'/')+1),'/')+1) AS JOB_NAME, "  # noqa:E501
        "SUBSYSTEM, JOB_STATUS, MEMORY_POOL, TEMPORARY_STORAGE FROM "
        "TABLE(QSYS2.ACTIVE_JOB_INFO('NO', '', '', ''))"
    ),
    'columns': [
        {'name': 'job_id', 'type': 'tag'},
        {'name': 'job_user', 'type': 'tag'},
        {'name': 'job_name', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'job_status', 'type': 'tag'},
        {'name': 'memory_pool_name', 'type': 'tag'},
        {'name': 'ibm_i.job.temp_storage', 'type': 'gauge'},
    ],
}

MemoryInfo = {
    'name': 'memory_info',
    'query': (
        'SELECT POOL_NAME, SUBSYSTEM_NAME, CURRENT_SIZE, RESERVED_SIZE, DEFINED_SIZE FROM QSYS2.MEMORY_POOL_INFO'
    ),
    'columns': [
        {'name': 'pool_name', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibm_i.pool.size', 'type': 'gauge'},
        {'name': 'ibm_i.pool.reserved_size', 'type': 'gauge'},
        {'name': 'ibm_i.pool.defined_size', 'type': 'gauge'},
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
        {'name': 'ibm_i.subsystem.active', 'type': 'gauge'},
        {'name': 'ibm_i.subsystem.active_jobs', 'type': 'gauge'},
    ],
}

JobQueueInfo = {
    'name': 'job_queue',
    'query': (
        'SELECT JOB_QUEUE_NAME, JOB_QUEUE_STATUS, SUBSYSTEM_NAME,'
        'NUMBER_OF_JOBS, RELEASED_JOBS, SCHEDULED_JOBS, HELD_JOBS '
        'FROM QSYS2.JOB_QUEUE_INFO'
    ),
    'columns': [
        {'name': 'job_queue_name', 'type': 'tag'},
        {'name': 'job_queue_status', 'type': 'tag'},
        {'name': 'subsystem_name', 'type': 'tag'},
        {'name': 'ibm_i.job_queue.size', 'type': 'gauge'},
        {'name': 'ibm_i.job_queue.released_size', 'type': 'gauge'},
        {'name': 'ibm_i.job_queue.scheduled_size', 'type': 'gauge'},
        {'name': 'ibm_i.job_queue.held_size', 'type': 'gauge'},
    ],
}

MessageQueueInfo = {
    'name': 'message_queue_info',
    'query': (
        'SELECT MESSAGE_QUEUE_NAME, MESSAGE_QUEUE_LIBRARY, COUNT(*), SUM(CASE WHEN SEVERITY >= 70 THEN 1 ELSE 0 END) '
        'FROM QSYS2.MESSAGE_QUEUE_INFO GROUP BY MESSAGE_QUEUE_NAME, MESSAGE_QUEUE_LIBRARY'
    ),
    'columns': [
        {'name': 'message_queue_name', 'type': 'tag'},
        {'name': 'message_queue_library', 'type': 'tag'},
        {'name': 'ibm_i.message_queue.size', 'type': 'gauge'},
        {'name': 'ibm_i.message_queue.critical_size', 'type': 'gauge'},
    ],
}

IBMMQInfo = {
    'name': 'ibm_mq_info',
    'query': 'SELECT QNAME, COUNT(*) FROM TABLE(MQREADALL()) GROUP BY QNAME',
    'columns': [
        {'name': 'message_queue_name', 'type': 'tag'},
        {'name': 'ibm_i.ibm_mq.size', 'type': 'gauge'},
    ],
}
