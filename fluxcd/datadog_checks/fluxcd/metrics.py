# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


FLUX_V1_METRICS = {
    "controller_runtime_active_workers": "controller.runtime.active.workers",
    "controller_runtime_max_concurrent_reconciles": "controller.runtime.max.concurrent.reconciles",
    "controller_runtime_reconcile": "controller.runtime.reconcile",
    "controller_runtime_reconcile_errors": "controller.runtime.reconcile.errors",
    "controller_runtime_reconcile_time_seconds": "controller.runtime.reconcile.time.seconds",
    "gotk_reconcile_condition": "gotk.reconcile.condition",
    "gotk_reconcile_duration_seconds": "gotk.reconcile.duration.seconds",
    "gotk_suspend_status": "gotk.suspend.status",
}
assert sorted(FLUX_V1_METRICS) == list(FLUX_V1_METRICS)

FLUX_V2_METRICS = {
    "leader_election_master_status": "leader_election_master_status",
    "process_cpu_seconds": "process.cpu_seconds",
    "process_max_fds": "process.max_fds",
    "process_open_fds": "process.open_fds",
    "process_resident_memory_bytes": "process.resident_memory",
    "process_start_time_seconds": "process.start_time",
    "process_virtual_memory_bytes": "process.virtual_memory",
    "process_virtual_memory_max_bytes": "process.virtual_memory.max",
    "workqueue_adds": "workqueue.adds",
    "workqueue_depth": "workqueue.depth",
    "workqueue_longest_running_processor_seconds": "workqueue.longest_running_processor",
    "workqueue_retries": "workqueue.retries",
    "workqueue_unfinished_work_seconds": "workqueue.unfinished_work",
}
assert sorted(FLUX_V2_METRICS) == list(FLUX_V2_METRICS)
METRIC_MAP = {**FLUX_V1_METRICS, **FLUX_V2_METRICS}
