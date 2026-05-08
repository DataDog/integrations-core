# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest
import requests

from datadog_checks.apache import Apache
from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor

from .common import AUTO_STATUS_URL, BASE_URL, CHECK_NAME, HERE, STATUS_CONFIG, STATUS_URL


@pytest.fixture(scope="session")
def dd_environment():
    env = {
        'APACHE_CONFIG': os.path.join(HERE, 'compose', 'httpd.conf'),
        'APACHE_DOCKERFILE': os.path.join(HERE, 'compose', 'Dockerfile'),
    }
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'apache.yaml'),
        env_vars=env,
        conditions=[CheckEndpoints([STATUS_URL]), generate_metrics, WaitFor(check_status_page_ready)],
        mount_logs=True,
        sleep=20,
    ):
        yield STATUS_CONFIG


def generate_metrics():
    for _ in range(0, 100):
        requests.get(BASE_URL)


def check_status_page_ready():
    """
    Some status info we need for metrics do not appear immediately.
    This check help waiting for the full status page.
    """
    resp = requests.get(AUTO_STATUS_URL)
    data = resp.content.decode('utf-8')
    assert 'ReqPerSec: ' in data
    assert 'CPULoad: ' in data


@pytest.fixture
def mock_hide_server_version(mock_http):
    def filter_server_version(url, *args, **kwargs):
        r = requests.get(url, **kwargs)
        content = '\n'.join(line for line in r.text.splitlines() if 'ServerVersion' not in line)
        return MockHTTPResponse(content=content, headers=dict(r.headers))

    mock_http.get.side_effect = filter_server_version
    yield


@pytest.fixture
def check():
    return lambda instance: Apache(CHECK_NAME, {}, [instance])
