# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import urllib.error
import urllib.request
from contextlib import closing
from typing import Any

import pytest

from datadog_checks.apache import Apache
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints, WaitFor
from datadog_checks.dev.http import MockHTTPResponse

from .common import AUTO_STATUS_URL, BASE_URL, CHECK_NAME, HERE, STATUS_CONFIG, STATUS_URL


def http_get(url: str, **kwargs: Any) -> Any:
    req = urllib.request.Request(url, headers=kwargs.get('headers') or {})
    timeout = kwargs.get('timeout')
    if isinstance(timeout, tuple):
        timeout = timeout[-1]

    try:
        if timeout is None:
            return urllib.request.urlopen(req)
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        return e


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
        http_get(BASE_URL).close()


def check_status_page_ready():
    """
    Some status info we need for metrics do not appear immediately.
    This check help waiting for the full status page.
    """
    resp = http_get(AUTO_STATUS_URL)
    try:
        data = resp.read().decode('utf-8')
    finally:
        resp.close()
    assert 'ReqPerSec: ' in data
    assert 'CPULoad: ' in data


@pytest.fixture
def mock_hide_server_version(mock_http):
    def filter_server_version(url, *args, **kwargs):
        with closing(http_get(url, **kwargs)) as r:
            content = '\n'.join(line for line in r.read().decode('utf-8').splitlines() if 'ServerVersion' not in line)
            status_code = r.getcode()
            headers = dict(r.headers)
            response_url = r.geturl()
        return MockHTTPResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            url=response_url,
        )

    mock_http.get.side_effect = filter_server_version
    yield


@pytest.fixture
def check():
    return lambda instance: Apache(CHECK_NAME, {}, [instance])
