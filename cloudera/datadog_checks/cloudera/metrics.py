TIMESERIES_METRICS = {
    'cluster': [
        'cpu_percent_across_hosts',
        'total_read_bytes_rate_across_disks',
        'total_write_bytes_rate_across_disks',
        'total_bytes_receive_rate_across_network_interfaces',
        'total_bytes_transmit_rate_across_network_interfaces',
    ],
    'host': [
        'cpu_user_rate',
        'cpu_system_rate',
        'cpu_nice_rate',
        'cpu_iowait_rate',
        'cpu_irq_rate',
        'cpu_soft_irq_rate',
        'cpu_steal_rate',
        'load_1',
        'load_5',
        'load_15',
        'swap_used',
        'swap_out_rate',
        'physical_memory_used',
        'physical_memory_total',
        'physical_memory_cached',
        'physical_memory_buffers',
    ],
    'role': [
        'mem_rss',
        'cpu_user_rate',
        'cpu_system_rate',
    ],
    'disk': [
        'service_time',
        'await_time',
        'await_read_time',
        'await_write_time',
    ],
}

NATIVE_METRICS = {}

METRICS = {**NATIVE_METRICS, **TIMESERIES_METRICS}
