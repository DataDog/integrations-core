# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Some metrics mapping are too long. This turns off the 120 line limit for this file:
# ruff: noqa: E501

# The scheduler also registers every metric below without the `kai_` prefix. Those copies are never updated, so only
# the prefixed names are mapped.
SCHEDULER_METRICS = {
    'kai_action_scheduling_latency_milliseconds': 'action.latency.milliseconds',
    'kai_close_session_latency_milliseconds': 'session.close.latency.milliseconds',
    'kai_e2e_scheduling_latency_milliseconds': 'scheduling_cycle.latency.milliseconds',
    'kai_open_session_latency_milliseconds': 'session.open.latency.milliseconds',
    'kai_plugin_scheduling_latency_milliseconds': 'plugin.latency.milliseconds',
    'kai_podgroups_acted_on_by_action': 'action.podgroups.attempted',
    'kai_podgroups_scheduled_by_action': 'action.podgroups.scheduled',
    'kai_queue_cpu_usage': 'queue.usage.cpu',
    'kai_queue_fair_share_cpu_cores': 'queue.fair_share.cpu',
    'kai_queue_fair_share_gpu': 'queue.fair_share.gpu',
    'kai_queue_gpu_usage': 'queue.usage.gpu',
    'kai_queue_memory_usage': 'queue.usage.memory',
    'kai_scenario_search_action_budget_configured_seconds': 'scenario_search.budget.action.seconds',
    'kai_scenario_search_action_budget_exhausted': 'scenario_search.budget_exhausted',
    'kai_scenario_search_duration_seconds': 'scenario_search.duration.seconds',
    'kai_scenario_search_generator_budget_configured_seconds': 'scenario_search.budget.generator.seconds',
    'kai_scenario_search_job_budget_configured_seconds': 'scenario_search.budget.job.seconds',
    'kai_scenario_search_jobs': 'scenario_search.jobs',
    'kai_scenario_search_scenarios': 'scenario_search.scenarios',
    'kai_scenarios_filtered_by_action': 'action.scenarios.filtered',
    'kai_scenarios_simulation_by_action': 'action.scenarios.simulated',
    'kai_task_bind_latency_milliseconds': 'task.bind_latency.milliseconds',
    'kai_task_scheduling_latency_milliseconds': 'task.scheduling_latency.milliseconds',
    'kai_total_preemption_attempts': 'preemption.attempts',
    'kai_usage_query_latency_milliseconds': 'usage_query.latency.milliseconds',
}

# Reported in GB by the scheduler and converted to bytes by a custom transformer, so that it shares a unit with the
# queue-controller memory metrics.
FAIR_SHARE_MEMORY_METRIC = 'kai_queue_fair_share_memory_gb'
FAIR_SHARE_MEMORY_NAME = 'queue.fair_share.memory'
BYTES_PER_GB = 1000 * 1000 * 1000

QUEUE_CONTROLLER_METRICS = {
    'kai_queue_allocated_cpu_cores': 'queue.allocated.cpu',
    'kai_queue_allocated_gpus': 'queue.allocated.gpu',
    'kai_queue_allocated_memory_bytes': 'queue.allocated.memory',
    'kai_queue_deserved_gpus': 'queue.quota.gpu',
    'kai_queue_info': 'queue.info',
    'kai_queue_quota_cpu_cores': 'queue.quota.cpu',
    'kai_queue_quota_memory_bytes': 'queue.quota.memory',
}

CONTROLLER_RUNTIME_METRICS = {
    'certwatcher_read_certificate': 'certwatcher.read_certificate',
    'certwatcher_read_certificate_errors': 'certwatcher.read_certificate_errors',
    'controller_runtime_active_workers': 'controller.runtime.active_workers',
    'controller_runtime_conversion_webhook_panics': 'controller.runtime.conversion_webhook_panics',
    'controller_runtime_max_concurrent_reconciles': 'controller.runtime.max_concurrent_reconciles',
    'controller_runtime_reconcile': 'controller.runtime.reconcile',
    'controller_runtime_reconcile_errors': 'controller.runtime.reconcile_errors',
    'controller_runtime_reconcile_panics': 'controller.runtime.reconcile_panics',
    'controller_runtime_reconcile_time_seconds': 'controller.runtime.reconcile_time.seconds',
    'controller_runtime_reconcile_timeouts': 'controller.runtime.reconcile_timeouts',
    'controller_runtime_terminal_reconcile_errors': 'controller.runtime.terminal_reconcile_errors',
    'controller_runtime_webhook_latency_seconds': 'controller.runtime.webhook_latency.seconds',
    'controller_runtime_webhook_panics': 'controller.runtime.webhook_panics',
    'controller_runtime_webhook_requests': 'controller.runtime.webhook_requests',
    'controller_runtime_webhook_requests_in_flight': 'controller.runtime.webhook_requests_in_flight',
    'leader_election_master_status': 'leader_election.master_status',
    'workqueue_adds': 'workqueue.adds',
    'workqueue_depth': 'workqueue.depth',
    'workqueue_longest_running_processor_seconds': 'workqueue.longest_running_processor.seconds',
    'workqueue_queue_duration_seconds': 'workqueue.queue_duration.seconds',
    'workqueue_retries': 'workqueue.retries',
    'workqueue_unfinished_work_seconds': 'workqueue.unfinished_work.seconds',
    'workqueue_work_duration_seconds': 'workqueue.work_duration.seconds',
}

GO_PROCESS_METRICS = {
    'go_gc_duration_seconds': 'go.gc.duration.seconds',
    'go_gc_gogc_percent': 'go.gc.gogc.percent',
    'go_gc_gomemlimit_bytes': 'go.gc.gomemlimit.bytes',
    'go_goroutines': 'go.goroutines',
    'go_info': 'go.info',
    # `go_memstats_alloc_bytes_total` is a counter that parses to the same name as this gauge.
    'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'},
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash.sys_bytes',
    'go_memstats_frees': 'go.memstats.frees',
    'go_memstats_gc_sys_bytes': 'go.memstats.gc.sys_bytes',
    'go_memstats_heap_alloc_bytes': 'go.memstats.heap_alloc.bytes',
    'go_memstats_heap_idle_bytes': 'go.memstats.heap_idle.bytes',
    'go_memstats_heap_inuse_bytes': 'go.memstats.heap_inuse.bytes',
    'go_memstats_heap_objects': 'go.memstats.heap_objects',
    'go_memstats_heap_released_bytes': 'go.memstats.heap_released.bytes',
    'go_memstats_heap_sys_bytes': 'go.memstats.heap_sys.bytes',
    'go_memstats_last_gc_time_seconds': {'name': 'go.memstats.time_since_last_gc.seconds', 'type': 'time_elapsed'},
    'go_memstats_mallocs': 'go.memstats.mallocs',
    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache_inuse.bytes',
    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache_sys.bytes',
    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan_inuse.bytes',
    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan_sys.bytes',
    'go_memstats_next_gc_bytes': 'go.memstats.next_gc.bytes',
    'go_memstats_other_sys_bytes': 'go.memstats.other_sys.bytes',
    'go_memstats_stack_inuse_bytes': 'go.memstats.stack_inuse.bytes',
    'go_memstats_stack_sys_bytes': 'go.memstats.stack_sys.bytes',
    'go_memstats_sys_bytes': 'go.memstats.sys.bytes',
    'go_threads': 'go.threads',
    'process_cpu_seconds': 'process.cpu.seconds',
    'process_max_fds': 'process.max_fds',
    'process_network_receive_bytes': 'process.network_receive.bytes',
    'process_network_transmit_bytes': 'process.network_transmit.bytes',
    'process_open_fds': 'process.open_fds',
    'process_resident_memory_bytes': 'process.resident_memory.bytes',
    'process_start_time_seconds': {'name': 'process.uptime.seconds', 'type': 'time_elapsed'},
    'process_virtual_memory_bytes': 'process.virtual_memory.bytes',
    'process_virtual_memory_max_bytes': 'process.virtual_memory.max_bytes',
}
