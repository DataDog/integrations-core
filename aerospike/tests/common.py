# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
PORT = 3000

NAMESPACE_METRICS = [
    'objects',
    'hwm_breached',
    'client_write_error',
    'client_write_success',
    'tombstones',
    'retransmit_all_batch_sub_dup_res',
    'truncate_lut',
    'tps.write',
    'tps.read',
    'ops_sub_write_success',
]

SET_METRICS = ['tombstones', 'memory_data_bytes', 'truncate_lut', 'objects', 'stop_writes_count']

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
