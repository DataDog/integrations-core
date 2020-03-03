# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))

# Networking
HOST = get_docker_hostname()

GITLAB_TEST_PASSWORD = "testroot"
GITLAB_LOCAL_PORT = 8086
GITLAB_LOCAL_PROMETHEUS_PORT = 8088

PROMETHEUS_ENDPOINT = "http://{}:{}/metrics".format(HOST, GITLAB_LOCAL_PROMETHEUS_PORT)
GITLAB_PROMETHEUS_ENDPOINT = "http://{}:{}/-/metrics".format(HOST, GITLAB_LOCAL_PORT)
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

METRICS_TO_TEST = [
    "transaction.new_redis_connections_total",
    "transaction.queue_duration_total",
    "transaction.rails_queue_duration_total",
    "transaction.view_duration_total",
    "transaction.view_duration_total.sum",
    "view_rendering_duration_seconds.count",
    "view_rendering_duration_seconds_sum",
    "http_requests_total",
    "http_request_duration_seconds.sum",
    "http_request_duration_seconds.count",
    "pipelines_created_total",
    "rack_uncaught_errors_total",
    "user_session_logins_total",
    "upload_file_does_not_exist",
    "failed_login_captcha_total",
]

METRICS = [
    "banzai.cacheless_render_real_duration_seconds.count",
    "banzai.cacheless_render_real_duration_seconds.sum",
    "cache.misses_total",
    "cache.operation_duration_seconds.count",
    "cache.operation_duration_seconds.sum",
    "cache_operations_total",
    "method_call_duration_seconds.count",
    "method_call_duration_seconds.sum",
    "page_out_of_bounds",
    "rails_queue_duration_seconds.count",
    "rails_queue_duration_seconds.sum",
    "transaction.allocated_memory_bytes.count",
    "transaction.allocated_memory_bytes.sum",
    "transaction.cache_count_total",
    "transaction.cache_duration_total",
    "transaction.cache_read_hit_count_total",
    "transaction.cache_read_miss_count_total",
    "transaction.duration_seconds.count",
    "transaction_duration_seconds.sum",
    "transaction.event_build_found_total",
    "transaction.event_build_invalid_total",
    "transaction.event_build_not_found_cached_total",
    "transaction.event_build_not_found_total",
    "transaction.event_change_default_branch_total",
    "transaction.event_create_repository_total",
    "transaction.event_etag_caching_cache_hit_total",
    "transaction.event_etag_caching_header_missing_total",
    "transaction.event_etag_caching_key_not_found_total",
    "transaction.event_etag_caching_middleware_used_total",
    "transaction.event_etag_caching_resource_changed_total",
    "transaction.event_fork_repository_total",
    "transaction.event_import_repository_total",
    "transaction.event_push_branch_total",
    "transaction.event_push_commit_total",
    "transaction.event_push_tag_total",
    "transaction.event_rails_exception_total",
    "transaction.event_receive_email_total",
    "transaction.event_remote_mirrors_failed_total",
    "transaction.event_remote_mirrors_finished_total",
    "transaction.event_remote_mirrors_running_total",
    "transaction.event_remove_branch_total",
    "transaction.event_remove_repository_total",
    "transaction.event_remove_tag_total",
    "transaction.event_sidekiq_exception_total",
    "transactionevent_stuck_import_jobs_total",
    "transaction.event_update_build_total",
    "transaction.new_redis_connections_total",
    "transaction.queue_duration_total",
    "transaction.rails_queue_duration_total",
    "transaction.view_duration_total",
    "transaction.view_duration_total.sum",
    "view_rendering_duration_seconds.count",
    "view_rendering_duration_seconds_sum",
    "http_requests_total",
    "http_request_duration_seconds.sum",
    "http_request_duration_seconds.count",
    "pipelines_created_total",
    "rack_uncaught_errors_total",
    "user_session_logins_total",
    "upload_file_does_not_exist",
    "failed_login_captcha_total",
    "successful_login_captcha_total",
    "auto_devops_pipelines_completed_total",
    "sidekiq.jobs_cpu_seconds.count",
    "sidekiq.jobs_cpu_seconds.sum",
    "sidekiq.jobs_completion_seconds.count",
    "sidekiq.jobs_completion_seconds.sum",
    "sidekiq.jobs_queue_duration_seconds.count",
    "sidekiq.jobs_queue_duration_seconds.sum",
    "sidekiq.jobs_failed_total",
    "sidekiq.jobs_retried_total",
    "sidekiq.running_jobs",
    "sidekiq.concurrency",
    "ruby_gc_duration_seconds",
    "ruby.file_descriptors",
    "ruby.memory_bytes",
    "ruby.sampler_duration",
    "ruby.process_cpu_seconds_total",
    "ruby.process_max_fds",
    "ruby.process_resident_memory_bytes",
    "ruby.process_start_time_seconds",
    "ruby.gc_stat.count",
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
    "ruby.gc_stat.total_freed_pages",
    "ruby.gc_stat.total_allocated_objects",
    "ruby.gc_stat.total_freed_objects",
    "ruby.gc_stat.malloc_increase_bytes",
    "ruby.gc_stat.malloc_increase_bytes_limit",
    "ruby.gc_stat.minor_gc_count",
    "ruby.gc_stat.major_gc_count",
    "ruby.gc_stat.remembered_wb_unprotected_objects",
    "ruby.gc_stat.remembered_wb_unprotected_objects_limit",
    "ruby.gc_stat.old_objects",
    "ruby.gc_stat.old_objects_limit",
    "ruby.gc_stat.oldmalloc_increase_bytes",
    "ruby.gc_stat.oldmalloc_increase_bytes_limit"
]

LEGACY_CONFIG = {
    'init_config': {'allowed_metrics': ALLOWED_METRICS},
    'instances': [
        {
            'prometheus_endpoint': PROMETHEUS_ENDPOINT,
            'gitlab_url': GITLAB_URL,
            'disable_ssl_validation': True,
            'tags': list(CUSTOM_TAGS),
        }
    ],
}

CONFIG = {
    'init_config': {},
    'instances': [
        {
            'prometheus_endpoint': GITLAB_PROMETHEUS_ENDPOINT,
            'gitlab_url': GITLAB_URL,
            'disable_ssl_validation': True,
            'tags': list(CUSTOM_TAGS),
        }
    ],
}

BAD_CONFIG = {
    'init_config': {'allowed_metrics': ALLOWED_METRICS},
    'instances': [
        {
            'prometheus_endpoint': 'http://{}:1234/-/metrics'.format(HOST),
            'gitlab_url': 'http://{}:1234/ci'.format(HOST),
            'disable_ssl_validation': True,
            'tags': list(CUSTOM_TAGS),
        }
    ],
}
