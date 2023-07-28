# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()

INFERENCE_API_PORT = "8080"
MANAGEMENT_API_PORT = "8081"
OPENMETRICS_PORT = "8082"

INFERENCE_API_URL = f"http://{get_docker_hostname()}:{INFERENCE_API_PORT}"
MANAGEMENT_API_URL = f"http://{get_docker_hostname()}:{MANAGEMENT_API_PORT}"
OPENMETRICS_ENDPOINT = f"http://{get_docker_hostname()}:{OPENMETRICS_PORT}/metrics"

OPENMETRICS_INSTANCE = {
    "openmetrics_endpoint": OPENMETRICS_ENDPOINT,
}

INFERENCE_INSTANCE = {
    "inference_api_url": INFERENCE_API_URL,
}

MANAGEMENT_INSTANCE = {
    "management_api_url": MANAGEMENT_API_URL,
}

MOCKED_OPENMETRICS_INSTANCE = {
    "openmetrics_endpoint": "http://torchserve:8082/metrics",
}

MOCKED_INFERENCE_INSTANCE = {
    "inference_api_url": "http://torchserve:8080",
}

MOCKED_MANAGEMENT_INSTANCE = {
    "management_api_url": "http://torchserve:8081",
}

E2E_METADATA = {
    'env_vars': {
        'DD_LOGS_ENABLED': 'true',
    },
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
