# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:8002/metrics",
    'tags': ['test:test'],
}

INSTANCE_MOCK = {
    'openmetrics_endpoint': 'http://localhost:8002/metrics',
    'tags': ['test:test'],
}

INSTANCE_DISABLED_SERVER_INFO = {
    'openmetrics_endpoint': f'http://{HOST}:8002/metrics',
    'collect_server_info': False,
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = {
    'nv.cache.insertion.duration',
    'nv.cache.lookup.duration',
    'nv.cache.num.entries',
    'nv.cache.num.evictions',
    'nv.cache.num.hits',
    'nv.cache.num.lookups',
    'nv.cache.num.misses',
    'nv.cache.util',
    'nv.cpu.memory.total_bytes',
    'nv.cpu.memory.used_bytes',
    'nv.cpu.utilization',
    'nv.energy.consumption.count',
    'nv.gpu.memory.total_bytes',
    'nv.gpu.memory.used_bytes',
    'nv.gpu.power.limit',
    'nv.gpu.power.usage',
    'nv.gpu.utilization',
    'nv.inference.compute.infer.duration_us.count',
    'nv.inference.compute.infer.summary_us.count',
    'nv.inference.compute.infer.summary_us.sum',
    'nv.inference.compute.infer.summary_us.quantile',
    'nv.inference.compute.input.duration_us.count',
    'nv.inference.compute.input.summary_us.count',
    'nv.inference.compute.input.summary_us.sum',
    'nv.inference.compute.input.summary_us.quantile',
    'nv.inference.compute.output.duration_us.count',
    'nv.inference.compute.output.summary_us.count',
    'nv.inference.compute.output.summary_us.sum',
    'nv.inference.compute.output.summary_us.quantile',
    'nv.inference.count.count',
    'nv.inference.exec.count.count',
    'nv.inference.pending.request.count',
    'nv.inference.queue.duration_us.count',
    'nv.inference.queue.summary_us.count',
    'nv.inference.queue.summary_us.sum',
    'nv.inference.queue.summary_us.quantile',
    'nv.inference.request.duration_us.count',
    'nv.inference.request.summary_us.count',
    'nv.inference.request.summary_us.sum',
    'nv.inference.request.summary_us.quantile',
    'nv.inference.request_failure.count',
    'nv.inference.request_success.count',
}

METRICS_MOCK = [f'nvidia_triton.{m}' for m in METRICS_MOCK]
