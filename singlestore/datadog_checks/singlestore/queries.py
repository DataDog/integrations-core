# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

MV_GLOBAL_STATUS = {
    'name': 'mv_global_status',
    'query': 'SELECT NODE_ID, IP_ADDR, PORT, NODE_TYPE, VARIABLE_NAME, VARIABLE_VALUE FROM '
    'INFORMATION_SCHEMA.MV_GLOBAL_STATUS',
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_type', 'type': 'tag'},
        {
            'name': 'VARIABLE_NAME',
            'type': 'match',
            'source': 'VARIABLE_VALUE',
            'items': {
                'Aborted_clients': {'name': 'aborted_clients', 'type': 'rate'},
                'Aborted_connects': {'name': 'aborted_connects', 'type': 'rate'},
                'Active_dedicated_admin_connections': {'name': 'active_dedicated_admin_connections', 'type': 'gauge'},
                'Auto_attach_remaining_seconds': {'name': 'auto_attach_remaining_seconds', 'type': 'gauge'},
                'Average_garbage_collection_duration': {'name': 'average_garbage_collection_duration', 'type': 'gauge'},
                'Buffer_manager_cached_memory': {'name': 'buffer_manager_cached_memory', 'type': 'gauge'},
                'Buffer_manager_memory': {'name': 'buffer_manager_memory', 'type': 'gauge'},
                'Buffer_manager_unrecycled_memory': {'name': 'buffer_manager_unrecycled_memory', 'type': 'gauge'},
                'Bytes_received': {'name': 'bytes_received', 'type': 'rate'},
                'Bytes_sent': {'name': 'bytes_sent', 'type': 'rate'},
                'Connections': {'name': 'connections', 'type': 'rate'},
                'Context_switches': {'name': 'context_switches', 'type': 'rate'},
                'Context_switch_misses': {'name': 'context_switch_misses', 'type': 'rate'},
                'Disk_space_reserved_for_secondary_index': {
                    'name': 'disk_space_reserved_for_secondary_index',
                    'type': 'gauge',
                },
                'Execution_time_of_reads': {
                    'name': 'execution_time_of_reads_pct',
                    'type': 'temporal_percent',
                    'scale': 1,
                },
                'Execution_time_of_write': {
                    'name': 'execution_time_of_write_pct',
                    'type': 'temporal_percent',
                    'scale': 1,
                },
                'Failed_read_queries': {'name': 'failed_read_queries', 'type': 'rate'},
                'Failed_write_queries': {'name': 'failed_write_queries', 'type': 'rate'},
                'Free_io_pool_memory': {'name': 'free_io_pool_memory', 'type': 'gauge'},
                'Idle_queue': {'name': 'idle_queue', 'type': 'gauge'},
                'Inflight_async_compilations': {'name': 'inflight_async_compilations', 'type': 'gauge'},
                'Ingest_errors_disk_space_use': {'name': 'ingest_errors_disk_space_use', 'type': 'gauge'},
                'License_capacity': {'name': 'license_capacity', 'type': 'gauge'},
                'Maximum_cluster_capacity': {'name': 'maximum_cluster_capacity', 'type': 'gauge'},
                'Queries': {'name': 'queries', 'type': 'rate'},
                'Query_compilations': {'name': 'query_compilations', 'type': 'rate'},
                'Query_compilation_failures': {'name': 'query_compilation_failures', 'type': 'rate'},
                'Questions': {'name': 'questions', 'type': 'rate'},
                'Ready_queue': {'name': 'ready_queue', 'type': 'gauge'},
                'Rows_affected_by_writes': {'name': 'rows_affected_by_writes', 'type': 'rate'},
                'Rows_returned_by_reads': {'name': 'rows_returned_by_reads', 'type': 'rate'},
                'Seconds_until_expiration': {'name': 'seconds_until_expiration', 'type': 'gauge'},
                'Ssl_accepts': {'name': 'ssl.accepts', 'type': 'rate'},
                'Ssl_accept_renegotiates': {'name': 'ssl.accept_renegotiates', 'type': 'rate'},
                'Ssl_client_connects': {'name': 'ssl.client_connects', 'type': 'rate'},
                'Ssl_connect_renegotiates': {'name': 'ssl.connect_renegotiates', 'type': 'rate'},
                'Ssl_finished_accepts': {'name': 'ssl.finished_accepts', 'type': 'rate'},
                'Ssl_finished_connects': {'name': 'ssl.finished_connects', 'type': 'rate'},
                'Successful_read_queries': {'name': 'successful_read_queries', 'type': 'rate'},
                'Successful_write_queries': {'name': 'successful_write_queries', 'type': 'rate'},
                'Threads_background': {'name': 'threads.background', 'type': 'gauge'},
                'Threads_cached': {'name': 'threads.cached', 'type': 'gauge'},
                'Threads_connected': {'name': 'threads.connected', 'type': 'gauge'},
                'Threads_created': {'name': 'threads.created', 'type': 'monotonic_gauge'},
                'Threads_idle': {'name': 'threads.idle', 'type': 'gauge'},
                'Threads_running': {'name': 'threads.running', 'type': 'gauge'},
                'Threads_shutdown': {'name': 'threads.shutdown', 'type': 'monotonic_gauge'},
                'Threads_waiting_for_disk_space': {'name': 'threads.waiting_for_disk_space', 'type': 'gauge'},
                'Total_io_pool_memory': {'name': 'total_io_pool_memory', 'type': 'gauge'},
                'Total_server_memory': {'name': 'total_server_memory', 'type': 'gauge'},
                'Transaction_buffer_wait_time': {'name': 'transaction_buffer_wait_time', 'type': 'gauge'},
                'Transaction_log_flush_wait_time': {'name': 'transaction_log_flush_wait_time', 'type': 'gauge'},
                'Uptime': {'name': 'uptime', 'type': 'gauge'},
                'Used_cluster_capacity': {'name': 'used_cluster_capacity', 'type': 'gauge'},
                'Used_instance_license_units': {'name': 'used_instance_license_units', 'type': 'gauge'},
                'Workload_management_active_connections': {
                    'name': 'workload_management_active_connections',
                    'type': 'gauge',
                },
                'Workload_management_active_queries': {'name': 'workload_management.active_queries', 'type': 'gauge'},
                'Workload_management_active_threads': {'name': 'workload_management.active_threads', 'type': 'gauge'},
                'Workload_management_queued_queries': {'name': 'workload_management.queued_queries', 'type': 'gauge'},
            },
        },
        {'name': 'VARIABLE_VALUE', 'type': 'source'},
    ],
}


AGGREGATORS = {
    'name': 'aggregators',
    'query': 'SELECT NODE_ID, HOST, PORT, ROLE, OPENED_CONNECTIONS, AVERAGE_ROUNDTRIP_LATENCY FROM '
    'INFORMATION_SCHEMA.AGGREGATORS',
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_role', 'type': 'tag'},
        {'name': 'aggregators.opened_connections', 'type': 'gauge'},
        {'name': 'aggregators.average_roundtrip_latency', 'type': 'gauge'},
    ],
}

LEAVES = {
    'name': 'leaves',
    'query': 'SELECT NODE_ID, HOST, PORT, AVAILABILITY_GROUP, PAIR_HOST, PAIR_PORT, OPENED_CONNECTIONS, '
    'AVERAGE_ROUNDTRIP_LATENCY FROM INFORMATION_SCHEMA.LEAVES',
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_leaf_availability_group', 'type': 'tag'},
        {'name': 'singlestore_pair_node_name', 'type': 'tag'},
        {'name': 'singlestore_pair_node_port', 'type': 'tag'},
        {'name': 'leaves.opened_connections', 'type': 'gauge'},
        {'name': 'leaves.average_roundtrip_latency', 'type': 'gauge'},
    ],
}

SYSINFO_CPU = {
    'name': 'mv_sysinfo_cpu',
    'query': "SELECT NODE_ID, IP_ADDR, PORT, TYPE, MEMSQL_TOTAL_CUMULATIVE_NS, MEMSQL_USER_CUMULATIVE_NS, "
    "MEMSQL_SYSTEM_CUMULATIVE_NS, TOTAL_USED_CUMULATIVE_NS, USER_CUMULATIVE_NS, NICE_CUMULATIVE_NS, "
    "SYSTEM_CUMULATIVE_NS, IDLE_CUMULATIVE_NS, IOWAIT_CUMULATIVE_NS, IRQ_CUMULATIVE_NS, "
    "SOFTIRQ_CUMULATIVE_NS, STEAL_CUMULATIVE_NS, GUEST_CUMULATIVE_NS, GUEST_NICE_CUMULATIVE_NS, NUM_CPUS "
    "FROM INFORMATION_SCHEMA.MV_SYSINFO_CPU",
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_type', 'type': 'tag'},
        {'name': 'cpu.memsql_total', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.memsql_user', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.memsql_system', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.total_used', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.user', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.nice', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.system', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.idle', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.iowait', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.irq', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.soft_irq', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.steal', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.guest', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.guest_nice', 'type': 'temporal_percent', 'scale': 'nanosecond'},
        {'name': 'cpu.cores_count', 'type': 'gauge'},
    ],
}

SYSINFO_DISK = {
    'name': 'mv_sysinfo_disk',
    'query': 'SELECT NODE_ID, IP_ADDR, PORT, TYPE, MOUNT_NAME, MOUNT_POINT, MOUNT_TOTAL_B, MOUNT_USED_B, '
    'MOUNT_TOTAL_B - MOUNT_USED_B, READ_CUMULATIVE_B, WRITE_CUMULATIVE_B FROM '
    'INFORMATION_SCHEMA.MV_SYSINFO_DISK',
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_type', 'type': 'tag'},
        {'name': 'mount_name', 'type': 'tag'},
        {'name': 'mount_point', 'type': 'tag'},
        {'name': 'disk.total', 'type': 'gauge'},
        {'name': 'disk.used', 'type': 'gauge'},
        {'name': 'disk.free', 'type': 'gauge'},
        {'name': 'disk.read_bytes', 'type': 'rate'},
        {'name': 'disk.write_bytes', 'type': 'rate'},
    ],
}

SYSINFO_MEM = {
    'name': 'mv_sysinfo_mem',
    'query': "SELECT NODE_ID, IP_ADDR, PORT, TYPE, HOST_TOTAL_B, HOST_USED_B, HOST_TOTAL_B - HOST_USED_B, "
    "CGROUP_TOTAL_B, CGROUP_USED_B, CGROUP_TOTAL_B - CGROUP_USED_B, MEMSQL_B FROM "
    "INFORMATION_SCHEMA.MV_SYSINFO_MEM",
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_type', 'type': 'tag'},
        {'name': 'mem.total', 'type': 'gauge'},
        {'name': 'mem.used', 'type': 'gauge'},
        {'name': 'mem.free', 'type': 'gauge'},
        {'name': 'mem.cgroup_total', 'type': 'gauge'},
        {'name': 'mem.cgroup_used', 'type': 'gauge'},
        {'name': 'mem.cgroup_free', 'type': 'gauge'},
        {'name': 'mem.singlestore_used_memory', 'type': 'gauge'},
    ],
}

SYSINFO_NET = {
    'name': 'mv_sysinfo_net',
    'query': "SELECT NODE_ID, IP_ADDR, PORT, TYPE, INTERFACE, RECEIVED_CUMULATIVE_B, TRANSMITTED_CUMULATIVE_B FROM "
    "INFORMATION_SCHEMA.MV_SYSINFO_NET",
    'columns': [
        {
            'name': 'singlestore_node_id',
            'type': 'tag',
        },
        {'name': 'singlestore_node_name', 'type': 'tag'},
        {'name': 'singlestore_node_port', 'type': 'tag'},
        {'name': 'singlestore_node_type', 'type': 'tag'},
        {
            'name': 'network_interface',
            'type': 'tag',
        },
        {
            'name': 'net.bytes_rx',
            'type': 'rate',
        },
        {
            'name': 'net.bytes_tx',
            'type': 'rate',
        },
    ],
}


VERSION_METADATA = {
    'name': 'version_metadata',
    'query': "SELECT VARIABLE_VALUE FROM INFORMATION_SCHEMA.GLOBAL_VARIABLES WHERE VARIABLE_NAME = 'MEMSQL_VERSION'",
    'columns': [{'name': 'version', 'type': 'metadata'}],
}
