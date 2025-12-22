# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# https://argo-cd.readthedocs.io/en/stable/operator-manual/metrics/
GENERAL_METRICS = {
    'argocd_redis_request': 'redis.request',
    'go_gc_duration_seconds': 'go.gc.duration.seconds',
    'go_goroutines': 'go.goroutines',
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash.sys_bytes',
    'go_memstats_frees': 'go.memstats.frees',
    'go_memstats_gc_cpu_fraction': 'go.memstats.gc.cpu_fraction',
    'go_memstats_gc_sys_bytes': 'go.memstats.gc.sys_bytes',
    'go_memstats_heap_alloc_bytes': 'go.memstats.heap.alloc_bytes',
    'go_memstats_heap_idle_bytes': 'go.memstats.heap.idle_bytes',
    'go_memstats_heap_inuse_bytes': 'go.memstats.heap.inuse_bytes',
    'go_memstats_heap_objects': 'go.memstats.heap.objects',
    'go_memstats_heap_released_bytes': 'go.memstats.heap.released_bytes',
    'go_memstats_heap_sys_bytes': 'go.memstats.heap.sys_bytes',
    'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time.seconds',
    'go_memstats_lookups': 'go.memstats.lookups',
    'go_memstats_mallocs': 'go.memstats.mallocs',
    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache.inuse_bytes',
    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache.sys_bytes',
    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan.inuse_bytes',
    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan.sys_bytes',
    'go_memstats_next_gc_bytes': 'go.memstats.next.gc_bytes',
    'go_memstats_other_sys_bytes': 'go.memstats.other.sys_bytes',
    'go_memstats_stack_inuse_bytes': 'go.memstats.stack.inuse_bytes',
    'go_memstats_stack_sys_bytes': 'go.memstats.stack.sys_bytes',
    'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
    'go_threads': 'go.threads',
    'process_cpu_seconds': 'process.cpu.seconds',
    'process_max_fds': 'process.max_fds',
    'process_open_fds': 'process.open_fds',
    'process_resident_memory_bytes': 'process.resident_memory.bytes',
    'process_start_time_seconds': 'process.start_time.seconds',
    'process_virtual_memory_bytes': 'process.virtual_memory.bytes',
    'process_virtual_memory_max_bytes': 'process.virtual_memory.max_bytes',
}

APPLICATION_CONTROLLER = {
    'argocd_app_k8s_request': 'app.k8s.request',
    'argocd_app_info': 'app.info',
    'argocd_app_reconcile': 'app.reconcile',
    'argocd_app_sync': 'app.sync',
    'argocd_app_sync_duration_seconds': 'app.sync.duration.seconds',
    'argocd_app_labels': 'app.labels',
    'argocd_app_condition': 'app.condition',
    'argocd_app_orphaned_resources_count': 'app.orphaned_resources.count',
    'argocd_resource_events_processing': 'resource_events.processing',
    'argocd_resource_events_processed_in_batch': 'resource_events.processed_in_batch',
    'argocd_cluster_api_resource_objects': 'cluster.api.resource_objects',
    'argocd_cluster_api_resources': 'cluster.api.resources',
    'argocd_cluster_cache_age_seconds': 'cluster.cache.age.seconds',
    'argocd_cluster_events': 'cluster.events',
    'argocd_kubectl_exec_pending': 'kubectl.exec.pending',
    'argocd_kubectl_exec': 'kubectl.exec',
    'argocd_kubectl_client_cert_rotation_age_seconds': 'kubectl.client_cert_rotation.age.seconds',
    'argocd_kubectl_request_duration_seconds': 'kubectl.request.duration.seconds',
    'argocd_kubectl_dns_resolution_duration_seconds': 'kubectl.dns_resolution.duration.seconds',
    'argocd_kubectl_request_size_bytes': 'kubectl.request.size.bytes',
    'argocd_kubectl_response_size_bytes': 'kubectl.response.size.bytes',
    'argocd_kubectl_rate_limiter_duration_seconds': 'kubectl.rate_limiter.duration.seconds',
    'argocd_kubectl_requests_total': 'kubectl.requests',
    'argocd_kubectl_exec_plugin_call_total': 'kubectl.exec_plugin.call',
    'argocd_kubectl_request_retries_total': 'kubectl.request.retries',
    'argocd_kubectl_transport_cache_entries': 'kubectl.transport.cache_entries',
    'argocd_kubectl_transport_create_calls_total': 'kubectl.transport.create_calls',
    'argocd_redis_request_duration': 'redis.request.duration',
    'workqueue_adds': 'workqueue.adds',
    'workqueue_depth': 'workqueue.depth',
    'workqueue_longest_running_processor_seconds': 'workqueue.longest.running_processor.seconds',
    'workqueue_queue_duration_seconds': 'workqueue.queue.duration.seconds',
    'workqueue_retries': 'workqueue.retries',
    'workqueue_unfinished_work_seconds': 'workqueue.unfinished_work.seconds',
    'workqueue_work_duration_seconds': 'workqueue.work.duration.seconds',
}

APPSET_CONTROLLER = {
    'controller_runtime_active_workers': 'active.workers',
    'controller_runtime_max_concurrent_reconciles': 'max.concurrent.reconciles',
    'controller_runtime_reconcile_errors': 'reconcile.errors',
    'controller_runtime_reconcile_time_seconds': 'reconcile.time_seconds',
    'controller_runtime_reconcile': 'runtime.reconcile',
    'argocd_appset_info': 'appset.info',
    'argocd_appset_reconcile': 'appset.reconcile',
    'argocd_appset_owned_applications': 'appset.owned.applications',
    'argocd_appset_labels': 'appset.labels',
    # GitHub API metrics (optional, disabled by default in ArgoCD)
    'argocd_github_api_requests_total': 'github_api.requests',
    'argocd_github_api_request_duration_seconds': 'github_api.request.duration.seconds',
    'argocd_github_api_rate_limit_remaining': 'github_api.rate_limit.remaining',
    'argocd_github_api_rate_limit_limit': 'github_api.rate_limit.limit',
    'argocd_github_api_rate_limit_reset_seconds': 'github_api.rate_limit.reset.seconds',
    'argocd_github_api_rate_limit_used': 'github_api.rate_limit.used',
}

API_SERVER = {
    'argocd_redis_request_duration': 'redis.request.duration',
    'grpc_server_handled': 'grpc.server.handled',
    'grpc_server_msg_sent': 'grpc.server.msg.sent',
    'grpc_server_msg_received': 'grpc.server.msg.received',
    'grpc_server_started': 'grpc.server.started',
    'argocd_login_request_total': 'login.request',
    'argocd_proxy_extension_request_total': 'proxy_extension.request',
    'argocd_proxy_extension_request_duration_seconds': 'proxy_extension.request.duration.seconds',
}

REPO_SERVER = {
    'argocd_git_request_duration_seconds': 'git.request.duration.seconds',
    'argocd_git_request': 'git.request',
    'argocd_git_fetch_fail_total': 'git.fetch.fail',
    'argocd_redis_request_duration_seconds': 'redis.request.duration.seconds',
    'argocd_repo_pending_request_total': 'repo.pending.request.total',
    # OCI registry metrics
    'argocd_oci_request_total': 'oci.request',
    'argocd_oci_request_duration_seconds': 'oci.request.duration.seconds',
    'argocd_oci_test_repo_fail_total': 'oci.test_repo.fail',
    'argocd_oci_get_tags_fail_total': 'oci.get_tags.fail',
    'argocd_oci_digest_metadata_fail_total': 'oci.digest_metadata.fail',
    'argocd_oci_resolve_revision_fail_total': 'oci.resolve_revision.fail',
    'argocd_oci_extract_fail_total': 'oci.extract.fail',
}

# https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/monitoring/
NOTIFICATIONS_CONTROLLER = {
    'argocd_notifications_deliveries': 'notifications.deliveries',
    'argocd_notifications_trigger_eval': 'notifications.trigger_eval',
}

COMMIT_SERVER = {
    'argocd_commitserver_commit_pending_request_total': 'commit.pending.request.total',
    'argocd_commitserver_git_request_duration_seconds': 'git.request.duration.seconds',
    'argocd_commitserver_git_request': 'git.request',
    'argocd_commitserver_commit_request_duration_seconds': 'commit.request.duration.seconds',
    'argocd_commitserver_userinfo_request_duration_seconds': 'userinfo.request.duration.seconds',
    'argocd_commitserver_commit_request': 'commit.request',
}

APPLICATION_CONTROLLER_METRICS = [{**APPLICATION_CONTROLLER, **GENERAL_METRICS}]
APPSET_CONTROLLER_METRICS = [{**APPSET_CONTROLLER, **GENERAL_METRICS}]
API_SERVER_METRICS = [{**API_SERVER, **GENERAL_METRICS}]
REPO_SERVER_METRICS = [{**REPO_SERVER, **GENERAL_METRICS}]
NOTIFICATIONS_CONTROLLER_METRICS = [{**NOTIFICATIONS_CONTROLLER, **GENERAL_METRICS}]
COMMIT_SERVER_METRICS = [{**COMMIT_SERVER, **GENERAL_METRICS}]
