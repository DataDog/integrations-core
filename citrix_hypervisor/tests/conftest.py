# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.dev import docker_run

from . import common


def _fixture_response(path: str) -> FakeHTTPResponse:
    with open(path, 'rb') as response_file:
        content = response_file.read()
    text = content.decode('utf-8')
    try:
        json_result = json.loads(text)
    except json.JSONDecodeError as error:
        return FakeHTTPResponse(content=content, text=text, json_error=error)
    return FakeHTTPResponse(content=content, text=text, json_result=json_result)


def _not_found_response() -> FakeHTTPResponse:
    return FakeHTTPResponse(
        status_code=404,
        status_error=HTTPClientStatusError('404 Client Error'),
        reason='Not Found',
    )


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=[
            '{}/rrd_updates'.format(common.E2E_INSTANCE[0]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[1]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[2]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[3]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[4]['url']),
            '{}/rrd_updates'.format(common.E2E_INSTANCE[5]['url']),
        ],
    ):
        yield common.E2E_INSTANCE


@pytest.fixture(params=common.MOCKED_INSTANCES, ids=common.MOCKED_INSTANCE_IDS)
def instance(request):
    return request.param


def mock_requests_get(url, *args, **kwargs):
    url_parts = url.split('/')
    print(url_parts)

    if url_parts[0] == 'wrong':
        return _not_found_response()

    json_file = f"rrd_updates_{url_parts[0]}.json" if url_parts[1] == "rrd_updates" else f"{url_parts[1]}.json"
    path = os.path.join(common.HERE, 'fixtures', 'standalone', json_file)
    if not os.path.exists(path):
        return _not_found_response()

    return _fixture_response(path)


@pytest.fixture
def mock_responses(mock_http):
    mock_http.get.side_effect = mock_requests_get
    yield
