# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = "8002"


def get_fixture_path(filename):
    return os.path.join(HERE, 'docker', filename)


INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:test'],
}

INSTANCE_DISABLED_SERVER_INFO = {
    'openmetrics_endpoint': f'http://{HOST}:{PORT}/metrics',
    'collect_server_info': False,
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = {
    'cache.insertion.duration',
    'cache.lookup.duration',
    'cache.num.entries',
    'cache.num.evictions',
    'cache.num.hits',
    'cache.num.lookups',
    'cache.num.misses',
    'cache.util',
    'cpu.memory.total_bytes',
    'cpu.memory.used_bytes',
    'cpu.utilization',
    'energy.consumption.count',
    'gpu.memory.total_bytes',
    'gpu.memory.used_bytes',
    'gpu.power.limit',
    'gpu.power.usage',
    'gpu.utilization',
    'inference.compute.infer.duration_us.count',
    'inference.compute.infer.summary_us.count',
    'inference.compute.infer.summary_us.sum',
    'inference.compute.infer.summary_us.quantile',
    'inference.compute.input.duration_us.count',
    'inference.compute.input.summary_us.count',
    'inference.compute.input.summary_us.sum',
    'inference.compute.input.summary_us.quantile',
    'inference.compute.output.duration_us.count',
    'inference.compute.output.summary_us.count',
    'inference.compute.output.summary_us.sum',
    'inference.compute.output.summary_us.quantile',
    'inference.count.count',
    'inference.exec.count.count',
    'inference.pending.request.count',
    'inference.queue.duration_us.count',
    'inference.queue.summary_us.count',
    'inference.queue.summary_us.sum',
    'inference.queue.summary_us.quantile',
    'inference.request.duration_us.count',
    'inference.request.summary_us.count',
    'inference.request.summary_us.sum',
    'inference.request.summary_us.quantile',
    'inference.request_failure.count',
    'inference.request_success.count',
}

METRICS_MOCK = [f'nvidia_triton.{m}' for m in METRICS_MOCK]
