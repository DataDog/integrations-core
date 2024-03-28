# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse
from datadog_checks.tekton import TektonCheck

HERE = get_here()

PIPELINES_METRICS = [
    "client.latency.bucket",
    "client.latency.count",
    "client.latency.sum",
    "client.results.count",
    "go.alloc",
    "go.bucket_hash_sys",
    "go.frees",
    "go.gc_cpu_fraction",
    "go.gc_sys",
    "go.heap_alloc",
    "go.heap_idle",
    "go.heap_in_use",
    "go.heap_objects",
    "go.heap_released",
    "go.heap_sys",
    "go.last_gc",
    "go.lookups",
    "go.mallocs",
    "go.mcache_in_use",
    "go.mcache_sys",
    "go.mspan_in_use",
    "go.mspan_sys",
    "go.next_gc",
    "go.num_forced_gc",
    "go.num_gc",
    "go.other_sys",
    "go.stack_in_use",
    "go.stack_sys",
    "go.sys",
    "go.total_alloc",
    "go.total_gc_pause",
    "pipelinerun.count",
    "pipelinerun.duration.bucket",
    "pipelinerun.duration.count",
    "pipelinerun.duration.sum",
    "running_pipelineruns",
    "running_pipelineruns_waiting_on_pipeline_resolution",
    "running_pipelineruns_waiting_on_task_resolution",
    "running_taskruns",
    "running_taskruns_throttled_by_node",
    "running_taskruns_throttled_by_quota",
    "running_taskruns_waiting_on_task_resolution",
    "taskrun.count",
    "taskrun_duration.bucket",
    "taskrun_duration.count",
    "taskrun_duration.sum",
    "taskruns_pod_latency",
    "workqueue.longest_running_processor.bucket",
    "workqueue.longest_running_processor.count",
    "workqueue.longest_running_processor.sum",
    "workqueue.unfinished_work.bucket",
    "workqueue.unfinished_work.count",
    "workqueue.unfinished_work.sum",
]
assert PIPELINES_METRICS == sorted(PIPELINES_METRICS)

PIPELINES_OPTIONAL_METRICS = [
    "pipelinerun.taskrun.duration.bucket",
    "pipelinerun.taskrun.duration.count",
    "pipelinerun.taskrun.duration.sum",
]
assert PIPELINES_OPTIONAL_METRICS == sorted(PIPELINES_OPTIONAL_METRICS)

TRIGGERS_METRICS = [
    "client.latency.bucket",
    "client.latency.count",
    "client.latency.sum",
    "client.results.count",
    "clusterinterceptor",
    "clustertriggerbinding",
    "eventlistener",
    "go.alloc",
    "go.bucket_hash_sys",
    "go.frees",
    "go.gc_cpu_fraction",
    "go.gc_sys",
    "go.heap_alloc",
    "go.heap_idle",
    "go.heap_in_use",
    "go.heap_objects",
    "go.heap_released",
    "go.heap_sys",
    "go.last_gc",
    "go.lookups",
    "go.mallocs",
    "go.mcache_in_use",
    "go.mcache_sys",
    "go.mspan_in_use",
    "go.mspan_sys",
    "go.next_gc",
    "go.num_forced_gc",
    "go.num_gc",
    "go.other_sys",
    "go.stack_in_use",
    "go.stack_sys",
    "go.sys",
    "go.total_alloc",
    "go.total_gc_pause",
    "reconcile.count",
    "reconcile_latency.bucket",
    "reconcile_latency.count",
    "reconcile_latency.sum",
    "triggerbinding",
    "triggertemplate",
    "work_queue_depth",
    "workqueue.adds.count",
    "workqueue.depth",
    "workqueue.longest_running_processor.bucket",
    "workqueue.longest_running_processor.count",
    "workqueue.longest_running_processor.sum",
    "workqueue.queue_latency.bucket",
    "workqueue.queue_latency.count",
    "workqueue.queue_latency.sum",
    "workqueue.unfinished_work.bucket",
    "workqueue.unfinished_work.count",
    "workqueue.unfinished_work.sum",
    "workqueue.work_duration.bucket",
    "workqueue.work_duration.count",
    "workqueue.work_duration.sum",
]
assert PIPELINES_METRICS == sorted(PIPELINES_METRICS)


def check(instance):
    return TektonCheck('tekton', {}, [instance])


def mock_http_responses(url, **_params):
    mapping = {
        'http://tekton-pipelines:9090': 'pipelines.txt',
        'http://tekton-triggers:9000': 'triggers.txt',
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        raise Exception(f"url `{url}` not registered")

    with open(os.path.join(HERE, 'fixtures', metrics_file)) as f:
        return MockResponse(content=f.read())
