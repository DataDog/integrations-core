# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Metric map
METRIC_MAP = {
    # Flower event metrics
    'flower_events_created': 'events.created',
    'flower_events': 'events',
    # Task metrics
    'flower_task_runtime_seconds': 'task.runtime.seconds',
    'flower_task_runtime_seconds_created': 'task.runtime.created',
    'flower_task_prefetch_time_seconds': 'task.prefetch_time.seconds',
    # Worker metrics
    'flower_worker_prefetched_tasks': 'worker.prefetched_tasks',
    'flower_worker_online': 'worker.online',
    'flower_worker_number_of_currently_executing_tasks': 'worker.executing_tasks',
}
