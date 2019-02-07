# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = 3003

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
    'namespaces': {'test'},
    'tags': ['tag:value'],
}
