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
    "collect_server_info": True,
}

MOCKED_VERSION_ENDPOINT = f"http://{HOST}:{PORT}/version"

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'python.gc.objects.collected.count',
    'python.gc.objects.uncollectable.count',
    'python.gc.collections.count',
    'python.info',
    'process.virtual_memory_bytes',
    'process.resident_memory_bytes',
    'process.start_time_seconds',
    'process.cpu_seconds.count',
    'process.open_fds',
    'process.max_fds',
    'cache_config_info',
    'num_requests.running',
    'num_requests.waiting',
    'num_requests.swapped',
    'cache_usage_perc',
    'cpu_cache_usage_perc',
    'num_preemptions.count',
    'prompt_tokens.count',
    'generation_tokens.count',
    'time_to_first_token.seconds.bucket',
    'time_to_first_token.seconds.count',
    'time_to_first_token.seconds.sum',
    'time_per_output_token.seconds.bucket',
    'time_per_output_token.seconds.count',
    'time_per_output_token.seconds.sum',
    'e2e.request_latency.seconds.bucket',
    'e2e.request_latency.seconds.count',
    'e2e.request_latency.seconds.sum',
    'request.prompt_tokens.bucket',
    'request.prompt_tokens.count',
    'request.prompt_tokens.sum',
    'request.generation_tokens.bucket',
    'request.generation_tokens.count',
    'request.generation_tokens.sum',
    'request.params.best_of.bucket',
    'request.params.best_of.count',
    'request.params.best_of.sum',
    'request.params.n.bucket',
    'request.params.n.count',
    'request.params.n.sum',
    'request.success.count',
    'avg.prompt.throughput.toks_per_s',
    'avg.generation_throughput.toks_per_s',
]

METRICS_MOCK = [f'vllm.{m}' for m in METRICS_MOCK]
