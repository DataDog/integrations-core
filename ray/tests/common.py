# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.http import MockResponse

HERE = get_here()

RAY_VERSION = os.environ.get("RAY_VERSION")

SERVE_PORT = "8000"
HEAD_METRICS_PORT = "8080"
WORKER1_METRICS_PORT = "8081"
WORKER2_METRICS_PORT = "8082"
WORKER3_METRICS_PORT = "8083"
HEAD_DASHBOARD_PORT = "8265"
HOSTNAME = get_docker_hostname()

HEAD_OPENMETRICS_ENDPOINT = f"http://{HOSTNAME}:{HEAD_METRICS_PORT}"
WORKER1_OPENMETRICS_ENDPOINT = f"http://{HOSTNAME}:{WORKER1_METRICS_PORT}"
WORKER2_OPENMETRICS_ENDPOINT = f"http://{HOSTNAME}:{WORKER2_METRICS_PORT}"
WORKER3_OPENMETRICS_ENDPOINT = f"http://{HOSTNAME}:{WORKER3_METRICS_PORT}"
SERVE_URL = f"http://{HOSTNAME}:{SERVE_PORT}"

HEAD_INSTANCE = {
    "openmetrics_endpoint": HEAD_OPENMETRICS_ENDPOINT,
}

WORKER1_INSTANCE = {
    "openmetrics_endpoint": WORKER1_OPENMETRICS_ENDPOINT,
}

WORKER2_INSTANCE = {
    "openmetrics_endpoint": WORKER2_OPENMETRICS_ENDPOINT,
}

WORKER3_INSTANCE = {
    "openmetrics_endpoint": WORKER3_OPENMETRICS_ENDPOINT,
}

MOCKED_HEAD_INSTANCE = {
    "openmetrics_endpoint": "http://ray-head:8080",
}

MOCKED_WORKER_INSTANCE = {
    "openmetrics_endpoint": "http://ray-worker:8081",
}

E2E_METADATA = {
    'env_vars': {
        'DD_LOGS_ENABLED': 'true',
    },
}

HEAD_METRICS = [
    'actors',
    'cluster.active_nodes',
    'component.cpu_percentage',
    'component.mem_shared',
    'component.rss',
    'component.uss',
    'gcs.actors',
    'gcs.placement_group',
    'gcs.storage_operation.count',
    'gcs.storage_operation.latency.bucket',
    'gcs.storage_operation.latency.count',
    'gcs.storage_operation.latency.sum',
    'gcs.task_manager.task_events.dropped',
    'gcs.task_manager.task_events.reported',
    'gcs.task_manager.task_events.stored',
    'gcs.task_manager.task_events.stored_bytes',
    'grpc_server.req.finished.count',
    'grpc_server.req.handling.count',
    'grpc_server.req.new.count',
    'grpc_server.req.process_time',
    'health_check.rpc_latency.bucket',
    'health_check.rpc_latency.count',
    'health_check.rpc_latency.sum',
    'internal_num.infeasible_scheduling_classes',
    'internal_num.processes.skipped.job_mismatch',
    'internal_num.processes.skipped.runtime_environment_mismatch',
    'internal_num.processes.started',
    'internal_num.processes.started.from_cache',
    'internal_num.spilled_tasks',
    'node.cpu',
    'node.cpu_utilization',
    'node.disk.free',
    'node.disk.io.read',
    'node.disk.io.read.count',
    'node.disk.io.read.speed',
    'node.disk.io.write',
    'node.disk.io.write.count',
    'node.disk.io.write.speed',
    'node.disk.read.iops',
    'node.disk.usage',
    'node.disk.utilization',
    'node.disk.write.iops',
    'node.mem.available',
    'node.mem.shared',
    'node.mem.total',
    'node.mem.used',
    'node.network.receive.speed',
    'node.network.received',
    'node.network.send.speed',
    'node.network.sent',
    'object_directory.added_locations',
    'object_directory.lookups',
    'object_directory.removed_locations',
    'object_directory.subscriptions',
    'object_directory.updates',
    'object_manager.bytes',
    'object_manager.num_pull_requests',
    'object_manager.received_chunks',
    'object_store.available_memory',
    'object_store.fallback_memory',
    'object_store.memory',
    'object_store.num_local_objects',
    'object_store.size.bucket',
    'object_store.size.count',
    'object_store.size.sum',
    'object_store.used_memory',
    'process.cpu_seconds.count',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory',
    'process.start_time',
    'process.virtual_memory',
    'pull_manager.active_bundles',
    'pull_manager.num_object_pins',
    'pull_manager.object_request_time.bucket',
    'pull_manager.object_request_time.count',
    'pull_manager.object_request_time.sum',
    'pull_manager.requested_bundles',
    'pull_manager.requests',
    'pull_manager.retries_total',
    'pull_manager.usage',
    'push_manager.chunks',
    'push_manager.in_flight_pushes',
    'python.gc.collections.count',
    'python.gc.objects_collected.count',
    'python.gc.objects_uncollectable.count',
    'resources',
    'scheduler.failed_worker_startup',
    'scheduler.placement_time.bucket',
    'scheduler.placement_time.count',
    'scheduler.placement_time.sum',
    'scheduler.tasks',
    'scheduler.unscheduleable_tasks',
    'serve.deployment.error',
    'serve.deployment.processing_latency.bucket',
    'serve.deployment.processing_latency.count',
    'serve.deployment.processing_latency.sum',
    'serve.deployment.queued_queries',
    'serve.deployment.replica.healthy',
    'serve.deployment.replica.starts',
    'serve.deployment.request.counter',
    'serve.grpc_request_latency.bucket',
    'serve.grpc_request_latency.count',
    'serve.grpc_request_latency.sum',
    'serve.handle_request',
    'serve.http_request_latency.bucket',
    'serve.http_request_latency.count',
    'serve.http_request_latency.sum',
    'serve.multiplexed_get_model_requests.count',
    'serve.multiplexed_model_load_latency.bucket',
    'serve.multiplexed_model_load_latency.count',
    'serve.multiplexed_model_load_latency.sum',
    'serve.multiplexed_model_unload_latency.bucket',
    'serve.multiplexed_model_unload_latency.count',
    'serve.multiplexed_model_unload_latency.sum',
    'serve.multiplexed_models_load.count',
    'serve.multiplexed_models_unload.count',
    'serve.num_deployment_grpc_error_requests',
    'serve.num_deployment_http_error_requests',
    'serve.num_grpc_error_requests',
    'serve.num_grpc_requests',
    'serve.num_http_error_requests',
    'serve.num_http_requests',
    'serve.num_multiplexed_models',
    'serve.num_router_requests',
    'serve.registered_multiplexed_model_id',
    'serve.replica.pending_queries',
    'serve.replica.processing_queries',
    'server.num_ongoing_grpc_requests',
    'server.num_ongoing_http_requests',
    'server.num_scheduling_tasks',
    'server.num_scheduling_tasks_in_backoff',
    'spill_manager.objects',
    'spill_manager.objects_size',
    'spill_manager.request_total',
    'tasks',
    'unintentional_worker_failures.count',
    'worker.register_time.bucket',
    'worker.register_time.count',
    'worker.register_time.sum',
]
HEAD_METRICS = ['ray.' + m for m in HEAD_METRICS]

WORKER_METRICS = [
    'actors',
    'component.cpu_percentage',
    'component.mem_shared',
    'component.rss',
    'component.uss',
    'grpc_server.req.finished.count',
    'grpc_server.req.handling.count',
    'grpc_server.req.new.count',
    'grpc_server.req.process_time',
    'internal_num.infeasible_scheduling_classes',
    'internal_num.processes.skipped.job_mismatch',
    'internal_num.processes.skipped.runtime_environment_mismatch',
    'internal_num.processes.skipped.runtime_environment_mismatch',
    'internal_num.processes.started',
    'internal_num.processes.started.from_cache',
    'internal_num.spilled_tasks',
    'node.cpu',
    'node.cpu_utilization',
    'node.disk.free',
    'node.disk.io.read',
    'node.disk.io.read.count',
    'node.disk.io.read.speed',
    'node.disk.io.write',
    'node.disk.io.write.count',
    'node.disk.io.write.speed',
    'node.disk.read.iops',
    'node.disk.usage',
    'node.disk.utilization',
    'node.disk.write.iops',
    'node.mem.available',
    'node.mem.shared',
    'node.mem.total',
    'node.mem.used',
    'node.network.receive.speed',
    'node.network.received',
    'node.network.send.speed',
    'node.network.sent',
    'object_directory.added_locations',
    'object_directory.lookups',
    'object_directory.removed_locations',
    'object_directory.subscriptions',
    'object_directory.updates',
    'object_manager.bytes',
    'object_manager.num_pull_requests',
    'object_manager.received_chunks',
    'object_store.available_memory',
    'object_store.fallback_memory',
    'object_store.memory',
    'object_store.num_local_objects',
    'object_store.size.bucket',
    'object_store.size.count',
    'object_store.size.sum',
    'object_store.used_memory',
    'process.cpu_seconds.count',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory',
    'process.start_time',
    'process.virtual_memory',
    'pull_manager.active_bundles',
    'pull_manager.num_object_pins',
    'pull_manager.requested_bundles',
    'pull_manager.requests',
    'pull_manager.retries_total',
    'pull_manager.usage',
    'push_manager.chunks',
    'push_manager.in_flight_pushes',
    'python.gc.collections.count',
    'python.gc.objects_collected.count',
    'python.gc.objects_uncollectable.count',
    'resources',
    'scheduler.failed_worker_startup',
    'scheduler.tasks',
    'scheduler.unscheduleable_tasks',
    'spill_manager.objects',
    'spill_manager.objects_size',
    'spill_manager.request_total',
    'tasks',
    'worker.register_time.bucket',
    'worker.register_time.count',
    'worker.register_time.sum',
]
WORKER_METRICS = ['ray.' + m for m in WORKER_METRICS]

OPTIONAL_METRICS = [
    'actors',
    'object_store.size.bucket',
    'object_store.size.count',
    'object_store.size.sum',
    'pull_manager.object_request_time.bucket',
    'pull_manager.object_request_time.count',
    'pull_manager.object_request_time.count',
    'pull_manager.object_request_time.sum',
    'serve.deployment.error',
    'serve.grpc_request_latency.bucket',
    'serve.grpc_request_latency.count',
    'serve.grpc_request_latency.sum',
    'serve.multiplexed_get_model_requests.count',
    'serve.multiplexed_model_load_latency.bucket',
    'serve.multiplexed_model_load_latency.count',
    'serve.multiplexed_model_load_latency.sum',
    'serve.multiplexed_model_unload_latency.bucket',
    'serve.multiplexed_model_unload_latency.count',
    'serve.multiplexed_model_unload_latency.sum',
    'serve.multiplexed_models_load.count',
    'serve.multiplexed_models_unload.count',
    'serve.num_deployment_grpc_error_requests',
    'serve.num_deployment_http_error_requests',
    'serve.num_grpc_error_requests',
    'serve.num_grpc_requests',
    'serve.num_multiplexed_models',
    'serve.registered_multiplexed_model_id',
    'server.num_ongoing_grpc_requests',
    'tasks',
    'worker.register_time.bucket',
    'worker.register_time.count',
    'worker.register_time.sum',
]
OPTIONAL_METRICS = ['ray.' + m for m in OPTIONAL_METRICS]


def mock_http_responses(url, **_params):
    mapping = {
        'http://ray-head:8080': 'ray_head.txt',
        'http://ray-worker:8081': 'ray_worker.txt',
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        raise Exception(f"url `{url}` not registered")

    with open(os.path.join(HERE, 'fixtures', metrics_file)) as f:
        return MockResponse(content=f.read())
