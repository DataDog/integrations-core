# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 30000


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': f'http://{HOST}:{PORT}/metrics',
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS = [
    'http.requests.active',
    'num_requests.running',
    'num_requests.waiting',
    'kv_cache.used_tokens',
    'kv_cache.usage',
    'kv_cache.hit_rate',
    'kv_cache.max_tokens',
    'generation_throughput.tokens_per_second',
    'scheduler.utilization',
    'cuda_graph.active',
    'prompt_tokens.count',
    'generation_tokens.count',
    'cached_tokens.count',
    'requests.count',
    'requests.retracted',
    'spec_decode.accept_length',
    'spec_decode.accept_rate',
    'startup.seconds',
    'weight_load.seconds',
    'process.cpu_seconds.count',
]

HISTOGRAMS = [
    'time_to_first_token.seconds',
    'inter_token_latency.seconds',
    'e2e_request_latency.seconds',
    'queue_time.seconds',
    'request.prompt_tokens',
    'request.generation_tokens',
]

# Histograms are submitted as distributions under the base metric name.
METRICS.extend(f'{metric}.{suffix}' for metric in HISTOGRAMS for suffix in ('count', 'sum'))
METRICS = [f'sglang.{metric}' for metric in METRICS]
HISTOGRAMS = [f'sglang.{metric}' for metric in HISTOGRAMS]
