# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
METRIC_MAP = {
    # Generic Metrics:
    'controller_clientset_k8s_request': 'controller.clientset.k8s.request',
    'go_gc_duration_seconds': 'go.gc.duration.seconds',
    'go_goroutines': 'go.goroutines',
    'go_info': "go.info",
    'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'},
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
    'workqueue_adds': 'workqueue.adds',
    'workqueue_depth': 'workqueue.depth',
    'workqueue_longest_running_processor_seconds': 'workqueue.longest.running_processor.seconds',
    'workqueue_queue_duration_seconds': 'workqueue.queue.duration.seconds',
    'workqueue_retries': 'workqueue.retries',
    'workqueue_unfinished_work_seconds': 'workqueue.unfinished_work.seconds',
    'workqueue_work_duration_seconds': 'workqueue.work.duration.seconds',
    # Kyverno specific metrics:
    'kyverno_policy_changes': 'policy.changes',
    'kyverno_controller_requeue': 'controller.requeue',
    'kyverno_controller_reconcile': 'controller.reconcile',
    'kyverno_controller_drop': 'controller.drop',
    'kyverno_client_queries': 'client.queries',
    'kyverno_ttl_controller_errors': 'ttl.controller.errors',
    'kyverno_ttl_controller_deletedobjects': 'ttl.controller.deletedobjects',
    'kyverno_cleanup_controller_deletedobjects': 'cleanup.controller.deletedobjects',
    'kyverno_cleanup_controller_errors': 'cleanup.controller.errors',
    'kyverno_admission_requests': 'admission.requests',
    'kyverno_admission_review_duration_seconds': 'admission.review.duration.seconds',
    'kyverno_policy_execution_duration_seconds': 'policy.execution.duration.seconds',
    'kyverno_http_requests_duration_seconds': 'http.requests.duration.seconds',
    'kyverno_http_requests': 'http.requests',
    'kyverno_policy_results': 'policy.results',
    # Not a counter, but a gauge
    'kyverno_policy_rule_info_total': 'policy.rule.info',
}


RENAME_LABELS_MAP = {
    'version': 'go_version',
    # These don't actually exist, but in the off chance they do we should remap them to not conflict with
    # regular generic tags.
    'name': 'kyverno_name',
    'namespace': 'kyverno_namespace',
}
