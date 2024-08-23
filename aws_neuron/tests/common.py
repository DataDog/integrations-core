# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8000


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:tag'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

TEST_METRICS = {
    'aws_neuron.execution.errors_created': 'gauge',
    'aws_neuron.execution.errors.count': 'monotonic_count',
    'aws_neuron.execution.latency_seconds': 'gauge',
    'aws_neuron.execution.status_created': 'gauge',
    'aws_neuron.execution.status.count': 'monotonic_count',
    'aws_neuron.hardware_ecc_events_created': 'gauge',
    'aws_neuron.hardware_ecc_events.count': 'monotonic_count',
    'aws_neuron.instance_info': 'gauge',
    'aws_neuron.neuron_hardware_info': 'gauge',
    'aws_neuron.neuron_runtime.memory_used_bytes': 'gauge',
    'aws_neuron.neuron_runtime.vcpu_usage_ratio': 'gauge',
    'aws_neuron.neuroncore.memory_usage.constants': 'gauge',
    'aws_neuron.neuroncore.memory_usage.model.code': 'gauge',
    'aws_neuron.neuroncore.memory_usage.model.shared_scratchpad': 'gauge',
    'aws_neuron.neuroncore.memory_usage.runtime_memory': 'gauge',
    'aws_neuron.neuroncore.memory_usage.tensors': 'gauge',
    'aws_neuron.neuroncore.utilization_ratio': 'gauge',
    'aws_neuron.process.cpu_seconds.count': 'monotonic_count',
    'aws_neuron.process.max_fds': 'gauge',
    'aws_neuron.process.open_fds': 'gauge',
    'aws_neuron.process.resident_memory_bytes': 'gauge',
    'aws_neuron.process.start_time_seconds': 'gauge',
    'aws_neuron.process.virtual_memory_bytes': 'gauge',
    'aws_neuron.python_gc.collections.count': 'monotonic_count',
    'aws_neuron.python_gc.objects_collected.count': 'monotonic_count',
    'aws_neuron.python_gc.objects_uncollectable.count': 'monotonic_count',
    'aws_neuron.python_info': 'gauge',
    'aws_neuron.system.memory.total_bytes': 'gauge',
    'aws_neuron.system.memory.used_bytes': 'gauge',
    'aws_neuron.system.swap.total_bytes': 'gauge',
    'aws_neuron.system.swap.used_bytes': 'gauge',
    'aws_neuron.system.vcpu.count': 'gauge',
    'aws_neuron.system.vcpu.usage_ratio': 'gauge',
}


RENAMED_LABELS = {
    "aws_neuron.python_info": 'python_version:3.9.16',
}
