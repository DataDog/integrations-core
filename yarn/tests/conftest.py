# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
from copy import deepcopy

import pytest
from mock import patch
from requests.exceptions import SSLError

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.yarn import YarnCheck

from .common import (
    HERE,
    INSTANCE_INTEGRATION,
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APPS_URL,
    YARN_CLUSTER_METRICS_URL,
    YARN_NODES_URL,
    YARN_SCHEDULER_URL,
)


@pytest.fixture(scope="session")
def dd_environment():
    with docker_run(
        compose_file=os.path.join(HERE, "compose", "docker-compose.yaml"),
        mount_logs=True,
        conditions=[CheckEndpoints(INSTANCE_INTEGRATION['resourcemanager_uri'], attempts=240)],
    ):
        yield INSTANCE_INTEGRATION


@pytest.fixture
def check():
    return lambda instance: YarnCheck('yarn', {}, [instance])


@pytest.fixture
def instance():
    return deepcopy(INSTANCE_INTEGRATION)


@pytest.fixture
def mocked_request():
    with patch("requests.get", new=requests_get_mock):
        yield


@pytest.fixture
def mocked_auth_request():
    def requests_auth_get(*args, **kwargs):
        # Make sure we're passing in authentication
        assert 'auth' in kwargs, 'Missing "auth" argument in requests.get(...) call'

        # Make sure we've got the correct username and password
        assert kwargs['auth'] == (TEST_USERNAME, TEST_PASSWORD), "Incorrect username or password in requests.get"

        # Return mocked request.get(...)
        return requests_get_mock(*args, **kwargs)

    with patch("requests.get", new=requests_auth_get):
        yield


@pytest.fixture
def mocked_bad_cert_request():
    """
    Mock request.get to an endpoint with a badly configured ssl cert
    """

    def requests_bad_cert_get(*args, **kwargs):
        # Make sure we're passing in the 'verify' argument
        assert 'verify' in kwargs, 'Missing "verify" argument in requests.get(...) call'

        if kwargs['verify']:
            raise SSLError("certificate verification failed for {}".format(args[0]))

        # Return the actual response
        return requests_get_mock(*args, **kwargs)

    with patch("requests.get", new=requests_bad_cert_get):
        yield


def requests_get_mock(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return json.loads(self.json_data)

        def raise_for_status(self):
            return True

    if args[0] == YARN_CLUSTER_METRICS_URL:
        yarn_cluster_metrics = os.path.join(HERE, "fixtures", "cluster_metrics")
        with open(yarn_cluster_metrics, "r") as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_APPS_URL:
        yarn_apps_metrics = os.path.join(HERE, "fixtures", "apps_metrics")
        with open(yarn_apps_metrics, "r") as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_NODES_URL:
        yarn_nodes_metrics = os.path.join(HERE, "fixtures", "nodes_metrics")
        with open(yarn_nodes_metrics, "r") as f:
            body = f.read()
            return MockResponse(body, 200)

    elif args[0] == YARN_SCHEDULER_URL:
        yarn_scheduler_metrics = os.path.join(HERE, "fixtures", "scheduler_metrics")
        with open(yarn_scheduler_metrics, "r") as f:
            body = f.read()
            return MockResponse(body, 200)
