# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.gitlab import GitlabCheck

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()

GITLAB_TEST_PASSWORD = 'hdkss33jdijb123'
GITLAB_TEST_API_TOKEN = 'token'
GITLAB_LOCAL_PORT = 8086
GITLAB_LOCAL_PROMETHEUS_PORT = 8088
GITLAB_LOCAL_GITALY_PROMETHEUS_PORT = 8089

PROMETHEUS_ENDPOINT = "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_PROMETHEUS_PORT)
GITLAB_PROMETHEUS_ENDPOINT = "http://{}:{}/-/metrics".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_READINESS_ENDPOINT = "http://{}:{}/-/readiness".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_LIVENESS_ENDPOINT = "http://{}:{}/-/liveness".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_HEALTH_ENDPOINT = "http://{}:{}/-/health".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_GITALY_PROMETHEUS_ENDPOINT = "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_GITALY_PROMETHEUS_PORT)
GITLAB_URL = "http://{}:{}".format(HOST, GITLAB_LOCAL_PORT)
GITLAB_TAGS = ['gitlab_host:{}'.format(HOST), 'gitlab_port:{}'.format(GITLAB_LOCAL_PORT)]

CUSTOM_TAGS = ['optional:tag1']

# Note that this is a subset of the ones defined in GitlabCheck
# When we stand up a clean test infrastructure some of those metrics might not
# be available yet, hence we validate a stable subset
ALLOWED_METRICS = [
    'process_max_fds',
    'process_open_fds',
    'process_resident_memory_bytes',
    'process_start_time_seconds',
    'process_virtual_memory_bytes',
]

COMMON_METRICS = [
    "banzai.cacheless_render_real_duration_seconds.count",
    "banzai.cacheless_render_real_duration_seconds.sum",
    "cache.operation_duration_seconds.count",
    "cache.operation_duration_seconds.sum",
    "rails_queue_duration_seconds.count",
    "rails_queue_duration_seconds.sum",
    "transaction.allocated_memory_bytes.count",
    "transaction.allocated_memory_bytes.sum",
    "transaction.duration_seconds.count",
    "transaction.duration_seconds.sum",
    "rack.http_request_duration_seconds.sum",
    "rack.http_request_duration_seconds.count",
    "ruby.file_descriptors",
    "ruby.memory_bytes",
    "ruby.process_max_fds",
    "ruby.process_resident_memory_bytes",
    "ruby.process_start_time_seconds",
    "ruby.gc_duration_seconds.count",
    "ruby.gc_duration_seconds.sum",
    "sql_duration_seconds.count",
    "sql_duration_seconds.sum",
    "ruby.gc_stat.heap_allocated_pages",
    "ruby.gc_stat.heap_sorted_length",
    "ruby.gc_stat.heap_allocatable_pages",
    "ruby.gc_stat.heap_available_slots",
    "ruby.gc_stat.heap_live_slots",
    "ruby.gc_stat.heap_free_slots",
    "ruby.gc_stat.heap_final_slots",
    "ruby.gc_stat.heap_marked_slots",
    "ruby.gc_stat.heap_eden_pages",
    "ruby.gc_stat.heap_tomb_pages",
    "ruby.gc_stat.total_allocated_pages",
    "ruby.gc_stat.total_freed_objects",
    "ruby.gc_stat.total_freed_pages",
    "ruby.gc_stat.total_allocated_objects",
    "ruby.gc_stat.malloc_increase_bytes",
    "ruby.gc_stat.malloc_increase_bytes_limit",
    "ruby.gc_stat.minor_gc_count",
    "ruby.gc_stat.major_gc_count",
    "ruby.gc_stat.remembered_wb_unprotected_objects",
    "ruby.gc_stat.remembered_wb_unprotected_objects_limit",
    "ruby.gc_stat.old_objects",
    "ruby.gc_stat.old_objects_limit",
    "ruby.gc_stat.oldmalloc_increase_bytes",
    "ruby.gc_stat.oldmalloc_increase_bytes_limit",
    "unicorn.active_connections",
    "unicorn.queued_connections",
    "unicorn.workers",
    "action_cable.active_connections",
    "database.connection_pool_busy",
    "database.connection_pool_connections",
    "database.connection_pool_dead",
    "database.connection_pool_idle",
    "database.connection_pool_size",
    "database.connection_pool_waiting",
    "db_load_balancing_hosts",
    "puma.active_connections",
    "puma.idle_threads",
    "puma.max_threads",
    "puma.pool_capacity",
    "puma.queued_connections",
    "puma.running",
    "puma.running_workers",
    "puma.stale_workers",
    "puma.workers",
    "redis.client_requests_duration_seconds.count",
    "redis.client_requests_duration_seconds.sum",
    "ruby.process_proportional_memory_bytes",
    "ruby.process_unique_memory_bytes",
    "ruby.threads_max_expected_threads",
    "ruby.threads_running_threads",
    "transaction.rails_queue_duration_total",
    "ruby.process_cpu_seconds_total",
    "geo.group.wiki.repositories",
    "geo.group.wiki.repositories_checksum_total",
    "geo.group.wiki.repositories_checksummed",
    "geo.group.wiki.repositories_checksum_failed",
    "geo.group.wiki.repositories_failed",
    "geo.group.wiki.repositories_registry",
    "geo.group.wiki.repositories_synced",
    "geo.group.wiki.repositories_verification_failed",
    "geo.group.wiki.repositories_verified",
    "geo.group.wiki.repositories_verification_total",
    "geo.project.repositories",
    "geo.project.repositories_checksum_total",
    "geo.project.repositories_checksummed",
    "geo.project.repositories_checksum_failed",
    "geo.project.repositories_failed",
    "geo.project.repositories_registry",
    "geo.project.repositories_synced",
    "geo.project.repositories_verification_failed",
    "geo.project.repositories_verified",
    "geo.project.repositories_verification_total",
    "geo.project.wiki.repositories",
    "geo.project.wiki.repositories_checksum_total",
    "geo.project.wiki.repositories_checksummed",
    "geo.project.wiki.repositories_checksum_failed",
    "geo.project.wiki.repositories_failed",
    "geo.project.wiki.repositories_registry",
    "geo.project.wiki.repositories_synced",
    "geo.project.wiki.repositories_verification_failed",
    "geo.project.wiki.repositories_verified",
    "geo.project.wiki.repositories_verification_total",
]

V1_METRICS = COMMON_METRICS + [
    "cache.misses_total",
    "cache_operations_total",
    "job.waiter_started_total",
    "job.waiter_timeouts_total",
    "transaction.cache_read_hit_count_total",
    "transaction.cache_read_miss_count_total",
    "transaction.new_redis_connections_total",
    "transaction.view_duration_total",
    "rack.http_requests_total",
    "ruby.sampler_duration_seconds_total",
    "ruby.gc_stat.count",
    "redis.client_requests_total",
]

V2_METRICS = COMMON_METRICS + [
    "ruby.gc_stat",
    "banzai.cacheless_render_real_duration_seconds.bucket",
    "cache.misses.count",
    "cache.operation_duration_seconds.bucket",
    "cache_operations.count",
    "job.waiter_started.count",
    "job.waiter_timeouts.count",
    "rack.http_request_duration_seconds.bucket",
    "rack.http_requests.count",
    "rails_queue_duration_seconds.bucket",
    "ruby.gc_duration_seconds.bucket",
    "ruby.sampler_duration_seconds.count",
    "sql_duration_seconds.bucket",
    "transaction.allocated_memory_bytes.bucket",
    "transaction.cache_read_hit_count.count",
    "transaction.cache_read_miss_count.count",
    "transaction.duration_seconds.bucket",
    "transaction.new_redis_connections.count",
    "transaction.view_duration.count",
    "redis.client_requests.count",
    "redis.client_requests_duration_seconds.bucket",
]

GITALY_METRICS = [
    "gitaly.cacheinvalidator_rpc.count",
    "gitaly.catfile_cache_members",
    "gitaly.catfile_processes",
    "gitaly.command.context_switches.count",
    "gitaly.command.cpu_seconds.count",
    "gitaly.command.major_page_faults.count",
    "gitaly.command.minor_page_faults.count",
    "gitaly.command.real_seconds.count",
    "gitaly.command.signals_received.count",
    "gitaly.command.spawn_token_acquiring_seconds.count",
    "gitaly.commands_running",
    "gitaly.concurrency_limiting_acquiring_seconds.bucket",
    "gitaly.concurrency_limiting_acquiring_seconds.count",
    "gitaly.concurrency_limiting_acquiring_seconds.sum",
    "gitaly.concurrency_limiting_in_progress",
    "gitaly.concurrency_limiting_queued",
    "gitaly.diskcache.bytes_fetched.count",
    "gitaly.diskcache.bytes_loser.count",
    "gitaly.diskcache.bytes_stored.count",
    "gitaly.diskcache.miss.count",
    "gitaly.diskcache.requests.count",
    "gitaly.diskcache.walker_empty_dir.count",
    "gitaly.diskcache.walker_empty_dir_removal.count",
    "gitaly.diskcache.walker_error.count",
    "gitaly.diskcache.walker_removal.count",
    "gitaly.go.gc_duration_seconds.count",
    "gitaly.go.gc_duration_seconds.quantile",
    "gitaly.go.gc_duration_seconds.sum",
    "gitaly.go.goroutines",
    "gitaly.go.info",
    "gitaly.go.memstats_alloc_bytes",
    "gitaly.go.memstats_buck_hash_sys_bytes",
    "gitaly.go.memstats_frees.count",
    "gitaly.go.memstats_gc_sys_bytes",
    "gitaly.go.memstats_heap_alloc_bytes",
    "gitaly.go.memstats_heap_idle_bytes",
    "gitaly.go.memstats_heap_inuse_bytes",
    "gitaly.go.memstats_heap_objects",
    "gitaly.go.memstats_heap_released_bytes",
    "gitaly.go.memstats_heap_sys_bytes",
    "gitaly.go.memstats_last_gc_time_seconds",
    "gitaly.go.memstats_lookups.count",
    "gitaly.go.memstats_mallocs.count",
    "gitaly.go.memstats_mcache_inuse_bytes",
    "gitaly.go.memstats_mcache_sys_bytes",
    "gitaly.go.memstats_mspan_inuse_bytes",
    "gitaly.go.memstats_mspan_sys_bytes",
    "gitaly.go.memstats_next_gc_bytes",
    "gitaly.go.memstats_other_sys_bytes",
    "gitaly.go.memstats_stack_inuse_bytes",
    "gitaly.go.memstats_stack_sys_bytes",
    "gitaly.go.memstats_sys_bytes",
    "gitaly.go.threads",
    "gitaly.grpc_server.handled.count",
    "gitaly.grpc_server.handling_seconds.bucket",
    "gitaly.grpc_server.handling_seconds.count",
    "gitaly.grpc_server.handling_seconds.sum",
    "gitaly.grpc_server.msg_received.count",
    "gitaly.grpc_server.msg_sent.count",
    "gitaly.grpc_server.started.count",
    "gitaly.hook_transaction_voting_delay_seconds.bucket",
    "gitaly.hook_transaction_voting_delay_seconds.count",
    "gitaly.hook_transaction_voting_delay_seconds.sum",
    "gitaly.inforef_cache_attempt.count",
    "gitaly.list_commits_by_oid_request_size.bucket",
    "gitaly.list_commits_by_oid_request_size.count",
    "gitaly.list_commits_by_oid_request_size.sum",
    "gitaly.pack_objects.acquiring_seconds.bucket",
    "gitaly.pack_objects.acquiring_seconds.count",
    "gitaly.pack_objects.acquiring_seconds.sum",
    "gitaly.pack_objects.generated_bytes.count",
    "gitaly.pack_objects.in_progress",
    "gitaly.pack_objects.queued",
    "gitaly.pack_objects.served_bytes.count",
    "gitaly.process_cpu_seconds.count",
    "gitaly.process_max_fds",
    "gitaly.process_open_fds",
    "gitaly.process_resident_memory_bytes",
    "gitaly.process_start_time_seconds",
    "gitaly.process_virtual_memory_bytes",
    "gitaly.process_virtual_memory_max_bytes",
    "gitaly.promhttp_metric_handler_requests.count",
    "gitaly.promhttp_metric_handler_requests_in_flight",
    "gitaly.spawn_timeouts.count",
    "gitaly.streamcache_sendfile_bytes.count",
]

METRICS_TO_TEST = [
    "puma.workers",
    "rack.http_requests_total",
    "ruby.process_start_time_seconds",
    "rack.http_request_duration_seconds.sum",
    "sql_duration_seconds.sum",
]

METRICS_TO_TEST_V2 = [
    "puma.workers",
    "rack.http_requests.count",
    "ruby.process_start_time_seconds",
    "rack.http_request_duration_seconds.sum",
    "sql_duration_seconds.sum",
]

GITALY_METRICS_TO_TEST = [
    "gitaly.process_max_fds",
]


def assert_check(aggregator, metrics=None, use_openmetrics=False):
    """
    Basic Test for gitlab integration.
    """
    # Make sure we're receiving gitlab service checks

    if not metrics:
        metrics = []

    for service_check in GitlabCheck.ALLOWED_SERVICE_CHECKS:
        aggregator.assert_service_check(
            'gitlab.{}'.format(service_check), status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS
        )

    # Make sure we're receiving prometheus service checks
    if use_openmetrics:
        from datadog_checks.gitlab.gitlab_v2 import GitlabCheckV2

        aggregator.assert_service_check(
            'gitlab.openmetrics.health',
            status=GitlabCheckV2.OK,
            tags=GITLAB_TAGS + CUSTOM_TAGS + ['endpoint:{}'.format(GITLAB_PROMETHEUS_ENDPOINT)],
        )

        for readiness_service_check in GitlabCheckV2.READINESS_SERVICE_CHECKS.values():
            aggregator.assert_service_check(
                'gitlab.readiness.{}'.format(readiness_service_check), tags=GITLAB_TAGS + CUSTOM_TAGS
            )
    else:
        aggregator.assert_service_check(
            GitlabCheck.PROMETHEUS_SERVICE_CHECK_NAME, status=GitlabCheck.OK, tags=GITLAB_TAGS + CUSTOM_TAGS
        )

    for metric in metrics:
        aggregator.assert_metric("gitlab.{}".format(metric))

    # Assert that we have at least one of them
    assert len(aggregator.metric_names) > 1
