# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from collections.abc import Callable, Iterator

import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
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


@pytest.fixture
def mock_responses(fake_http: FakeHTTPClient) -> Iterator[Callable[..., None]]:
    fixtures_dir = os.path.join(common.HERE, 'fixtures', 'standalone')
    host_response_path = os.path.join(fixtures_dir, 'host_rrd.json')
    host_options = {'params': {'json': 'true'}}
    expected_requests: list[RecordedRequest] = []

    def register(base_url: str, *, include_host: bool = True, metrics_start: int | None = None) -> None:
        if include_host:
            host_response = _not_found_response() if base_url == 'wrong' else _fixture_response(host_response_path)
            fake_http.register_response(
                'GET',
                f'{base_url}/host_rrd',
                host_response,
                match_options=host_options,
            )
            expected_requests.append(RecordedRequest('GET', f'{base_url}/host_rrd', host_options))

        if metrics_start is None:
            return

        if base_url == 'wrong':
            metrics_response = _not_found_response()
        else:
            metrics_response_path = os.path.join(fixtures_dir, f'rrd_updates_{base_url}.json')
            metrics_response = _fixture_response(metrics_response_path)
        metrics_options = {'params': {'start': metrics_start, 'host': 'true', 'json': 'true'}}
        fake_http.register_response(
            'GET',
            f'{base_url}/rrd_updates',
            metrics_response,
            match_options=metrics_options,
        )
        expected_requests.append(RecordedRequest('GET', f'{base_url}/rrd_updates', metrics_options))

    yield register

    fake_http.assert_requests(expected_requests)
    fake_http.assert_all_responses_consumed()
