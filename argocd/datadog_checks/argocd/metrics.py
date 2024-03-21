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
    'argocd_app_labels': 'app.labels',
    'argocd_cluster_api_resource_objects': 'cluster.api.resource_objects',
    'argocd_cluster_api_resources': 'cluster.api.resources',
    'argocd_cluster_cache_age_seconds': 'cluster.cache.age.seconds',
    'argocd_cluster_events': 'cluster.events',
    'argocd_kubectl_exec_pending': 'kubectl.exec.pending',
    'argocd_kubectl_exec': 'kubectl.exec',
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
    'controller_runtime_reconcile_errors_total': 'reconcile.errors.total',
    'controller_runtime_reconcile_time_seconds': 'reconcile.time_seconds',
    'controller_runtime_reconcile_total': 'runtime.reconcile.total',
}

API_SERVER = {
    'argocd_redis_request_duration': 'redis.request.duration',
    'grpc_server_handled': 'grpc.server.handled',
    'grpc_server_msg_sent': 'grpc.server.msg.sent',
    'grpc_server_msg_received': 'grpc.server.msg.received',
    'grpc_server_started': 'grpc.server.started',
}

REPO_SERVER = {
    'argocd_git_request_duration_seconds': 'git.request.duration.seconds',
    'argocd_git_request': 'git.request',
    'argocd_redis_request_duration_seconds': 'redis.request.duration.seconds',
    'argocd_repo_pending_request_total': 'repo.pending.request.total',
}

# https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/monitoring/
NOTIFICATIONS_CONTROLLER = {
    'argocd_notifications_deliveries': 'notifications.deliveries',
    'argocd_notifications_trigger_eval': 'notifications.trigger_eval',
}

APPLICATION_CONTROLLER_METRICS = [{**APPLICATION_CONTROLLER, **GENERAL_METRICS}]
APPSET_CONTROLLER_METRICS = [{**APPSET_CONTROLLER, **GENERAL_METRICS}]
API_SERVER_METRICS = [{**API_SERVER, **GENERAL_METRICS}]
REPO_SERVER_METRICS = [{**REPO_SERVER, **GENERAL_METRICS}]
NOTIFICATIONS_CONTROLLER_METRICS = [{**NOTIFICATIONS_CONTROLLER, **GENERAL_METRICS}]
