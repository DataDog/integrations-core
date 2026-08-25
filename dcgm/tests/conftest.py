# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
from pathlib import Path

import pytest

from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.dcgm import DcgmCheck
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = common.COMPOSE_FILE
    conditions = [
        CheckDockerLogs(identifier='caddy', patterns=['server running']),
        CheckEndpoints(common.INSTANCE["openmetrics_endpoint"]),
    ]
    with docker_run(compose_file, conditions=conditions):
        yield {
            'instances': [common.INSTANCE],
        }


@pytest.fixture
def instance():
    return copy.deepcopy(common.INSTANCE)


# For Unit Test:
@pytest.fixture
def check(instance):
    return DcgmCheck('dcgm.', {}, [instance])


def _text_response(file_path: str | Path) -> FakeHTTPResponse:
    content = Path(file_path).read_bytes()
    text = content.decode('utf-8')
    return FakeHTTPResponse(
        content=content,
        text=text,
        content_chunks=(content,),
        lines=text.splitlines(),
        headers={'Content-Type': 'text/plain'},
    )


@pytest.fixture()
def mock_metrics(mock_http):
    mock_http.get.return_value = _text_response(Path(__file__).parent / 'fixtures' / 'metrics.txt')
    yield


@pytest.fixture()
def mock_label_remap(mock_http):
    mock_http.get.return_value = _text_response(Path(__file__).parent / 'fixtures' / 'label_remap.txt')
    yield
