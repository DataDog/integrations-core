# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

OPENMETRICS_METRIC_MAP = {
    'CPUUtilization': 'cpu.utilization',
    'DiskAvailable': 'disk.available',
    'DiskUsage': 'disk.used',
    'DiskUtilization': 'disk.utilization',
    'MemoryAvailable': 'memory.available',
    'MemoryUsed': 'memory.used',
    'MemoryUtilization': 'memory.utilization',
    'QueueTime': 'queue.time',
    'Requests2XX': 'requests.2xx',
    'Requests4XX': 'requests.4xx',
    'Requests5XX': 'requests.5xx',
    'ts_inference_latency_microseconds': 'inference.latency',
    'ts_inference_requests': 'inference',
    'ts_queue_latency_microseconds': 'queue.latency',
    'WorkerLoadTime': 'worker.load_time',
    'WorkerThreadTime': 'worker.thread_time',
    'GPUUtilization': 'gpu.utilization',
    'GPUMemoryUtilization': 'gpu.memory.utilization',
    'GPUMemoryUsed': 'gpu.memory.used',
    'HandlerTime': 'handler_time',
    'PredictionTime': 'prediction_time',
}
