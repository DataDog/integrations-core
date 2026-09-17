# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
FRONTEND_PORT = 8000
WORKER_PORT = 8081


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_FRONTEND_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{FRONTEND_PORT}/metrics",
    "tags": ['test:test'],
}

MOCKED_WORKER_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{WORKER_PORT}/metrics",
    "tags": ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

FRONTEND_METRICS_MOCK = [
    'frontend.requests.count',
    'frontend.requests_started.count',
    'frontend.queued_requests',
    'frontend.inflight_requests',
    'frontend.active_requests',
    'frontend.disconnected_clients',
    'frontend.output_tokens.count',
    'frontend.kv_hit_rate',
    'frontend.shared_cache_hit_rate',
    'frontend.shared_cache_beyond_blocks',
    'frontend.non_max_overlap_selections.count',
    'frontend.overlap_blocks_lost',
    'frontend.model.total_kv_blocks',
    'frontend.model.max_num_seqs',
    'frontend.model.max_num_batched_tokens',
    'frontend.model.context_length',
    'frontend.model.kv_cache_block_size',
    'frontend.model.migration_limit',
    'frontend.model.migration.count',
    'frontend.model.migration_max_seq_len_exceeded.count',
    'frontend.model.cancellation.count',
    'frontend.model.rejection.count',
    'frontend.worker.active_decode_blocks',
    'frontend.worker.active_prefill_tokens',
    'frontend.worker.last_time_to_first_token_seconds',
    'frontend.worker.last_input_sequence_tokens',
    'frontend.worker.last_inter_token_latency_seconds',
    'frontend.router_queue_pending_requests',
    'frontend.lora.replica_factor',
    'frontend.lora.is_active',
    'frontend.lora.estimated_load',
    'frontend.lora.raw_arrival_count',
    'frontend.lora.active_requests',
    'frontend.lora.churn_loads.count',
    'frontend.lora.churn_unloads.count',
    'frontend.lora.overflow_count',
]

WORKER_METRICS_MOCK = [
    'component.requests.count',
    'component.request_bytes.count',
    'component.response_bytes.count',
    'component.inflight_requests',
    'component.errors.count',
    'component.cancellation.count',
    'component.queue_depth',
    'component.queue_capacity',
    'component.enqueue_rejected.count',
    'component.pool_active_tasks',
    'component.pool_capacity',
    'component.uptime_seconds',
    'component.tasks_issued.count',
    'component.tasks_started.count',
    'component.tasks_success.count',
    'component.tasks_cancelled.count',
    'component.tasks_failed.count',
    'component.tasks_rejected.count',
    'component.kv_cache.total_blocks',
    'component.kv_cache.gpu_cache_usage_percent',
    'component.kv_cache.hit_rate',
    'component.kv_cache.events_applied.count',
    'component.router.requests.count',
    'component.router.requests_started.count',
    'component.router.non_max_overlap_selections.count',
    'rejection.requests.count',
]


# Histograms are submitted as distributions (histogram_buckets_as_distributions=True), so the Agent
# records them as histogram buckets under the base metric name rather than as regular `.bucket` metrics.
FRONTEND_HISTOGRAM_BUCKETS_MOCK = [
    'frontend.request_duration.seconds',
    'frontend.input_sequence_tokens',
    'frontend.output_sequence_tokens',
    'frontend.tokenizer_latency_ms',
    'frontend.images_per_request',
    'frontend.videos_per_request',
    'frontend.audio_per_request',
    'frontend.image_tokens_per_request',
    'frontend.time_to_first_token.seconds',
    'frontend.inter_token_latency.seconds',
    'frontend.embedding_latency.seconds',
    'frontend.kv_transfer_estimated_latency.seconds',
    'frontend.cached_tokens',
    'router.overhead.block_hashing_ms',
    'router.overhead.indexer_find_matches_ms',
    'router.overhead.seq_hashing_ms',
    'router.overhead.scheduling_ms',
    'router.overhead.total_ms',
]

WORKER_HISTOGRAM_BUCKETS_MOCK = [
    'component.request_duration.seconds',
    'component.network_transit.seconds',
    'component.time_to_first_response.seconds',
    'component.permit_wait.seconds',
    'component.router.time_to_first_token.seconds',
    'component.router.inter_token_latency.seconds',
    'component.router.input_sequence_tokens',
    'component.router.output_sequence_tokens',
    'component.router.kv_hit_rate',
    'component.router.overlap_blocks_lost',
]

FRONTEND_METRICS_MOCK.extend(
    f'{metric}.{suffix}' for metric in FRONTEND_HISTOGRAM_BUCKETS_MOCK for suffix in ('count', 'sum')
)
WORKER_METRICS_MOCK.extend(
    f'{metric}.{suffix}' for metric in WORKER_HISTOGRAM_BUCKETS_MOCK for suffix in ('count', 'sum')
)

FRONTEND_METRICS_MOCK = [f'dynamo.{m}' for m in FRONTEND_METRICS_MOCK]
WORKER_METRICS_MOCK = [f'dynamo.{m}' for m in WORKER_METRICS_MOCK]
FRONTEND_HISTOGRAM_BUCKETS_MOCK = [f'dynamo.{m}' for m in FRONTEND_HISTOGRAM_BUCKETS_MOCK]
WORKER_HISTOGRAM_BUCKETS_MOCK = [f'dynamo.{m}' for m in WORKER_HISTOGRAM_BUCKETS_MOCK]
