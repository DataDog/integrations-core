# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    'execution_errors_created': 'execution.errors_created',
    'execution_errors': 'execution.errors',
    'execution_latency_seconds': 'execution.latency_seconds',
    'execution_status_created': 'execution.status_created',
    'execution_status': 'execution.status',
    'hardware_ecc_events_created': 'hardware_ecc_events_created',
    'hardware_ecc_events': 'hardware_ecc_events',
    'instance_info': 'instance_info',
    'neuron_hardware_info': 'neuron_hardware_info',
    'neuron_runtime_memory_used_bytes': 'neuron_runtime.memory_used_bytes',
    'neuron_runtime_vcpu_usage_ratio': 'neuron_runtime.vcpu_usage_ratio',
    'neuroncore_memory_usage_constants': 'neuroncore.memory_usage.constants',
    'neuroncore_memory_usage_model_code': 'neuroncore.memory_usage.model.code',
    'neuroncore_memory_usage_model_shared_scratchpad': 'neuroncore.memory_usage.model.shared_scratchpad',
    'neuroncore_memory_usage_runtime_memory': 'neuroncore.memory_usage.runtime_memory',
    'neuroncore_memory_usage_tensors': 'neuroncore.memory_usage.tensors',
    'neuroncore_utilization_ratio': 'neuroncore.utilization_ratio',
    'process_cpu_seconds': 'process.cpu_seconds',
    'process_max_fds': 'process.max_fds',
    'process_open_fds': 'process.open_fds',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': 'process.start_time_seconds',
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
    'python_gc_collections': 'python_gc.collections',
    'python_gc_objects_collected': 'python_gc.objects_collected',
    'python_gc_objects_uncollectable': 'python_gc.objects_uncollectable',
    'python_info': 'python_info',
    'system_memory_total_bytes': 'system.memory.total_bytes',
    'system_memory_used_bytes': 'system.memory.used_bytes',
    'system_swap_total_bytes': 'system.swap.total_bytes',
    'system_swap_used_bytes': 'system.swap.used_bytes',
    'system_vcpu_count': 'system.vcpu.count',
    'system_vcpu_usage_ratio': 'system.vcpu.usage_ratio',
}

RENAME_LABELS_MAP = {
    "version": "python_version",
}
