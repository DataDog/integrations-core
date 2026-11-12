# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
ROUTER_PORT = 9090
SIDECAR_PORT = 9091
COORDINATOR_PORT = 9092
LEGACY_ROUTER_PORT = 9093


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


def instance_for(port):
    return {'openmetrics_endpoint': f'http://{HOST}:{port}/metrics', 'tags': ['test:test']}


MOCKED_ROUTER_INSTANCE = instance_for(ROUTER_PORT)
MOCKED_SIDECAR_INSTANCE = instance_for(SIDECAR_PORT)
MOCKED_COORDINATOR_INSTANCE = instance_for(COORDINATOR_PORT)
MOCKED_LEGACY_ROUTER_INSTANCE = instance_for(LEGACY_ROUTER_PORT)

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

ROUTER_METRICS = [
    'epp.request.count',
    'epp.request.error.count',
    'epp.request.outcome.count',
    'epp.request.running',
    'epp.pool.average_kv_cache_utilization',
    'epp.pool.average_queue_size',
    'epp.pool.average_running_requests',
    'epp.pool.std_dev_kv_cache_utilization',
    'epp.pool.std_dev_queue_size',
    'epp.pool.std_dev_running_requests',
    'epp.pool.ready_endpoints',
    'epp.endpoint.queue_size',
    'epp.endpoint.nixl.failed_transfers.count',
    'epp.endpoint.nixl.failed_notifications.count',
    'epp.endpoint.nixl.kv_expired_requests.count',
    'epp.scheduler.attempts.count',
    'epp.scheduler.failures.count',
    'epp.info',
    'epp.disagg_decision.count',
    'epp.prefix_indexer.size',
    'epp.kv_cache_index.admissions.count',
    'epp.kv_cache_index.evictions.count',
    'epp.kv_cache_index.lookup_requests.count',
    'epp.kv_cache_index.lookup_hits.count',
    'epp.kv_cache_index.max_pod_hit_count.count',
    'epp.kv_cache_events.dedup_removed_hashes_suppressed.count',
    'epp.kv_cache_events.dedup_removed_hashes_forwarded.count',
    'epp.kv_cache_events.stores_skipped.count',
    'epp.kv_cache_events.removals_skipped.count',
    'epp.kv_cache_events.active_subscribers',
    'epp.kv_cache_events.subscriber_reconnections.count',
    'epp.kv_cache_events.messages_received.count',
    'epp.kv_cache_events.zmq_errors.count',
    'epp.kv_cache_events.pool_queue_depth',
    'epp.kv_cache_events.pool_capacity',
    'epp.flow_control.queue_size',
    'epp.flow_control.queue_bytes',
    'epp.flow_control.pool_saturation',
    'epp.flow_control.stale_endpoints',
    'epp.flow_control.detector_saturation',
    'epp.flow_control.capacity_utilization_requests',
    'epp.flow_control.capacity_utilization_bytes',
    'epp.flow_control.global_capacity_utilization_requests',
    'epp.flow_control.global_capacity_utilization_bytes',
    'epp.flow_control.requests.count',
    'epp.flow_control.revocations_issued.count',
    'epp.flow_control.revocations.count',
    'epp.flow_control.reclaim_target',
    'epp.flow_control.pending_reclaim',
    'epp.inflight.requests',
    'epp.inflight.tokens',
    'epp.datalayer.poll_errors.count',
    'epp.datalayer.extract_errors.count',
    'epp.datalayer.polls.count',
    'epp.extproc.streams_inflight',
    'epp.extproc.streams.count',
    'epp.endpoint_health.excluded_endpoints',
    'epp.endpoint_health.ejections.count',
    'epp.endpoint_health.readmissions.count',
    'epp.endpoint_health.fail_open.count',
]

ROUTER_HISTOGRAMS = [
    'epp.request.duration.seconds',
    'epp.request.ttft.seconds',
    'epp.request.ntpot.seconds',
    'epp.request.streaming_tpot.seconds',
    'epp.request.streaming_itl.seconds',
    'epp.request.input_tokens',
    'epp.request.output_tokens',
    'epp.request.cached_tokens',
    'epp.request.size.bytes',
    'epp.response.size.bytes',
    'epp.scheduler.e2e_duration.seconds',
    'epp.plugin.duration.seconds',
    'epp.prefix_indexer.hit_ratio',
    'epp.prefix_indexer.hit_bytes',
    'epp.prefix.predicted_cached_tokens',
    'epp.kv_cache_index.lookup_latency.seconds',
    'epp.flow_control.request_queue_duration.seconds',
    'epp.flow_control.dispatch_cycle_duration.seconds',
    'epp.flow_control.request_enqueue_duration.seconds',
    'epp.flow_control.revocation_confirmation.seconds',
    'epp.datalayer.poll_duration.seconds',
    'epp.extproc.stream_duration.seconds',
]

# Legacy names land on the same Datadog metrics as their llm_d_epp_* replacements.
LEGACY_ROUTER_METRICS = [
    'epp.request.count',
    'epp.request.error.count',
    'epp.request.running',
    'epp.pool.average_kv_cache_utilization',
    'epp.pool.average_queue_size',
    'epp.pool.average_running_requests',
    'epp.pool.ready_endpoints',
    'epp.endpoint.queue_size',
    'epp.scheduler.attempts.count',
    'epp.info',
    'epp.flow_control.queue_size',
    'epp.flow_control.queue_bytes',
    'epp.flow_control.pool_saturation',
    'epp.prefix_indexer.size',
    'epp.disagg_decision.count',
    'epp.datalayer.poll_errors.count',
    'epp.datalayer.extract_errors.count',
    'epp.kv_cache_index.admissions.count',
    'epp.kv_cache_index.evictions.count',
    'epp.kv_cache_index.lookup_requests.count',
    'epp.kv_cache_index.lookup_hits.count',
    'epp.kv_cache_index.max_pod_hit_count.count',
    'epp.kv_cache_events.dedup_removed_hashes_suppressed.count',
    'epp.kv_cache_events.dedup_removed_hashes_forwarded.count',
]

LEGACY_ROUTER_HISTOGRAMS = [
    'epp.request.duration.seconds',
    'epp.request.ttft.seconds',
    'epp.request.streaming_tpot.seconds',
    'epp.request.ntpot.seconds',
    'epp.request.input_tokens',
    'epp.request.output_tokens',
    'epp.request.cached_tokens',
    'epp.request.size.bytes',
    'epp.response.size.bytes',
    'epp.scheduler.e2e_duration.seconds',
    'epp.plugin.duration.seconds',
    'epp.flow_control.request_queue_duration.seconds',
    'epp.flow_control.dispatch_cycle_duration.seconds',
    'epp.flow_control.request_enqueue_duration.seconds',
    'epp.prefix_indexer.hit_ratio',
    'epp.prefix_indexer.hit_bytes',
    'epp.kv_cache_index.lookup_latency.seconds',
]

SIDECAR_METRICS = [
    'sidecar.requests.count',
    'sidecar.disagg_requests.count',
    'sidecar.request_errors.count',
    'sidecar.info',
]

SIDECAR_HISTOGRAMS = [
    'sidecar.encode_duration.seconds',
    'sidecar.prefill_duration.seconds',
    'sidecar.decode_duration.seconds',
]

COORDINATOR_METRICS = [
    'coordinator.info',
    'coordinator.request.count',
    'coordinator.request.error.count',
    'coordinator.request.running',
    'coordinator.step.errors.count',
    'coordinator.step.running',
    'coordinator.upstream.request.count',
    'coordinator.execution_path.count',
    'coordinator.conditional_decode_probes.count',
    'coordinator.force_stream.buffered_bytes',
    'coordinator.force_stream.count',
    'coordinator.prompt_token_mismatch.count',
]

COORDINATOR_HISTOGRAMS = [
    'coordinator.request.duration.seconds',
    'coordinator.request.size.bytes',
    'coordinator.request.input_tokens',
    'coordinator.response.size.bytes',
    'coordinator.step.duration.seconds',
    'coordinator.upstream.request.duration.seconds',
    'coordinator.encode_subrequests',
    'coordinator.orchestration_overhead.seconds',
    'coordinator.media_items',
    'coordinator.media_download_duration.seconds',
]


def with_histogram_counters(metrics, histograms):
    # Histograms are submitted as distributions under the base metric name, plus `.count` and `.sum`.
    expanded = metrics + [f'{metric}.{suffix}' for metric in histograms for suffix in ('count', 'sum')]
    return [f'llm_d.{metric}' for metric in expanded]


ROUTER_METRICS = with_histogram_counters(ROUTER_METRICS, ROUTER_HISTOGRAMS)
LEGACY_ROUTER_METRICS = with_histogram_counters(LEGACY_ROUTER_METRICS, LEGACY_ROUTER_HISTOGRAMS)
SIDECAR_METRICS = with_histogram_counters(SIDECAR_METRICS, SIDECAR_HISTOGRAMS)
COORDINATOR_METRICS = with_histogram_counters(COORDINATOR_METRICS, COORDINATOR_HISTOGRAMS)
ROUTER_HISTOGRAMS = [f'llm_d.{metric}' for metric in ROUTER_HISTOGRAMS]
LEGACY_ROUTER_HISTOGRAMS = [f'llm_d.{metric}' for metric in LEGACY_ROUTER_HISTOGRAMS]
SIDECAR_HISTOGRAMS = [f'llm_d.{metric}' for metric in SIDECAR_HISTOGRAMS]
COORDINATOR_HISTOGRAMS = [f'llm_d.{metric}' for metric in COORDINATOR_HISTOGRAMS]
