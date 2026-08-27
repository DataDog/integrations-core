# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.dev.fs import get_here

from .common import INSTANCE


@pytest.fixture
def instance():
    return INSTANCE


@pytest.fixture(scope="session")
def dd_environment():
    yield INSTANCE


def _json_response(file_path: str) -> FakeHTTPResponse:
    with open(file_path, 'r') as file:
        return FakeHTTPResponse(json_result=json.load(file))


@pytest.fixture
def mock_http_get(request, fake_http):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    overrides = param.get('http_error', {})
    fixtures_dir = os.path.join(get_here(), 'fixtures', 'GET')
    api_endpoint = INSTANCE['proxmox_server']
    response_paths = (
        ('/version', 'api2/json/version/response.json', None),
        ('/cluster/resources', 'api2/json/cluster/resources/response.json', None),
        (
            '/nodes/ip-122-82-3-112/qemu/100/agent/get-host-name',
            'api2/json/nodes/ip-122-82-3-112/qemu/100/agent/get-host-name/response.json',
            None,
        ),
        ('/cluster/metrics/export', 'api2/json/cluster/metrics/export/response.json', None),
        ('/cluster/ha/status/current', 'api2/json/cluster/ha/status/current/response.json', None),
        (
            '/nodes/ip-122-82-3-112/tasks',
            'api2/json/nodes/ip-122-82-3-112/tasks/since=1752552000/response.json',
            {'params': {'since': 1752552000}},
        ),
    )

    for path, fixture_path, match_options in response_paths:
        response = overrides.get(f'/api2/json{path}')
        if response is None:
            response = _json_response(os.path.join(fixtures_dir, fixture_path))
        fake_http.register_response(
            'GET',
            f'{api_endpoint}{path}',
            response,
            match_options=match_options,
        )

    return fake_http
