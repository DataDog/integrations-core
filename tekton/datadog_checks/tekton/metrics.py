# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

GENERIC_METRIC_MAP = {
    'client_latency': 'client.latency',
    "client_results": "client.results",
    'go_alloc': 'go.alloc',
    'go_bucket_hash_sys': 'go.bucket_hash_sys',
    'go_frees': 'go.frees',
    'go_gc_cpu_fraction': 'go.gc_cpu_fraction',
    'go_gc_sys': 'go.gc_sys',
    'go_heap_alloc': 'go.heap_alloc',
    'go_heap_idle': 'go.heap_idle',
    'go_heap_in_use': 'go.heap_in_use',
    'go_heap_objects': 'go.heap_objects',
    'go_heap_released': 'go.heap_released',
    'go_heap_sys': 'go.heap_sys',
    'go_last_gc': 'go.last_gc',
    'go_lookups': 'go.lookups',
    'go_mallocs': 'go.mallocs',
    'go_mcache_in_use': 'go.mcache_in_use',
    'go_mcache_sys': 'go.mcache_sys',
    'go_mspan_in_use': 'go.mspan_in_use',
    'go_mspan_sys': 'go.mspan_sys',
    'go_next_gc': 'go.next_gc',
    'go_num_forced_gc': 'go.num_forced_gc',
    'go_num_gc': 'go.num_gc',
    'go_other_sys': 'go.other_sys',
    'go_stack_in_use': 'go.stack_in_use',
    'go_stack_sys': 'go.stack_sys',
    'go_sys': 'go.sys',
    'go_total_alloc': 'go.total_alloc',
    'go_total_gc_pause_ns': 'go.total_gc_pause',
    'workqueue_longest_running_processor_seconds': 'workqueue.longest_running_processor',
    'workqueue_unfinished_work_seconds': 'workqueue.unfinished_work',
}

PIPELINES_METRIC = {
    "pipelinerun_count": "pipelinerun",
    "pipelinerun_duration_seconds": "pipelinerun.duration",
    "pipelinerun_taskrun_duration_seconds": "pipelinerun.taskrun.duration",
    "running_pipelineruns_count": "running_pipelineruns",
    "running_pipelineruns_waiting_on_pipeline_resolution_count": "running_pipelineruns_waiting_on_pipeline_resolution",
    "running_pipelineruns_waiting_on_task_resolution_count": "running_pipelineruns_waiting_on_task_resolution",
    "running_taskruns_count": "running_taskruns",
    "running_taskruns_throttled_by_node_count": "running_taskruns_throttled_by_node",
    "running_taskruns_throttled_by_quota_count": "running_taskruns_throttled_by_quota",
    "running_taskruns_waiting_on_task_resolution_count": "running_taskruns_waiting_on_task_resolution",
    "taskrun_count": "taskrun",
    "taskrun_duration_seconds": "taskrun_duration",
    "taskruns_pod_latency_milliseconds": "taskruns_pod_latency",
}

TRIGGERS_METRIC = {
    "clusterinterceptor_count": "clusterinterceptor",
    "clustertriggerbinding_count": "clustertriggerbinding",
    "eventlistener_count": "eventlistener",
    "reconcile_count": "reconcile",
    "reconcile_latency": "reconcile_latency",
    "triggerbinding_count": "triggerbinding",
    "triggertemplate_count": "triggertemplate",
    "work_queue_depth": "work_queue_depth",
    "workqueue_work_duration_seconds": "workqueue.work_duration",
    "workqueue_adds": "workqueue.adds",
    "workqueue_depth": "workqueue.depth",
    "workqueue_queue_latency_seconds": "workqueue.queue_latency",
}

PIPELINES_METRIC_MAP = PIPELINES_METRIC | GENERIC_METRIC_MAP
PIPELINES_METRIC_MAP = {f"tekton_pipelines_controller_{key}": value for key, value in PIPELINES_METRIC_MAP.items()}

TRIGGERS_METRIC_MAP = TRIGGERS_METRIC | GENERIC_METRIC_MAP
TRIGGERS_METRIC_MAP = {f"controller_{key}": value for key, value in TRIGGERS_METRIC_MAP.items()}

ENDPOINTS_METRICS_MAP = {
    "pipelines_controller_endpoint": PIPELINES_METRIC_MAP,
    "triggers_controller_endpoint": TRIGGERS_METRIC_MAP,
}
