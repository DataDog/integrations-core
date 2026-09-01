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

MOCKED_INSTANCE_RAY = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics_prefix",
    "tags": ['test:test'],
}

MOCKED_VERSION_ENDPOINT = f"http://{HOST}:{PORT}/version"

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'avg.generation_throughput.toks_per_s',
    'avg.prompt.throughput.toks_per_s',
    'cache_config_info',
    'cpu_cache_usage_perc',
    'e2e_request_latency.seconds.bucket',
    'e2e_request_latency.seconds.count',
    'e2e_request_latency.seconds.sum',
    'engine_sleep_state',
    'external_prefix_cache.hits.count',
    'external_prefix_cache.queries.count',
    'generation_tokens.count',
    'gpu_cache_usage_perc',
    'inter_token_latency.seconds.bucket',
    'inter_token_latency.seconds.count',
    'inter_token_latency.seconds.sum',
    'iteration_tokens_total.bucket',
    'iteration_tokens_total.count',
    'iteration_tokens_total.sum',
    'kv_cache_usage_perc',
    'mm_cache.hits.count',
    'mm_cache.queries.count',
    'num_preemptions.count',
    'num_requests.running',
    'num_requests.swapped',
    'num_requests.waiting',
    'prefix_cache.hits.count',
    'prefix_cache.queries.count',
    'process.cpu_seconds.count',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory_bytes',
    'process.start_time_seconds',
    'process.virtual_memory_bytes',
    'prompt_tokens.count',
    'prompt_tokens_by_source.count',
    'prompt_tokens_cached.count',
    'prompt_tokens_recomputed.count',
    'python.gc.collections.count',
    'python.gc.objects.collected.count',
    'python.gc.objects.uncollectable.count',
    'python.info',
    'request.decode_time.seconds.bucket',
    'request.decode_time.seconds.count',
    'request.decode_time.seconds.sum',
    'request.generation_tokens.bucket',
    'request.generation_tokens.count',
    'request.generation_tokens.sum',
    'request.inference_time.seconds.bucket',
    'request.inference_time.seconds.count',
    'request.inference_time.seconds.sum',
    'request.max_num_generation_tokens.bucket',
    'request.max_num_generation_tokens.count',
    'request.max_num_generation_tokens.sum',
    'request.params.best_of.bucket',
    'request.params.best_of.count',
    'request.params.best_of.sum',
    'request.params.max_tokens.bucket',
    'request.params.max_tokens.count',
    'request.params.max_tokens.sum',
    'request.params.n.bucket',
    'request.params.n.count',
    'request.params.n.sum',
    'request.prefill_kv_computed_tokens.bucket',
    'request.prefill_kv_computed_tokens.count',
    'request.prefill_kv_computed_tokens.sum',
    'request.prefill_time.seconds.bucket',
    'request.prefill_time.seconds.count',
    'request.prefill_time.seconds.sum',
    'request.prompt_tokens.bucket',
    'request.prompt_tokens.count',
    'request.prompt_tokens.sum',
    'request.queue_time.seconds.bucket',
    'request.queue_time.seconds.count',
    'request.queue_time.seconds.sum',
    'request.success.count',
    'request.time_per_output_token.seconds.bucket',
    'request.time_per_output_token.seconds.count',
    'request.time_per_output_token.seconds.sum',
    'time_per_output_token.seconds.bucket',
    'time_per_output_token.seconds.count',
    'time_per_output_token.seconds.sum',
    'time_to_first_token.seconds.bucket',
    'time_to_first_token.seconds.count',
    'time_to_first_token.seconds.sum',
]

METRICS_MOCK = [f'vllm.{m}' for m in METRICS_MOCK]
