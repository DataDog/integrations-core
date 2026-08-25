# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://bentoml:3000/metrics',
    'tags': ['test:tag'],
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


METRICS = [
    'bentoml.service.request.in_progress',
    'bentoml.service.request.count',
    'bentoml.service.request.duration.count',
    'bentoml.service.request.duration.sum',
    'bentoml.service.request.duration.bucket',
    'bentoml.service.adaptive_batch_size.count',
    'bentoml.service.adaptive_batch_size.sum',
    'bentoml.service.adaptive_batch_size.bucket',
    'bentoml.service.request.in_progress',
    'bentoml.service.time_since_last_request',
]

ENDPOINT_METRICS = [
    'bentoml.endpoint_livez',
    'bentoml.endpoint_readyz',
]
