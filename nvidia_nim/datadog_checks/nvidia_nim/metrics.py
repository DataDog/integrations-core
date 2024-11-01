# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    'python_gc_objects_collected': 'python.gc.objects.collected',
    'python_gc_objects_uncollectable': 'python.gc.objects.uncollectable',
    'python_gc_collections': 'python.gc.collections',
    'python_info': 'python.info',
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
    'process_resident_memory_bytes': 'process.resident_memory_bytes',
    'process_start_time_seconds': 'process.start_time_seconds',
    'process_cpu_seconds': 'process.cpu_seconds',
    'process_open_fds': 'process.open_fds',
    'process_max_fds': 'process.max_fds',
    'num_request_max': 'num_request.max',
    'num_requests_running': 'num_requests.running',
    'num_requests_waiting': 'num_requests.waiting',
    'prompt_tokens': 'prompt_tokens',
    'gpu_cache_usage_perc': 'gpu_cache_usage_percent',
    'generation_tokens': 'generation_tokens',
    'time_to_first_token_seconds': 'time_to_first_token.seconds',
    'time_per_output_token_seconds': 'time_per_output_token.seconds',
    'e2e_request_latency_seconds': 'e2e_request_latency.seconds',
    'request_prompt_tokens': 'request.prompt_tokens',
    'request_finish': 'request.finish',
    'request_generation_tokens': 'request.generation_tokens',
    'request_success': 'request.success',
    'request_failure': 'request.failure',
    # HELP python_gc_objects_collected_total Objects collected during gc
    # TYPE python_gc_objects_collected_total counter
    # HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
    # TYPE python_gc_objects_uncollectable_total counter
    # HELP python_gc_collections_total Number of times this generation was collected
    # TYPE python_gc_collections_total counter
    # HELP python_info Python platform information
    # TYPE python_info gauge
    # HELP process_virtual_memory_bytes Virtual memory size in bytes.
    # TYPE process_virtual_memory_bytes gauge
    # HELP process_resident_memory_bytes Resident memory size in bytes.
    # TYPE process_resident_memory_bytes gauge
    # HELP process_start_time_seconds Start time of the process since unix epoch in seconds.
    # TYPE process_start_time_seconds gauge
    # HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
    # TYPE process_cpu_seconds_total counter
    # HELP process_open_fds Number of open file descriptors.
    # TYPE process_open_fds gauge
    # HELP process_max_fds Maximum number of open file descriptors.
    # TYPE process_max_fds gauge
    # HELP num_requests_running Number of requests currently running on GPU.
    # TYPE num_requests_running gauge
    # HELP num_requests_waiting Number of requests waiting to be processed.
    # TYPE num_requests_waiting gauge
    # HELP num_request_max Max number of concurrently running requests.
    # TYPE num_request_max gauge
    # HELP gpu_cache_usage_perc GPU KV-cache usage. 1 means 100 percent usage.
    # TYPE gpu_cache_usage_perc gauge
    # HELP prompt_tokens_total Number of prefill tokens processed.
    # TYPE prompt_tokens_total counter
    # HELP generation_tokens_total Number of generation tokens processed.
    # TYPE generation_tokens_total counter
    # HELP time_to_first_token_seconds Histogram of time to first token in seconds.
    # TYPE time_to_first_token_seconds histogram
    # HELP time_per_output_token_seconds Histogram of time per output token in seconds.
    # TYPE time_per_output_token_seconds histogram
    # HELP e2e_request_latency_seconds Histogram of end to end request latency in seconds.
    # TYPE e2e_request_latency_seconds histogram
    # HELP request_prompt_tokens Number of prefill tokens processed.
    # TYPE request_prompt_tokens histogram
    # HELP request_generation_tokens Number of generation tokens processed.
    # TYPE request_generation_tokens histogram
    # HELP request_finish_total Count of finished requests, differentiated by finish reason as label.
    # TYPE request_finish_total counter
    # HELP request_success_total Count of successful requests.
    # TYPE request_success_total counter
    # HELP request_failure_total Count of failed requests.
    # TYPE request_failure_total counter
}

RENAME_LABELS_MAP = {
    'version': 'python_version',
}
