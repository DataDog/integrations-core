# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.constants import ServiceCheck

# Service check
MQ_SUBSCRIPTION = 'mq.subscription'

# Metric names
MESSAGES_CURRENT = 'messages.current'

# Metric map
METRIC_MAP = {
    # Process metrics
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': 'process.start_time_seconds',
    'process_cpu_seconds_total': 'process.cpu_seconds',
    'process_open_fds': 'process.open_fds',
    'process_max_fds': 'process.max_fds',
    
    # Python GC metrics
    'python_gc_objects_collected_total': 'python.gc.objects.collected',
    'python_gc_objects_uncollectable_total': 'python.gc.objects.uncollectable',
    'python_gc_collections_total': 'python.gc.collections',
    'python_info': 'python.info',
    
    # Flower event metrics
    'flower_events_total': 'flower.events.total',
    'flower_events_created': 'flower.events.created',
    
    # Task metrics
    'flower_task_runtime_seconds': 'flower.task.runtime.seconds',
    'flower_task_runtime_seconds_created': 'flower.task.runtime.created',
    'flower_task_prefetch_time_seconds': 'flower.task.prefetch_time.seconds',
    
    # Worker metrics
    'flower_worker_prefetched_tasks': 'flower.worker.prefetched_tasks',
    'flower_worker_online': 'flower.worker.online',
    'flower_worker_number_of_currently_executing_tasks': 'flower.worker.executing_tasks',
}

# Label renaming
RENAME_LABELS_MAP = {
    'version': 'python_version',
}

# Default metric tags
DEFAULT_METRIC_TAGS = [
    'task',
    'worker',
    'generation',  # For GC metrics
    'type',       # For event metrics
]

# Task-specific tags
TASK_TAGS = [
    'task',
    'worker',
]

# Worker-specific tags
WORKER_TAGS = [
    'worker',
]

# Event-specific tags
EVENT_TAGS = [
    'task',
    'type',
    'worker',
]
