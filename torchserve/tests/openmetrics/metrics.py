# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

HOST_TAGS = ('endpoint:http://torchserve:8082/metrics', 'level:Host')

METRICS = {
    'cpu.utilization': {
        "value": 93.3,
        "tags": HOST_TAGS,
    },
    'disk.available': {
        "value": 107.06270599365234,
        "tags": HOST_TAGS,
    },
    'disk.used': {
        "value": 131.79601669311523,
        "tags": HOST_TAGS,
    },
    'disk.utilization': {
        "value": 55.2,
        "tags": HOST_TAGS,
    },
    'memory.available': {
        "value": 29758.09375,
        "tags": HOST_TAGS,
    },
    'memory.used': {
        "value": 1616.35546875,
        "tags": HOST_TAGS,
    },
    'memory.utilization': {
        "value": 7.2,
        "tags": HOST_TAGS,
    },
    'queue.time': {
        "value": 1.0,
        "tags": HOST_TAGS,
    },
    'requests.2xx.count': {
        "value": 58.0,
        "tags": HOST_TAGS,
    },
    'requests.4xx.count': {
        "value": 59,
        "tags": HOST_TAGS,
    },
    'requests.5xx.count': {
        "value": 60,
        "tags": HOST_TAGS,
    },
    'inference.latency.count': {
        "count": 5,
    },
    'inference.count': {
        "count": 5,
    },
    'queue.latency.count': {
        "count": 5,
    },
    'worker.load_time': {
        "count": 5,
    },
    'worker.thread_time': {
        "value": 4,
        "tags": HOST_TAGS,
    },
    'handler_time': {
        "count": 5,
    },
    'prediction_time': {
        "count": 5,
    },
    'gpu.utilization': {
        "value": 1.0,
        "tags": HOST_TAGS,
    },
    'gpu.memory.utilization': {
        "value": 2.0,
        "tags": HOST_TAGS,
    },
    'gpu.memory.used': {
        "value": 4.0,
        "tags": HOST_TAGS,
    },
}

OPTIONAL_METRICS = {
    'requests.4xx.count',
    'requests.5xx.count',
    'gpu.utilization',
    'gpu.memory.utilization',
    'gpu.memory.used',
}
