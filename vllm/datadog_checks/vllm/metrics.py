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
    'vllm:cache_config_info': 'cache_config_info',
    'vllm:num_requests_running': 'num_requests.running',
    'vllm:num_requests_waiting': 'num_requests.waiting',
    'vllm:num_requests_swapped': 'num_requests.swapped',
    'vllm:gpu_cache_usage_perc': 'gpu_cache_usage_perc',
    'vllm:cpu_cache_usage_perc': 'cpu_cache_usage_perc',
    'vllm:num_preemptions': 'num_preemptions',
    'vllm:prompt_tokens': 'prompt_tokens',
    'vllm:generation_tokens': 'generation_tokens',
    'vllm:time_to_first_token_seconds': 'time_to_first_token.seconds',
    'vllm:time_per_output_token_seconds': 'time_per_output_token.seconds',
    'vllm:e2e_request_latency_seconds': 'e2e_request_latency.seconds',
    'vllm:request_prompt_tokens': 'request.prompt_tokens',
    'vllm:request_generation_tokens': 'request.generation_tokens',
    'vllm:request_params_best_of': 'request.params.best_of',
    'vllm:request_params_n': 'request.params.n',
    'vllm:request_success': 'request.success',
    'vllm:avg_prompt_throughput_toks_per_s': 'avg.prompt.throughput.toks_per_s',
    'vllm:avg_generation_throughput_toks_per_s': 'avg.generation_throughput.toks_per_s',
}

RENAME_LABELS_MAP = {
    'version': 'python_version',
}
