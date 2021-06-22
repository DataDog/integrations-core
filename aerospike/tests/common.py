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
VERSION = os.environ.get('AEROSPIKE_VERSION')

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

SET_METRICS = ['tombstones', 'memory_data_bytes', 'truncate_lut', 'objects', 'stop_writes_count', 'disable_eviction']

ALL_METRICS = NAMESPACE_METRICS + SET_METRICS

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
