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
    'correctable_remapped_rows.count',
    'dec_utilization',
    'device.count',
    'enc_utilization',
    'fan_speed',
    'frame_buffer.free',
    'frame_buffer.reserved',
    'frame_buffer.total',
    'frame_buffer.used',
    'frame_buffer.used_percent',
    'gpu_utilization',
    'mem.clock',
    'mem.copy_utilization',
    'mem.temperature',
    'nvlink_bandwidth.count',
    'pcie_replay.count',
    'pcie_rx_throughput.count',
    'pcie_tx_throughput.count',
    'power_management_limit',
    'power_usage',
    'pstate',
    'row_remap_failure',
    'slowdown_temperature',
    'sm_clock',
    'temperature',
    'total_energy_consumption.count',
    'uncorrectable_remapped_rows.count',
    'vgpu_license_status',
    'xid_errors',
]
