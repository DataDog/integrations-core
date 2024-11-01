# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8000


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    "tags": ['test:test'],
}

MOCKED_VERSION_ENDPOINT = f"http://{HOST}:{PORT}/version"

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'e2e_request_latency.seconds.bucket',
    'e2e_request_latency.seconds.count',
    'e2e_request_latency.seconds.sum',
    'generation_tokens.count',
    'gpu_cache_usage_percent',
    'num_request.max',
    'num_requests.running',
    'num_requests.waiting',
    'process.cpu_seconds.count',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory_bytes',
    'process.start_time_seconds',
    'process.virtual_memory_bytes',
    'prompt_tokens.count',
    'python.gc.collections.count',
    'python.gc.objects.collected.count',
    'python.gc.objects.uncollectable.count',
    'python.info',
    'request.failure.count',
    'request.finish.count',
    'request.generation_tokens.bucket',
    'request.generation_tokens.count',
    'request.generation_tokens.sum',
    'request.prompt_tokens.bucket',
    'request.prompt_tokens.count',
    'request.prompt_tokens.sum',
    'request.success.count',
    'time_per_output_token.seconds.bucket',
    'time_per_output_token.seconds.count',
    'time_per_output_token.seconds.sum',
    'time_to_first_token.seconds.bucket',
    'time_to_first_token.seconds.count',
    'time_to_first_token.seconds.sum',
]

METRICS_MOCK = [f'nvidia_nim.{m}' for m in METRICS_MOCK]
