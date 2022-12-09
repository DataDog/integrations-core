from collections import defaultdict

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
        'total_bytes_receive_rate_across_network_interfaces',
        'total_bytes_transmit_rate_across_network_interfaces',
        'total_read_bytes_rate_across_disks',
        'total_write_bytes_rate_across_disks',
        'total_read_ios_rate_across_disks',
        'total_write_ios_rate_across_disks',
        'health_good_rate',
        'health_concerning_rate',
        'health_bad_rate',
        'health_disabled_rate',
        'health_unknown_rate',
        'alerts_rate',
        'events_critical_rate',
        'events_important_rate',
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

NATIVE_METRICS = {
    'host': [
        'num_cores',
        'num_physical_cores',
        'total_phys_mem_bytes',
    ]
}


def merge_dicts(d1, d2):
    merged_dict = defaultdict(list)
    for d in (d1, d2):
        for key, value in d.items():
            merged_dict[key] += value
    return merged_dict


METRICS = merge_dicts(NATIVE_METRICS, TIMESERIES_METRICS)
