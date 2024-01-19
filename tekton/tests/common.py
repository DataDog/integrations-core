# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.http import MockResponse

HERE = get_here()

MOCKED_METRICS = [
    'pipelines_controller.go_alloc',
]

METRICS = [
    'pipelines_controller.go_alloc',
]


def mock_http_responses(url, **_params):
    mapping = {
        'http://tekton:8080': 'metrics.txt',
    }

    metrics_file = mapping.get(url)

    if not metrics_file:
        raise Exception(f"url `{url}` not registered")

    with open(os.path.join(HERE, 'fixtures', metrics_file)) as f:
        return MockResponse(content=f.read())
