# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run

from . import common


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
        return MockHTTPResponse(status_code=404)

    json_file = f"rrd_updates_{url_parts[0]}.json" if url_parts[1] == "rrd_updates" else f"{url_parts[1]}.json"
    path = os.path.join(common.HERE, 'fixtures', 'standalone', json_file)
    if not os.path.exists(path):
        return MockHTTPResponse(status_code=404)

    return MockHTTPResponse(file_path=path)


@pytest.fixture
def mock_responses(mock_http):
    mock_http.get.side_effect = mock_requests_get
    yield
