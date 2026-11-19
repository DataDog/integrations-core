# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.fs import get_here

from .common import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_FLY_LAB


@pytest.fixture(scope='session')
def dd_environment():
    if not USE_FLY_LAB:
        compose_file = COMPOSE_FILE
        conditions = [
            CheckDockerLogs(identifier='prometheus', patterns=['server running']),
            CheckDockerLogs(identifier='machines-api', patterns=['server running']),
            CheckEndpoints(INSTANCE["machines_api_endpoint"]),
            CheckEndpoints(INSTANCE["openmetrics_endpoint"]),
        ]
        with docker_run(compose_file, conditions=conditions):
            yield INSTANCE
    else:
        yield LAB_INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


@pytest.fixture
def mock_http_get(request, fake_http, fake_http_response, instance):
    """Serve the fixture tree under `fixtures/machines-api` and the OpenMetrics payload through fake_http.

    The fixture tree encodes query parameters as a `key=value` directory, for example `GET/v1/apps/org_slug=test`.
    `http_error` maps request paths to a response that replaces the fixture.
    """
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})

    with open(os.path.join(get_here(), 'fixtures', 'output.txt'), 'rb') as f:
        fake_http_response(instance['openmetrics_endpoint'], f.read())

    root_dir = Path(get_here()) / 'fixtures' / 'machines-api' / 'GET'
    for file in root_dir.rglob('response.json'):
        relative_dir = file.parent.relative_to(root_dir)
        parts = list(relative_dir.parts)
        params = None
        if parts and '=' in parts[-1]:
            key, value = parts.pop().split('=', 1)
            params = {key: value}
        url = '{}/{}'.format(instance['machines_api_endpoint'], '/'.join(parts))
        match_options = {'params': params} if params else None
        fake_http_response(url, json_data=get_json_value_from_file(file), match_options=match_options)

    # Registered last so they take precedence over the fixture tree.
    for path, response in http_error.items():
        fake_http.register_response('GET', instance['machines_api_endpoint'] + path, response)

    return fake_http
