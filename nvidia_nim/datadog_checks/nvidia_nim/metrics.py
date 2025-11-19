# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': {'name': 'process.start_time_seconds', 'type': 'time_elapsed'},
    'process_cpu_seconds': 'process.cpu_seconds',
    'process_open_fds': 'process.open_fds',
    'process_max_fds': 'process.max_fds',
    'prompt_tokens': 'prompt_tokens',
    'python_gc_objects_collected': 'python.gc.objects.collected',
    'python_gc_objects_uncollectable': 'python.gc.objects.uncollectable',
    'python_gc_collections': 'python.gc.collections',
    'python_info': 'python.info',
    'num_request_max': 'num_request.max',
    'num_requests_running': 'num_requests.running',
    'num_requests_waiting': 'num_requests.waiting',
    'gpu_cache_usage_perc': 'gpu_cache_usage_percent',
    'generation_tokens': 'generation_tokens',
    'time_to_first_token_seconds': 'time_to_first_token.seconds',
    'time_per_output_token_seconds': 'time_per_output_token.seconds',
    'e2e_request_latency_seconds': 'e2e_request_latency.seconds',
    'request_finish': 'request.finish',
    'request_generation_tokens': 'request.generation_tokens',
    'request_prompt_tokens': 'request.prompt_tokens',
    'request_success': 'request.success',
    'request_failure': 'request.failure',
}

RENAME_LABELS_MAP = {
    'version': 'python_version',
}
