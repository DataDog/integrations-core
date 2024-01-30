# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse

HERE = get_here()

MOCKED_PIPELINES_METRICS = [
    'go_alloc',
]

MOCKED_TRIGGERS_METRICS = [
    'clusterinterceptor',
]

PIPELINES_METRICS = [
    'go_alloc',
]

TRIGGERS__METRICS = [
    'clusterinterceptor',
]


def mock_http_responses(url, **_params):
    mapping = {
        'http://tekton-pipelines:9090': 'pipelines.txt',
        'http://tekton-triggers:9000': 'triggers.txt',
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        raise Exception(f"url `{url}` not registered")

    with open(os.path.join(HERE, 'fixtures', metrics_file)) as f:
        return MockResponse(content=f.read())
