# (C) Datadog, Inc. 2023-present
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
    'cluster_autoscaler_created_node_groups_total': 'created.node.groups.total',
    'cluster_autoscaler_deleted_node_groups_total': 'deleted.node.groups.total',
    'cluster_autoscaler_errors_total': 'errors.total',
    'cluster_autoscaler_evicted_pods_total': 'evicted.pods.total',
    'cluster_autoscaler_failed_scale_ups_total': 'failed.scale.ups.total',
    'cluster_autoscaler_function_duration_seconds': 'function.duration.seconds',
    'cluster_autoscaler_last_activity': 'last.activity',
    'cluster_autoscaler_max_nodes_count': 'max.nodes.count',
    'cluster_autoscaler_memory_limits_bytes': 'memory.limits.bytes',
    'cluster_autoscaler_nap_enabled': 'nap.enabled',
    'cluster_autoscaler_node_count': 'node.count',
    'cluster_autoscaler_node_groups_count': 'node.groups.count',
    'cluster_autoscaler_old_unregistered_nodes_removed_count': 'old.unregistered.nodes.removed.count',
    'cluster_autoscaler_scaled_dow_gpu_nodes_total': 'scaled.down.gpu.nodes.total',
    'cluster_autoscaler_scaled_down_nodes_total': 'scaled.down.nodes.total',
    'cluster_autoscaler_scaled_up_gpu_nodes_total': 'scaled.up.gpu.nodes.total',
    'cluster_autoscaler_scaled_up_nodes_total': 'scaled.up.nodes.total',
    'cluster_autoscaler_skipped_scale_events_count': 'skipped.scale.events.count',
    'cluster_autoscaler_unneeded_nodes_count': 'unneeded.nodes.count',
    'cluster_autoscaler_unschedulable_pods_count': 'unschedulable.pods.count',
}
