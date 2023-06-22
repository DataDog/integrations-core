# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HOST = get_docker_hostname()
INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:9400/metrics",
}

INSTANCE_WRONG_URL = {
    'openmetrics_endpoint': 'http://localhost:5555/metrics',
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

EXPECTED_METRICS = [
    'dec_utilization',
    'enc_utilization',
    'fb_free',
    'fb_used',
    'temperature',
    'gpu_utilization',
    'mem.clock',
    'mem.copy_utilization',
    'nvlink_bandwidth.count',
    'pcie_replay.count',
    'power_usage',
    'sm_clock',
    'total_energy_consumption.count',
    'vgpu_license_status',
    'xid_errors',
    'device.count',
]
