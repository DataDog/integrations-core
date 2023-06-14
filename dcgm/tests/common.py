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

# TODO will need to use this structure when comparing tags, etc.
# A representative sampling of metrics from the fixture used for unit tests
# for expected_metric in METRICS:
#     aggregator.assert_metric(name=f"dcgm.{expected_metric['name']}", at_least=0)
# METRICS = [
#     {"name": "dec_utilization"},
#     {"name": "enc_utilization"},
#     {"name": "fb_free"},
#     {"name": "fb_used"},
#     {"name": "temperature"},
#     {"name": "gpu_utilization"},
#     {"name": "mem_clock"},
#     {"name": "mem_copy_utilization"},
#     {"name": "nvlink_bandwidth.count"},
#     {"name": "pcie_replay_counter.count"},
#     {"name": "power_usage"},
#     {"name": "sm_clock"},
#     {"name": "total_energy_consumption.count"},
#     {"name": "vgpu_license_status"},
#     {"name": "xid_errors"},
#     {"name": "device_count.count"},
# ]

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
