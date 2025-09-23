# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Some metrics mapping are too long. This turns off the 120 line limit for this file:
# ruff: noqa: E501

# metrics are documented here
# https://github.com/kubernetes/autoscaler/blob/master/cluster-autoscaler/proposals/metrics.md

METRIC_MAP = {
    'cluster_autoscaler_cluster_cpu_current_cores': 'cluster.cpu.current.cores',
    'cluster_autoscaler_cluster_memory_current_bytes': 'cluster.memory.current.bytes',
    'cluster_autoscaler_cluster_safe_to_autoscale': 'cluster.safe.to.autoscale',
    'cluster_autoscaler_cpu_limits_cores': 'cpu.limits.cores',
    'cluster_autoscaler_created_node_groups': 'created.node.groups',
    'cluster_autoscaler_deleted_node_groups': 'deleted.node.groups',
    'cluster_autoscaler_errors': 'errors',
    'cluster_autoscaler_evicted_pods': 'evicted.pods',
    'cluster_autoscaler_failed_scale_ups': 'failed.scale.ups',
    'cluster_autoscaler_function_duration_seconds': 'function.duration.seconds',
    'cluster_autoscaler_last_activity': 'last.activity',
    'cluster_autoscaler_max_nodes_count': 'max.nodes.count',
    'cluster_autoscaler_memory_limits_bytes': 'memory.limits.bytes',
    'cluster_autoscaler_nap_enabled': 'nap.enabled',
    'cluster_autoscaler_nodes_count': 'nodes.count',
    'cluster_autoscaler_node_groups_count': 'node.groups.count',
    'cluster_autoscaler_old_unregistered_nodes_removed_count': 'old.unregistered.nodes.removed',
    'cluster_autoscaler_scaled_down_gpu_nodes': 'scaled.down.gpu.nodes',
    'cluster_autoscaler_scaled_down_nodes': 'scaled.down.nodes',
    'cluster_autoscaler_scaled_up_gpu_nodes': 'scaled.up.gpu.nodes',
    'cluster_autoscaler_scaled_up_nodes': 'scaled.up.nodes',
    'cluster_autoscaler_skipped_scale_events_count': 'skipped.scale.events',
    'cluster_autoscaler_unneeded_nodes_count': 'unneeded.nodes.count',
    'cluster_autoscaler_unschedulable_pods_count': 'unschedulable.pods.count',
    # GO metrics
    'go_gc_duration_seconds': 'go.gc.duration.seconds',
    'go_goroutines': 'go.goroutines',
    'go_info': 'go.info',
    'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'},
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash.sys_bytes',
    'go_memstats_frees': 'go.memstats.frees',
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
}

RENAME_LABELS_MAP = {
    'cluster': 'kubernetes_cluster_autoscaler_cluster',
    'namespace': 'kubernetes_cluster_autoscaler_namespace',
    'version': 'go_version',
    'name': 'kubernetes_cluster_autoscaler_name',
}
