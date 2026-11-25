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
    'cache.hit.duration_per_model.count',
    'cache.hit.histogram_us.bucket',
    'cache.hit.histogram_us.count',
    'cache.hit.histogram_us.sum',
    'cache.hit.summary_per_model.count',
    'cache.hit.summary_per_model.quantile',
    'cache.hit.summary_per_model.sum',
    'cache.insertion.duration',
    'cache.lookup.duration',
    'cache.miss.duration_per_model.count',
    'cache.miss.histogram_us.bucket',
    'cache.miss.histogram_us.count',
    'cache.miss.histogram_us.sum',
    'cache.miss.summary_per_model.count',
    'cache.miss.summary_per_model.quantile',
    'cache.miss.summary_per_model.sum',
    'cache.num.entries',
    'cache.num.evictions',
    'cache.num.hits',
    'cache.num.hits_per_model.count',
    'cache.num.lookups',
    'cache.num.misses',
    'cache.num.misses_per_model.count',
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
    'inference.compute.infer.histogram_us.bucket',
    'inference.compute.infer.histogram_us.count',
    'inference.compute.infer.histogram_us.sum',
    'inference.compute.infer.summary_us.count',
    'inference.compute.infer.summary_us.quantile',
    'inference.compute.infer.summary_us.sum',
    'inference.compute.input.duration_us.count',
    'inference.compute.input.histogram_us.bucket',
    'inference.compute.input.histogram_us.count',
    'inference.compute.input.histogram_us.sum',
    'inference.compute.input.summary_us.count',
    'inference.compute.input.summary_us.quantile',
    'inference.compute.input.summary_us.sum',
    'inference.compute.output.duration_us.count',
    'inference.compute.output.histogram_us.bucket',
    'inference.compute.output.histogram_us.count',
    'inference.compute.output.histogram_us.sum',
    'inference.compute.output.summary_us.count',
    'inference.compute.output.summary_us.quantile',
    'inference.compute.output.summary_us.sum',
    'inference.count.count',
    'inference.exec.count.count',
    'inference.first_response.histogram_ms.bucket',
    'inference.first_response.histogram_ms.count',
    'inference.first_response.histogram_ms.sum',
    'inference.pending.request.count',
    'inference.queue.duration_us.count',
    'inference.queue.histogram_us.bucket',
    'inference.queue.histogram_us.count',
    'inference.queue.histogram_us.sum',
    'inference.queue.summary_us.count',
    'inference.queue.summary_us.quantile',
    'inference.queue.summary_us.sum',
    'inference.request.duration_us.count',
    'inference.request.histogram_us.bucket',
    'inference.request.histogram_us.count',
    'inference.request.histogram_us.sum',
    'inference.request.summary_us.count',
    'inference.request.summary_us.quantile',
    'inference.request.summary_us.sum',
    'inference.request_failure.count',
    'inference.request_success.count',
    'llm.input_token_len.bucket',
    'llm.input_token_len.count',
    'llm.input_token_len.sum',
    'llm.output_token_len.bucket',
    'llm.output_token_len.count',
    'llm.output_token_len.sum',
    'model.load.duration_secs',
    'pinned_memory.pool.total_bytes',
    'pinned_memory.pool.used_bytes',
    'trt_llm.disaggregated_serving_metrics.count',
    'trt_llm.general_metrics',
    'trt_llm.inflight_batcher_metrics',
    'trt_llm.kv_cache_block_metrics',
    'trt_llm.request_metrics',
    'trt_llm.runtime_memory_metrics',
    'trt_llm.v1_metrics',
}

METRICS_MOCK = [f'nvidia_triton.{m}' for m in METRICS_MOCK]
