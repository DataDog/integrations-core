# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    'tgi_batch_concat': 'batch.concat',
    'tgi_batch_concat_duration': 'batch.concat.duration',
    'tgi_batch_current_max_tokens': 'batch.current.max_tokens',
    'tgi_batch_current_size': 'batch.current.size',
    'tgi_batch_decode_duration': 'batch.decode.duration',
    'tgi_batch_filter_duration': 'batch.filter.duration',
    'tgi_batch_forward_duration': 'batch.forward.duration',
    'tgi_batch_inference_count': 'batch.inference',
    'tgi_batch_inference_duration': 'batch.inference.duration',
    'tgi_batch_inference_success': 'batch.inference.success',
    'tgi_batch_next_size': 'batch.next.size',
    'tgi_queue_size': 'queue.size',
    'tgi_request_count': 'request',
    'tgi_request_duration': 'request.duration',
    'tgi_request_failure': 'request.failure',
    'tgi_request_generated_tokens': 'request.generated_tokens',
    'tgi_request_inference_duration': 'request.inference.duration',
    'tgi_request_input_length': 'request.input_length',
    'tgi_request_max_new_tokens': 'request.max_new_tokens',
    'tgi_request_mean_time_per_token_duration': 'request.mean_time_per_token.duration',
    'tgi_request_queue_duration': 'request.queue.duration',
    'tgi_request_skipped_tokens': 'request.skipped_tokens',
    'tgi_request_success': 'request.success',
    'tgi_request_validation_duration': 'request.validation.duration',
}

RENAME_LABELS_MAP = {
    'err': 'error_type',
}
