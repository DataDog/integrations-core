# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See: https://github.com/Azure/iotedge/blob/1.0.10-rc2/doc/BuiltInMetrics.md#edgehub
EDGE_HUB_METRICS = [
    {
        'edgehub_queue_length': 'queue.length',
    },
]

# See: https://github.com/Azure/iotedge/blob/1.0.10-rc2/doc/BuiltInMetrics.md#edgeagent
EDGE_AGENT_METRICS = [
    {
        # One copy for each module.
        'edgeAgent_total_time_running_correctly_seconds': 'total_time_running_correctly_seconds',
        'edgeAgent_total_time_expected_running_seconds': 'total_time_expected_running_seconds',
        'edgeAgent_command_latency_seconds': 'command_latency_seconds',
        'edgeAgent_available_disk_space_bytes': 'available_disk_space_bytes',
        'edgeAgent_total_disk_space_bytes': 'total_disk_space_bytes',
        'edgeAgent_used_memory_bytes': 'used_memory_bytes',
        'edgeAgent_total_memory_bytes': 'total_memory_bytes',
        'edgeAgent_used_cpu_percent': 'used_cpu_percent',
        'edgeAgent_created_pids_total': 'created_pids_total',
        'edgeAgent_total_network_in_bytes': 'total_network_in_bytes',
        'edgeAgent_total_network_out_bytes': 'total_network_out_bytes',
        'edgeAgent_total_disk_read_bytes': 'total_disk_read_bytes',
        'edgeAgent_total_disk_write_bytes': 'total_disk_write_bytes',
        # One copy for each module, except the Edge Agent.
        'edgeAgent_module_start_total': 'module_start_total',
        'edgeAgent_module_stop_total': 'module_stop_total',
        # Single copy.
        'edgeAgent_iothub_syncs_total': 'iothub_syncs_total',
        'edgeAgent_unsuccessful_iothub_syncs_total': 'unsuccessful_iothub_syncs_total',
        'edgeAgent_deployment_time_seconds': 'deployment_time_seconds',
        'edgeAgent_host_uptime_seconds': 'host_uptime_seconds',
        'edgeAgent_iotedged_uptime_seconds': 'iotedged_uptime_seconds',
    },
]
