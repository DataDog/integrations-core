# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 3000

INSTANCE = {
    'host': HOST,
    'port': PORT,
    'metrics': ['cluster_size', 'batch_error'],
    'namespace_metrics': [
        'objects',
        'hwm_breached',
        'client_write_error',
        'client_write_success',
        'objects',
        'tombstones',
        'stop_writes_count',
        'truncate_lut',
        'memory_data_bytes',
    ],
    'namespaces': ['test'],
    'datacenters': ['test'],
    'tags': ['tag:value'],
}

FULL_INSTANCE = {
    'host': HOST,
    'port': PORT,
    'metrics': ['cluster_size', 'batch_error'],
    'namespaces': ['test'],
    'datacenters': ['test'],
    'tags': ['tag:value'],
}

DATACENTER_METRICS = [
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
]
