# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HOST = get_docker_hostname()
INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:9400/metrics",
}

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

EXPECTED_METRICS = [
    'clock_throttle_reasons',
    'dec_utilization',
    'device.count',
    'enc_utilization',
    'frame_buffer.free',
    'frame_buffer.reserved',
    'frame_buffer.total',
    'frame_buffer.used',
    'frame_buffer.used_percent',
    'gpu_utilization',
    'mem.clock',
    'mem.copy_utilization',
    'nvlink_bandwidth.count',
    'pcie_replay.count',
    'power_management_limit',
    'power_usage',
    'pstate',
    'slowdown_temperature',
    'sm_clock',
    'temperature',
    'total_energy_consumption.count',
    'vgpu_license_status',
    'xid_errors',
]
