# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
from pathlib import Path

import pytest

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


@pytest.fixture()
def mock_metrics(fake_http, fake_http_response, instance):
    fake_http_response(
        instance['openmetrics_endpoint'],
        (Path(__file__).parent / 'fixtures' / 'metrics.txt').read_bytes(),
        match_options={'stream': True},
        headers={'Content-Type': 'text/plain'},
    )
    yield
    fake_http.assert_all_responses_consumed()


@pytest.fixture()
def mock_label_remap(fake_http, fake_http_response, instance):
    for _ in range(2):
        fake_http_response(
            instance['openmetrics_endpoint'],
            (Path(__file__).parent / 'fixtures' / 'label_remap.txt').read_bytes(),
            match_options={'stream': True},
            headers={'Content-Type': 'text/plain'},
        )
    yield
    fake_http.assert_all_responses_consumed()
