# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See: https://github.com/Azure/iotedge/blob/1.0.10-rc2/doc/BuiltInMetrics.md#edgehub
EDGE_HUB_METRICS = [
    {
        'edgehub_queue_length': 'queue_length',
        'edgehub_gettwin_total': 'gettwin_total',
        'edgehub_messages_received_total': 'messages_received_total',
        'edgehub_messages_sent_total': 'messages_sent_total',
        'edgehub_reported_properties_total': 'reported_properties_total',
        'edgehub_gettwin_duration_seconds': 'gettwin_duration_seconds',
        'edgehub_message_send_duration_seconds': 'message_send_duration_seconds',
        'edgehub_message_process_duration_seconds': 'message_process_duration_seconds',
        'edgehub_reported_properties_update_duration_seconds': 'reported_properties_update_duration_seconds',
        'edgehub_direct_method_duration_seconds': 'direct_method_duration_seconds',
        'edgehub_direct_methods_total': 'direct_methods_total',
        'edgehub_messages_dropped_total': 'messages_dropped_total',
        'edgehub_messages_unack_total': 'messages_unack_total',
        'edgehub_offline_count_total': 'offline_count_total',
        'edgehub_offline_duration_seconds': 'offline_duration_seconds',
        'edgehub_operation_retry_total': 'operation_retry_total',
        'edgehub_client_connect_failed_total': 'client_connect_failed_total',
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

EDGE_AGENT_TYPE_OVERRIDES = {
    # Prometheus endpoint sends these as 'gauge', but the values represent monotonic counts.
    'edgeAgent_total_network_in_bytes': 'counter',
    'edgeAgent_total_network_out_bytes': 'counter',
    'edgeAgent_total_disk_read_bytes': 'counter',
    'edgeAgent_total_disk_write_bytes': 'counter',
}
