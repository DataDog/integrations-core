# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from copy import deepcopy
from urllib.parse import urljoin

import pytest
from mock import patch
from requests.exceptions import SSLError

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.yarn import YarnCheck
from datadog_checks.yarn.yarn import YARN_APPS_PATH, YARN_CLUSTER_METRICS_PATH, YARN_NODES_PATH, YARN_SCHEDULER_PATH

from .common import (
    FIXTURE_DIR,
    HERE,
    INSTANCE_INTEGRATION,
    YARN_APPS_URL,
    YARN_CLUSTER_METRICS_URL,
    YARN_NODES_URL,
    YARN_SCHEDULER_URL,
)


@pytest.fixture(scope="session")
def dd_environment():
    conditions = [
        CheckEndpoints(urljoin(INSTANCE_INTEGRATION['resourcemanager_uri'], endpoint), attempts=240)
        for endpoint in (YARN_APPS_PATH, YARN_CLUSTER_METRICS_PATH, YARN_NODES_PATH, YARN_SCHEDULER_PATH)
    ]

    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        mount_logs=True,
        conditions=conditions,
        sleep=30,
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: YarnCheck('yarn', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


@pytest.fixture
def mocked_auth_request(mock_http):
    mock_http.get.side_effect = requests_get_mock
    yield


@pytest.fixture
def mocked_bad_cert_request():
    """Keep requests.Session.get patch — tests verify=True vs verify=False which requires the real HTTP wrapper."""

    def requests_bad_cert_get(session, *args, **kwargs):
        if kwargs.get('verify', True):
            raise SSLError("certificate verification failed for {}".format(args[0]))
        return requests_get_mock(args[0], *args[1:], **kwargs)

    with patch("requests.Session.get", new=requests_bad_cert_get):
        yield


def requests_get_mock(url, *args, **kwargs):
    if url == YARN_CLUSTER_METRICS_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'cluster_metrics'))
    elif url == YARN_APPS_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'apps_metrics'))
    elif url == YARN_NODES_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'nodes_metrics'))
    elif url == YARN_SCHEDULER_URL:
        return MockHTTPResponse(file_path=os.path.join(FIXTURE_DIR, 'scheduler_metrics'))
