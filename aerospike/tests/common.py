# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

# from datadog_checks.dev import get_docker_hostname
# HOST = get_docker_hostname()
# get_docker_hostname value value causes socket error on azure CI, so we have
# to hardcode the ip 127.0.0.1 to make it work.
# get_docker_hostname is still useful to test locally.
HOST = "127.0.0.1"
PORT = 3000
EXPORTER_PORT = 9145
VERSION = os.environ.get('AEROSPIKE_VERSION')

OPENMETRICS_V2_INSTANCE = {
    'openmetrics_endpoint': 'http://{}:{}/metrics'.format(HOST, EXPORTER_PORT),
    'tags': ['openmetrics_instance'],
}

EXPECTED_PROMETHEUS_METRICS = [
    'aerospike.aerospike_latencies_read_ms_bucket',
    'aerospike.aerospike_latencies_read_ms_count',
    'aerospike.aerospike_latencies_write_ms_bucket',
    'aerospike.aerospike_latencies_write_ms_count',
    'aerospike.aerospike_namespace_allow_nonxdr_writes',
    'aerospike.aerospike_namespace_allow_ttl_without_nsup',
    'aerospike.aerospike_namespace_allow_xdr_writes',
    'aerospike.aerospike_namespace_appeals_records_exonerated',
    'aerospike.aerospike_namespace_appeals_rx_active',
    'aerospike.aerospike_namespace_appeals_tx_active',
    'aerospike.aerospike_namespace_appeals_tx_remaining',
    'aerospike.aerospike_namespace_available_bin_names',
    'aerospike.aerospike_namespace_background_scan_max_rps',
    'aerospike.aerospike_namespace_batch_sub_proxy_complete',
    'aerospike.aerospike_namespace_batch_sub_proxy_error',
    'aerospike.aerospike_namespace_batch_sub_proxy_timeout',
    'aerospike.aerospike_namespace_batch_sub_read_error',
    'aerospike.aerospike_namespace_batch_sub_read_filtered_out',
    'aerospike.aerospike_namespace_batch_sub_read_not_found',
    'aerospike.aerospike_namespace_batch_sub_read_success',
    'aerospike.aerospike_namespace_batch_sub_read_timeout',
    'aerospike.aerospike_namespace_batch_sub_tsvc_error',
    'aerospike.aerospike_namespace_batch_sub_tsvc_timeout',
    'aerospike.aerospike_namespace_client_delete_error',
    'aerospike.aerospike_namespace_client_delete_filtered_out',
    'aerospike.aerospike_namespace_client_delete_not_found',
    'aerospike.aerospike_namespace_client_delete_success',
    'aerospike.aerospike_namespace_client_delete_timeout',
    'aerospike.aerospike_namespace_client_lang_delete_success',
    'aerospike.aerospike_namespace_client_lang_error',
    'aerospike.aerospike_namespace_client_lang_read_success',
    'aerospike.aerospike_namespace_client_lang_write_success',
    'aerospike.aerospike_namespace_client_proxy_complete',
    'aerospike.aerospike_namespace_client_proxy_error',
    'aerospike.aerospike_namespace_client_proxy_timeout',
    'aerospike.aerospike_namespace_client_read_error',
    'aerospike.aerospike_namespace_client_read_filtered_out',
    'aerospike.aerospike_namespace_client_read_not_found',
    'aerospike.aerospike_namespace_client_read_success',
    'aerospike.aerospike_namespace_client_read_timeout',
    'aerospike.aerospike_namespace_client_tsvc_error',
    'aerospike.aerospike_namespace_client_tsvc_timeout',
    'aerospike.aerospike_namespace_client_udf_complete',
    'aerospike.aerospike_namespace_client_udf_error',
    'aerospike.aerospike_namespace_client_udf_filtered_out',
    'aerospike.aerospike_namespace_client_udf_timeout',
    'aerospike.aerospike_namespace_client_write_error',
    'aerospike.aerospike_namespace_client_write_filtered_out',
    'aerospike.aerospike_namespace_client_write_success',
    'aerospike.aerospike_namespace_client_write_timeout',
    'aerospike.aerospike_namespace_clock_skew_stop_writes',
    'aerospike.aerospike_namespace_current_time',
    'aerospike.aerospike_namespace_dead_partitions',
    'aerospike.aerospike_namespace_device_available_pct',
    'aerospike.aerospike_namespace_hwm_breached',
    'aerospike.aerospike_namespace_memory_free_pct',
    'aerospike.aerospike_namespace_memory_used_bytes',
    'aerospike.aerospike_namespace_scan_aggr_error',
    'aerospike.aerospike_namespace_scan_basic_error',
    'aerospike.aerospike_namespace_scan_ops_bg_error',
    'aerospike.aerospike_namespace_scan_udf_bg_error',
    'aerospike.aerospike_namespace_sindex_num_partitions',
    'aerospike.aerospike_namespace_stop_writes',
    'aerospike.aerospike_namespace_storage_engine_file_defrag_q',
    'aerospike.aerospike_namespace_storage_engine_file_write_q',
    'aerospike.aerospike_namespace_unavailable_partitions',
    'aerospike.aerospike_node_stats_batch_index_error',
    'aerospike.aerospike_node_stats_client_connections',
    'aerospike.aerospike_node_stats_cluster_size',
    'aerospike.aerospike_node_stats_heap_efficiency_pct',
    'aerospike.aerospike_node_stats_rw_in_progress',
    'aerospike.aerospike_node_stats_sindex_gc_objects_validated',
    'aerospike.aerospike_node_stats_sindex_gc_retries',
    'aerospike.aerospike_node_stats_sindex_ucgarbage_found',
    'aerospike.aerospike_node_stats_system_free_mem_pct',
    'aerospike.aerospike_node_stats_system_kernel_cpu_pct',
    'aerospike.aerospike_node_stats_system_total_cpu_pct',
    'aerospike.aerospike_node_stats_system_user_cpu_pct',
    'aerospike.aerospike_node_stats_time_since_rebalance',
    'aerospike.aerospike_node_stats_tombstones',
    'aerospike.aerospike_node_stats_tree_gc_queue',
    'aerospike.aerospike_node_stats_uptime',
    'aerospike.aerospike_node_ticks',
    'aerospike.aerospike_node_up',
    'aerospike.aerospike_sets_disable_eviction',
    'aerospike.aerospike_sets_memory_data_bytes',
    'aerospike.aerospike_sets_objects',
    'aerospike.aerospike_sets_stop_writes_count',
    'aerospike.aerospike_sets_tombstones',
    'aerospike.aerospike_sets_truncate_lut',
    'aerospike.aerospike_sindex_delete_error',
    'aerospike.aerospike_sindex_delete_success',
    'aerospike.aerospike_sindex_entries',
    'aerospike.aerospike_sindex_histogram',
    'aerospike.aerospike_sindex_ibtr_memory_used',
    'aerospike.aerospike_sindex_keys',
    'aerospike.aerospike_sindex_load_pct',
    'aerospike.aerospike_sindex_loadtime',
    'aerospike.aerospike_sindex_nbtr_memory_used',
    'aerospike.aerospike_sindex_stat_gc_recs',
    'aerospike.aerospike_sindex_write_error',
    'aerospike.aerospike_sindex_write_success',
]

EXPECTED_PROMETHEUS_METRICS_5_6 = [
    'aerospike.aerospike_node_stats_client_connections_opened',
    'aerospike.aerospike_node_stats_fabric_connections_opened',
    'aerospike.aerospike_node_stats_heartbeat_connections_opened',
]

PROMETHEUS_XDR_METRICS = [
    'aerospike.aerospike_xdr_abandoned',
    'aerospike.aerospike_xdr_lag',
    'aerospike.aerospike_xdr_lap_us',
    'aerospike.aerospike_xdr_latency_ms',
    'aerospike.aerospike_xdr_recoveries',
    'aerospike.aerospike_xdr_recoveries_pending',
    'aerospike.aerospike_xdr_retry_conn_reset',
    'aerospike.aerospike_xdr_retry_dest',
    'aerospike.aerospike_xdr_retry_no_node',
    'aerospike.aerospike_xdr_success',
]

NAMESPACE_METRICS = [
    'objects',
    'hwm_breached',
    'client_write_error',
    'client_write_success',
    'tombstones',
    'retransmit_all_batch_sub_dup_res',
    'truncate_lut',
    'ops_sub_write_success',
]

TPS_METRICS = [
    'tps.write',
    'tps.read',
]

LEGACY_SET_METRICS = [
    'set.tombstones',
    'set.memory_data_bytes',
    'set.truncate_lut',
    'set._objects',
    'set.stop_writes_count',
    'set.disable_eviction',
]

SET_METRICS = ['enable_index', 'index_populating', 'sindexes']
# we support dashboards only latest set metrics
# SET_METRICS.extend(LEGACY_SET_METRICS)

ALL_METRICS = NAMESPACE_METRICS + LEGACY_SET_METRICS

INDEXES_METRICS = [
    "aerospike.sindex.delete_error",
    "aerospike.sindex.delete_success",
    "aerospike.sindex.entries",
    "aerospike.sindex.histogram",
    "aerospike.sindex.ibtr_memory_used",
    "aerospike.sindex.keys",
    "aerospike.sindex.load_pct",
    "aerospike.sindex.loadtime",
    "aerospike.sindex.nbtr_memory_used",
    "aerospike.sindex.query_agg",
    "aerospike.sindex.query_agg_avg_rec_count",
    "aerospike.sindex.query_agg_avg_record_size",
    "aerospike.sindex.query_avg_rec_count",
    "aerospike.sindex.query_avg_record_size",
    "aerospike.sindex.query_lookup_avg_rec_count",
    "aerospike.sindex.query_lookup_avg_record_size",
    "aerospike.sindex.query_lookups",
    "aerospike.sindex.query_reqs",
    "aerospike.sindex.si_accounted_memory",
    "aerospike.sindex.stat_gc_recs",
    "aerospike.sindex.stat_gc_time",
    "aerospike.sindex.write_error",
    "aerospike.sindex.write_success",
]

STATS_METRICS = [
    'cluster_size',
    'batch_index_initiate',
    'cluster_generation',
    'cluster_clock_skew_stop_writes_sec',
    'uptime',
]

LAZY_METRICS = [
    'aerospike.namespace.latency.write_over_64ms',
    'aerospike.namespace.latency.write_over_8ms',
    'aerospike.namespace.latency.write_over_1ms',
    'aerospike.namespace.latency.write_ops_sec',
    'aerospike.namespace.latency.read_over_64ms',
    'aerospike.namespace.latency.read_over_8ms',
    'aerospike.namespace.latency.read_over_1ms',
    'aerospike.namespace.latency.read_ops_sec',
    'aerospike.namespace.latency.batch_index_over_64ms',
    'aerospike.namespace.latency.batch_index_over_8ms',
    'aerospike.namespace.latency.batch_index_over_1ms',
    'aerospike.namespace.latency.batch_index_ops_sec',
]

LATENCIES_METRICS = [
    'aerospike.namespace.latency.read_over_1ms',
    'aerospike.namespace.latency.read_over_8ms',
    'aerospike.namespace.latency.read_over_64ms',
    'aerospike.namespace.latency.read',
    'aerospike.namespace.latency.read_ops_sec',
    'aerospike.namespace.latency.write_ops_sec',
    'aerospike.namespace.latency.write_over_1ms',
    'aerospike.namespace.latency.write_over_64ms',
    'aerospike.namespace.latency.write',
    'aerospike.namespace.latency.write_over_8ms',
    'aerospike.namespace.latency.batch_index_ops_sec',
    'aerospike.namespace.latency.batch_index_over_1ms',
    'aerospike.namespace.latency.batch_index_over_64ms',
    'aerospike.namespace.latency.batch_index',
    'aerospike.namespace.latency.batch_index_over_8ms',
]

INSTANCE = {
    'host': HOST,
    'port': PORT,
    'metrics': STATS_METRICS,
    'namespace_metrics': ALL_METRICS,
    'namespaces': ['test'],
    'datacenters': ['test'],
    'tags': ['tag:value'],
}

MOCK_INDEXES_METRICS = [
    "keys=1",
    "entries=1",
    "ibtr_memory_used=18688",
    "nbtr_memory_used=31",
    "si_accounted_memory=18719",
    "load_pct=100",
    "loadtime=7",
    "write_success=1",
    "write_error=0",
    "delete_success=0",
    "delete_error=0",
    "stat_gc_recs=0",
    "stat_gc_time=0",
    "query_reqs=0",
    "query_avg_rec_count=0",
    "query_avg_record_size=0",
    "query_agg=0",
    "query_agg_avg_rec_count=0",
    "query_agg_avg_record_size=0",
    "query_lookups=0",
    "query_lookup_avg_rec_count=0",
    "query_lookup_avg_record_size=0",
    "histogram=false",
]

MOCK_DATACENTER_METRICS = [
    'dc_state=CLUSTER_UP',
    'dc_timelag=0',
    'dc_rec_ship_attempts=58374',
    'dc_delete_ship_attempts=0',
    'dc_remote_ship_ok=58121',
    'dc_err_ship_client=38',
    'dc_err_ship_server=0',
    'dc_esmt_bytes_shipped=5662278',
    'dc_esmt_ship_avg_comp_pct=0.00',
    'dc_latency_avg_ship=0',
    'dc_remote_ship_avg_sleep=0.000',
    'dc_open_conn=192',
    'dc_recs_inflight=216',
    'dc_size=3',
    'dc_as_open_conn=3',
    'dc_as_size=2',
]

MOCK_XDR_DATACENTER_METRICS = """
ip-10-10-17-247.ec2.internal:3000 (10.10.17.247) returned:\n
lag=0;in_queue=0;in_progress=0;success=98344698;abandoned=0;not_found=0;filtered_out=0;retry_no_node=0;retry_conn_reset=775483;retry_dest=0;recoveries=293;recoveries_pending=0;hot_keys=20291210;uncompressed_pct=0.000;compression_ratio=1.000;throughput=0;latency_ms=17;lap_us=348
"""

# all datacenter metrics are referred as xdr metrics covered in PROMETHEUS_XDR_METRICS
DATACENTER_METRICS = [
    'aerospike.datacenter.dc_timelag',
    'aerospike.datacenter.dc_rec_ship_attempts',
    'aerospike.datacenter.dc_delete_ship_attempts',
    'aerospike.datacenter.dc_remote_ship_ok',
    'aerospike.datacenter.dc_err_ship_client',
    'aerospike.datacenter.dc_err_ship_server',
    'aerospike.datacenter.dc_esmt_bytes_shipped',
    'aerospike.datacenter.dc_esmt_ship_avg_comp_pct',
    'aerospike.datacenter.dc_latency_avg_ship',
    'aerospike.datacenter.dc_remote_ship_avg_sleep',
    'aerospike.datacenter.dc_open_conn',
    'aerospike.datacenter.dc_recs_inflight',
    'aerospike.datacenter.dc_size',
    'aerospike.datacenter.dc_as_open_conn',
    'aerospike.datacenter.dc_as_size',
]

# XDR metrics are covered in PROMETHEUS_XDR_METRICS
XDR_DC_METRICS = [
    'aerospike.xdr_dc.lag',
    'aerospike.xdr_dc.in_queue',
    'aerospike.xdr_dc.in_progress',
    'aerospike.xdr_dc.success',
    'aerospike.xdr_dc.abandoned',
    'aerospike.xdr_dc.not_found',
    'aerospike.xdr_dc.filtered_out',
    'aerospike.xdr_dc.retry_no_node',
    'aerospike.xdr_dc.retry_conn_reset',
    'aerospike.xdr_dc.retry_dest',
    'aerospike.xdr_dc.recoveries',
    'aerospike.xdr_dc.recoveries_pending',
    'aerospike.xdr_dc.hot_keys',
    'aerospike.xdr_dc.uncompressed_pct',
    'aerospike.xdr_dc.compression_ratio',
    'aerospike.xdr_dc.throughput',
    'aerospike.xdr_dc.latency_ms',
    'aerospike.xdr_dc.lap_us',
]
