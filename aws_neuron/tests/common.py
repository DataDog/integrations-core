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
    'aws_neuron.execution_errors_created',
    'aws_neuron.execution_errors.count',
    'aws_neuron.execution_latency_seconds',
    'aws_neuron.execution_status_created',
    'aws_neuron.execution_status.count',
    'aws_neuron.hardware_ecc_events_created',
    'aws_neuron.hardware_ecc_events.count',
    'aws_neuron.instance_info',
    'aws_neuron.neuron_hardware_info',
    'aws_neuron.neuron_runtime_memory_used_bytes',
    'aws_neuron.neuron_runtime_vcpu_usage_ratio',
    'aws_neuron.neuroncore_memory_usage_constants',
    'aws_neuron.neuroncore_memory_usage_model_code',
    'aws_neuron.neuroncore_memory_usage_model_shared_scratchpad',
    'aws_neuron.neuroncore_memory_usage_runtime_memory',
    'aws_neuron.neuroncore_memory_usage_tensors',
    'aws_neuron.neuroncore_utilization_ratio',
    'aws_neuron.process_cpu_seconds.count',
    'aws_neuron.process_max_fds',
    'aws_neuron.process_open_fds',
    'aws_neuron.process_resident_memory_bytes',
    'aws_neuron.process_start_time_seconds',
    'aws_neuron.process_virtual_memory_bytes',
    'aws_neuron.python_gc_collections.count',
    'aws_neuron.python_gc_objects_collected.count',
    'aws_neuron.python_gc_objects_uncollectable.count',
    'aws_neuron.python_info',
    'aws_neuron.system_memory_total_bytes',
    'aws_neuron.system_memory_used_bytes',
    'aws_neuron.system_swap_total_bytes',
    'aws_neuron.system_swap_used_bytes',
    'aws_neuron.system_vcpu_count',
    'aws_neuron.system_vcpu_usage_ratio',
]


RENAMED_LABELS = {
        'python_version:3.9.16',
}
