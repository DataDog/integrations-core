# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import mock
import pytest
import requests

from datadog_checks.apache import Apache
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
    resp = requests.get(AUTO_STATUS_URL)
    assert 'ReqPerSec: ' in resp.content.decode('utf-8')


@pytest.fixture
def mock_hide_server_version():
    with mock.patch('datadog_checks.base.utils.http.requests') as req:

        def mock_requests_get_headers(*args, **kwargs):
            r = requests.get(*args, **kwargs)
            old_iter = r.iter_lines
            r.iter_lines = mock.MagicMock()
            r.iter_lines.return_value = (l for l in old_iter(decode_unicode=True) if 'ServerVersion' not in l)
            return r

        req.get = mock_requests_get_headers
        yield


@pytest.fixture
def check():
    return lambda instance: Apache(CHECK_NAME, {}, [instance])
