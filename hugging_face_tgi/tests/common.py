# (C) Datadog, Inc. 2025-present
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
    'hugging_face_tgi.batch.concat.count': 'monotonic_count',
    'hugging_face_tgi.batch.concat.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.concat.duration.sum': 'monotonic_count',
    'hugging_face_tgi.batch.concat.duration.count': 'monotonic_count',
    'hugging_face_tgi.batch.current.max_tokens': 'gauge',
    'hugging_face_tgi.batch.current.size': 'gauge',
    'hugging_face_tgi.batch.decode.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.decode.duration.sum': 'monotonic_count',
    'hugging_face_tgi.batch.decode.duration.count': 'monotonic_count',
    'hugging_face_tgi.batch.filter.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.filter.duration.sum': 'monotonic_count',
    'hugging_face_tgi.batch.filter.duration.count': 'monotonic_count',
    'hugging_face_tgi.batch.forward.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.forward.duration.sum': 'monotonic_count',
    'hugging_face_tgi.batch.forward.duration.count': 'monotonic_count',
    'hugging_face_tgi.batch.inference.count': 'monotonic_count',
    'hugging_face_tgi.batch.inference.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.inference.duration.sum': 'monotonic_count',
    'hugging_face_tgi.batch.inference.duration.count': 'monotonic_count',
    'hugging_face_tgi.batch.inference.success.count': 'monotonic_count',
    'hugging_face_tgi.batch.next.size.bucket': 'monotonic_count',
    'hugging_face_tgi.batch.next.size.sum': 'monotonic_count',
    'hugging_face_tgi.batch.next.size.count': 'monotonic_count',
    'hugging_face_tgi.queue.size': 'gauge',
    'hugging_face_tgi.request.count': 'monotonic_count',
    'hugging_face_tgi.request.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.request.duration.sum': 'monotonic_count',
    'hugging_face_tgi.request.duration.count': 'monotonic_count',
    'hugging_face_tgi.request.failure.count': 'monotonic_count',
    'hugging_face_tgi.request.generated_tokens.bucket': 'monotonic_count',
    'hugging_face_tgi.request.generated_tokens.sum': 'monotonic_count',
    'hugging_face_tgi.request.generated_tokens.count': 'monotonic_count',
    'hugging_face_tgi.request.inference.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.request.inference.duration.sum': 'monotonic_count',
    'hugging_face_tgi.request.inference.duration.count': 'monotonic_count',
    'hugging_face_tgi.request.input_length.bucket': 'monotonic_count',
    'hugging_face_tgi.request.input_length.sum': 'monotonic_count',
    'hugging_face_tgi.request.input_length.count': 'monotonic_count',
    'hugging_face_tgi.request.max_new_tokens.bucket': 'monotonic_count',
    'hugging_face_tgi.request.max_new_tokens.sum': 'monotonic_count',
    'hugging_face_tgi.request.max_new_tokens.count': 'monotonic_count',
    'hugging_face_tgi.request.mean_time_per_token.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.request.mean_time_per_token.duration.sum': 'monotonic_count',
    'hugging_face_tgi.request.mean_time_per_token.duration.count': 'monotonic_count',
    'hugging_face_tgi.request.queue.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.request.queue.duration.sum': 'monotonic_count',
    'hugging_face_tgi.request.queue.duration.count': 'monotonic_count',
    'hugging_face_tgi.request.skipped_tokens.quantile': 'gauge',
    'hugging_face_tgi.request.skipped_tokens.sum': 'monotonic_count',
    'hugging_face_tgi.request.skipped_tokens.count': 'monotonic_count',
    'hugging_face_tgi.request.success.count': 'monotonic_count',
    'hugging_face_tgi.request.validation.duration.bucket': 'monotonic_count',
    'hugging_face_tgi.request.validation.duration.sum': 'monotonic_count',
    'hugging_face_tgi.request.validation.duration.count': 'monotonic_count',
}


RENAMED_LABELS = {
    "hugging_face_tgi.request.failure.count": 'error_type:validation',
    "hugging_face_tgi.batch.concat.count": 'reason:chunking',
}
