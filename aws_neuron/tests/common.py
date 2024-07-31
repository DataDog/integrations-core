# (C) Datadog, Inc. 2023-present
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

TEST_METRICS = [
    'aws_neuron.execution.errors_created',
    'aws_neuron.execution.errors.count',
    'aws_neuron.execution.latency_seconds',
    'aws_neuron.execution.status_created',
    'aws_neuron.execution.status.count',
    'aws_neuron.hardware_ecc_events_created',
    'aws_neuron.hardware_ecc_events.count',
    'aws_neuron.instance_info',
    'aws_neuron.neuron_hardware_info',
    'aws_neuron.neuron_runtime.memory_used_bytes',
    'aws_neuron.neuron_runtime.vcpu_usage_ratio',
    'aws_neuron.neuroncore.memory_usage.constants',
    'aws_neuron.neuroncore.memory_usage.model.code',
    'aws_neuron.neuroncore.memory_usage.model.shared_scratchpad',
    'aws_neuron.neuroncore.memory_usage.runtime_memory',
    'aws_neuron.neuroncore.memory_usage.tensors',
    'aws_neuron.neuroncore.utilization_ratio',
    'aws_neuron.process.cpu_seconds.count',
    'aws_neuron.process.max_fds',
    'aws_neuron.process.open_fds',
    'aws_neuron.process.resident_memory_bytes',
    'aws_neuron.process.start_time_seconds',
    'aws_neuron.process.virtual_memory_bytes',
    'aws_neuron.python_gc.collections.count',
    'aws_neuron.python_gc.objects_collected.count',
    'aws_neuron.python_gc.objects_uncollectable.count',
    'aws_neuron.python_info',
    'aws_neuron.system.memory.total_bytes',
    'aws_neuron.system.memory.used_bytes',
    'aws_neuron.system.swap.total_bytes',
    'aws_neuron.system.swap.used_bytes',
    'aws_neuron.system.vcpu.count',
    'aws_neuron.system.vcpu.usage_ratio',
]


RENAMED_LABELS = {
    'python_version:3.9.16',
}
