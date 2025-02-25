# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://docs.aerospike.com/server/operations/monitor/key_metrics
METRIC_MAP = {
    'aerospike_namespace_clock_skew_stop_writes': 'namespace.clock_skew_stop_writes',
    'aerospike_namespace_dead_partitions': 'namespace.dead_partitions',
    'aerospike_namespace_device_available_pct': 'namespace.device_available_pct',
    'aerospike_namespace_hwm_breached': 'namespace.hwm_breached',
    'aerospike_namespace_memory_free_pct': 'namespace.memory_free_pct',
    'aerospike_namespace_stop_writes': 'namespace.stop_writes',
    # pmem only available when configured:
    # https://github.com/aerospike/aerospike-prometheus-exporter/issues/20#issuecomment-634476536
    'aerospike_namespace_pmem_available_pct': 'namespace.pmem_available_pct',
    'aerospike_namespace_unavailable_partitions': 'namespace.unavailable_partitions',
    'aerospike_node_stats_client_connections': 'node_stats.client_connections',
    'aerospike_node_stats_client_connections_opened': 'node_stats.client_connections_opened',
    'aerospike_node_stats_cluster_size': 'node_stats.cluster_size',
    'aerospike_node_stats_fabric_connections_opened': 'node_stats.fabric_connections_opened',
    'aerospike_node_stats_heartbeat_connections_opened': 'node_stats.heartbeat_connections_opened',
    'aerospike_node_stats_system_free_mem_pct': 'node_stats.system_free_mem_pct',
    'aerospike_xdr_lag': 'xdr.lag',
    'aerospike_namespace_client_delete_error': 'namespace.client_delete_error',
    'aerospike_namespace_client_read_error': 'namespace.client_read_error',
    'aerospike_namespace_client_read_success': 'namespace.client_read_success',
    'aerospike_namespace_client_read_not_found': 'namespace.client_read_not_found',
    'aerospike_namespace_client_read_timeout': 'namespace.client_read_timeout',
    'aerospike_namespace_client_read_filtered_out': 'namespace.client_read_filtered_out',
    'aerospike_namespace_client_udf_error': 'namespace.client_udf_error',
    'aerospike_namespace_client_write_error': 'namespace.client_write_error',
    'aerospike_namespace_client_write_success': 'namespace.client_write_success',
    'aerospike_namespace_client_write_timeout': 'namespace.client_write_timeout',
    'aerospike_namespace_client_write_filtered_out': 'namespace.client_write_filtered_out',
    # index_flash_alloc_pct only available in ee configured with index-type flash:
    # https://docs.aerospike.com/reference/metrics#index_flash_alloc_pct
    'aerospike_namespace_index_flash_alloc_pct': 'namespace.index_flash_alloc_pct',
    'aerospike_namespace_memory_used_bytes': 'namespace.memory_used_bytes',
    'aerospike_namespace_scan_aggr_error': 'namespace.scan_aggr_error',
    'aerospike_namespace_scan_basic_error': 'namespace.scan_basic_error',
    'aerospike_namespace_scan_ops_bg_error': 'namespace.scan_ops_bg_error',
    'aerospike_namespace_scan_udf_bg_error': 'namespace.scan_udf_bg_error',
    # storage_engine metrics available per-device or per-file depending on storage configuration:
    # https://github.com/aerospike/aerospike-prometheus-exporter/blob/bf6af43d758c6f96d7d34bf2b8742d3a6df4bfc8/watcher_namespaces.go#L383-L400
    'aerospike_namespace_storage_engine_device_defrag_q': 'namespace.storage_engine_device_defrag_q',
    'aerospike_namespace_storage_engine_file_defrag_q': 'namespace.storage_engine_file_defrag_q',
    'aerospike_namespace_storage_engine_device_write_q': 'namespace.storage_engine_device_write_q',
    'aerospike_namespace_storage_engine_file_write_q': 'namespace.storage_engine_file_write_q',
    'aerospike_node_stats_batch_index_error': 'node_stats.batch_index_error',
    'aerospike_node_stats_heap_efficiency_pct': 'node_stats.heap_efficiency_pct',
    'aerospike_node_stats_rw_in_progress': 'node_stats.rw_in_progress',
    'aerospike_xdr_abandoned': 'xdr.abandoned',
    'aerospike_xdr_lap_us': 'xdr.lap_us',
    'aerospike_xdr_latency_ms': 'xdr.latency_ms',
    'aerospike_xdr_recoveries': 'xdr.recoveries',
    'aerospike_xdr_recoveries_pending': 'xdr.recoveries_pending',
    'aerospike_xdr_retry_conn_reset': 'xdr.retry_conn_reset',
    'aerospike_xdr_retry_dest': 'xdr.retry_dest',
    'aerospike_xdr_retry_no_node': 'xdr.retry_no_node',
    'aerospike_xdr_success': 'xdr.success',
}
