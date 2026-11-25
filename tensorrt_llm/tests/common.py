# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8000

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


INSTANCE = {'openmetrics_endpoint': f'http://{HOST}:{PORT}/prometheus/metrics', 'tags': ['test:test']}

# Emitted by trtllm-serve 1.3.0 (fixture: live dump, Qwen3-0.6B, enable_iter_perf_stats).
_METRICS_1_3_0 = [
    'batch.avg_decoded_tokens_per_iter',
    'batch.context_tokens',
    'batch.max_num_tokens_runtime',
    'batch.max_size_runtime',
    'batch.max_size_static',
    'batch.prefill_occupancy',
    'batch.prefill_tokens.count',
    'batch.prefill_tokens.sum',
    'e2e_request_latency.seconds.count',
    'e2e_request_latency.seconds.sum',
    'generation_tokens.count',
    'iteration.latency.seconds',
    'kv_cache.free_blocks',
    'kv_cache.gen_alloc_blocks.count',
    'kv_cache.hit_rate',
    'kv_cache.intra_device_copy_bytes.count',
    'kv_cache.iter.full_reused_blocks.count',
    'kv_cache.iter.missed_blocks.count',
    'kv_cache.iter.partial_reused_blocks.count',
    'kv_cache.iter.reuse_rate',
    'kv_cache.iter.reused_blocks.count',
    'kv_cache.max_blocks',
    'kv_cache.missed_blocks.count',
    'kv_cache.reused_blocks.count',
    'kv_cache.tokens_per_block',
    'kv_cache.used_blocks',
    'kv_cache.usage',
    'kv_cache_config_info',
    'memory.cpu_usage_bytes',
    'memory.gpu_usage_bytes',
    'memory.pinned_usage_bytes',
    'model_config_info',
    'num_requests.completed.count',
    'num_requests.context',
    'num_requests.generation',
    'num_requests.max_active',
    'num_requests.paused',
    'num_requests.running',
    'num_requests.scheduled',
    'num_requests.waiting',
    'parallel_config_info',
    'prompt_tokens.cached.count',
    'prompt_tokens.cached_per_request.count',
    'prompt_tokens.cached_per_request.sum',
    'prompt_tokens.count',
    'request.decode_time.seconds.count',
    'request.decode_time.seconds.sum',
    'request.inference_time.seconds.count',
    'request.inference_time.seconds.sum',
    'request.prefill_time.seconds.count',
    'request.prefill_time.seconds.sum',
    'request.queue_time.seconds.count',
    'request.queue_time.seconds.sum',
    'request.success.count',
    'request.time_per_output_token.seconds.count',
    'request.time_per_output_token.seconds.sum',
    'time_to_first_token.seconds.count',
    'time_to_first_token.seconds.sum',
]

# Added by trtllm-serve 1.4.0rc4 (fixture: live dump with a host KV cache tier and n-gram speculative decoding).
_METRICS_1_4_0RC4_ADDED = [
    'disaggregation.gen_deferred_receives',
    'kv_cache.host_slab_bytes',
    'kv_cache.host_usage',
    'kv_cache.offload_bytes.count',
    'prompt_tokens.cache_hit.count',
    'request.error.count',
    'spec_decode.accept_length',
    'spec_decode.num_accepted_tokens_per_pos.count',
    'spec_decode.draft_overhead',
    'spec_decode.num_drafted_tokens_per_pos.count',
    'spec_decode.num_accepted_tokens.count',
    'spec_decode.num_draft_tokens.count',
    'speculative_config_info',
]

# Conditional families (fixture: hand-written from the collector source).
_CONDITIONAL_METRICS = [
    'disaggregation.gen_init_holds.count',
    'disaggregation.gen_receive_ready_wait_seconds.count',
    'input_processing.queue_seconds.count',
    'input_processing.queue_seconds.sum',
    'input_processing.seconds.count',
    'input_processing.seconds.sum',
    'kv_cache.disk_prefetch_blocks.count',
    'kv_cache.iter.connector_reused_blocks.count',
    'kv_cache.onboard_bytes.count',
    'kv_cache.page_table.conversions.count',
    'kv_cache.page_table.full_build_seconds.count',
    'media_processing.seconds.count',
    'media_processing.seconds.sum',
    'multimodal_encoder.gpu_time_seconds.count',
    'multimodal_encoder.gpu_time_seconds.sum',
    'perplexity.generation.count',
    'perplexity.generation.sum',
    'perplexity.prefill.count',
    'perplexity.prefill.sum',
    'scheduler.ctx_chunks_reverted.count',
    'scheduler.ctx_decoder_held_requests.count',
    'scheduler.ctx_decoder_hold_passes.count',
    'scheduler.ctx_tokens_reverted.count',
]

_HISTOGRAMS = [
    'batch.prefill_tokens',
    'e2e_request_latency.seconds',
    'prompt_tokens.cached_per_request',
    'request.decode_time.seconds',
    'request.inference_time.seconds',
    'request.prefill_time.seconds',
    'request.queue_time.seconds',
    'request.time_per_output_token.seconds',
    'time_to_first_token.seconds',
]

_CONDITIONAL_HISTOGRAMS = [
    'input_processing.queue_seconds',
    'input_processing.seconds',
    'media_processing.seconds',
    'multimodal_encoder.gpu_time_seconds',
    'perplexity.generation',
    'perplexity.prefill',
]


def namespaced(metrics):
    return [f'tensorrt_llm.{m}' for m in metrics]


METRICS_1_3_0 = namespaced(_METRICS_1_3_0)
METRICS_1_4_0RC4 = METRICS_1_3_0 + namespaced(_METRICS_1_4_0RC4_ADDED)
CONDITIONAL_METRICS = namespaced(_CONDITIONAL_METRICS)
HISTOGRAMS = namespaced(_HISTOGRAMS)
CONDITIONAL_HISTOGRAMS = namespaced(_CONDITIONAL_HISTOGRAMS)
