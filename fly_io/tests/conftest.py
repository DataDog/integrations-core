# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from collections.abc import Iterator

import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient, RecordedRequest
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.fs import get_here

from .common import COMPOSE_FILE, INSTANCE, LAB_INSTANCE, USE_FLY_LAB

API_ROUTES = (
    ('/v1/apps', 'v1/apps/org_slug=test/response.json', {'params': {'org_slug': 'test'}}),
    ('/v1/apps/example-app-1', 'v1/apps/example-app-1/response.json', None),
    ('/v1/apps/example-app-1/machines', 'v1/apps/example-app-1/machines/response.json', None),
    ('/v1/apps/example-app-1/volumes', 'v1/apps/example-app-1/volumes/response.json', None),
    ('/v1/apps/example-app-2', 'v1/apps/example-app-2/response.json', None),
    ('/v1/apps/example-app-2/machines', None, None),
    ('/v1/apps/example-app-2/volumes', None, None),
    ('/v1/apps/example-app-3', 'v1/apps/example-app-3/response.json', None),
    ('/v1/apps/example-app-3/machines', 'v1/apps/example-app-3/machines/response.json', None),
    ('/v1/apps/example-app-3/volumes', None, None),
    ('/v1/apps/example-app-4', 'v1/apps/example-app-4/response.json', None),
    ('/v1/apps/example-app-4/machines', None, None),
    ('/v1/apps/example-app-4/volumes', None, None),
)
API_REQUEST_SETS = {
    'full': API_ROUTES,
    'apps_only': API_ROUTES[:1],
    'none': (),
}


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


@pytest.fixture
def mock_http_get(request, fake_http: FakeHTTPClient, fake_http_response) -> Iterator[FakeHTTPClient]:
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    response_overrides = param.get('response_overrides', {})
    request_set = param.get('request_set', 'full')
    fixtures_dir = os.path.join(get_here(), 'fixtures')
    intended_requests: list[RecordedRequest] = []

    with open(os.path.join(fixtures_dir, 'output.txt'), 'rb') as response_file:
        openmetrics_content = response_file.read()
    fake_http_response(
        INSTANCE['openmetrics_endpoint'],
        openmetrics_content,
        match_options={'stream': True},
    )
    intended_requests.append(RecordedRequest('GET', INSTANCE['openmetrics_endpoint'], {'stream': True}))

    api_endpoint = INSTANCE['machines_api_endpoint']
    for path, fixture_path, match_options in API_REQUEST_SETS[request_set]:
        url = f'{api_endpoint}{path}'
        response = response_overrides.get(path)
        if response is not None:
            fake_http.register_response('GET', url, response, match_options=match_options)
        elif fixture_path is None:
            response = fake_http_response(
                url,
                status_code=404,
                match_options=match_options,
            )
            response.url = url
        else:
            with open(os.path.join(fixtures_dir, 'machines-api', 'GET', fixture_path), 'r') as response_file:
                response_data = json.load(response_file)
            fake_http_response(url, method='GET', json_data=response_data, match_options=match_options)
        intended_requests.append(RecordedRequest('GET', url, match_options or {}))

    yield fake_http

    fake_http.assert_requests(intended_requests)
    fake_http.assert_all_responses_consumed()
