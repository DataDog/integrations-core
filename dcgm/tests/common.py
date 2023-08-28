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
    'dram.active',
    'enc_utilization',
    'fan_speed',
    'frame_buffer.free',
    'frame_buffer.reserved',
    'frame_buffer.total',
    'frame_buffer.used',
    'frame_buffer.used_percent',
    'gpu_utilization',
    'gr_engine_active',
    'mem.clock',
    'mem.copy_utilization',
    'mem.temperature',
    'nvlink_bandwidth.count',
    'pcie_replay.count',
    'pcie_rx_throughput.count',
    'pcie_tx_throughput.count',
    'pipe.fp16_active',
    'pipe.fp32_active',
    'pipe.fp64_active',
    'pipe.tensor_active',
    'power_management_limit',
    'power_usage',
    'pstate',
    'row_remap_failure',
    'slowdown_temperature',
    'sm_active',
    'sm_clock',
    'sm_occupancy',
    'temperature',
    'total_energy_consumption.count',
    'uncorrectable_remapped_rows.count',
    'vgpu_license_status',
    'xid_errors',
]
EXPECTED_METRICS = [f'dcgm.{m}' for m in EXPECTED_METRICS]
assert sorted(EXPECTED_METRICS) == EXPECTED_METRICS, 'Please keep this list in alphabetic order!'
