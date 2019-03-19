# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest
import requests

from datadog_checks.apache import Apache
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckEndpoints

from .common import (
    HERE, STATUS_URL, STATUS_CONFIG, BASE_URL, CHECK_NAME
)


@pytest.fixture(scope="session")
def dd_environment():
    env = {
        'APACHE_CONFIG': os.path.join(HERE, 'compose', 'httpd.conf'),
        'APACHE_DOCKERFILE': os.path.join(HERE, 'compose', 'Dockerfile'),
    }
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'apache.yaml'),
        env_vars=env,
        conditions=[
            CheckEndpoints([STATUS_URL]),
            generate_metrics,
        ],
        sleep=20
    ):
        yield STATUS_CONFIG


def generate_metrics():
    for _ in range(0, 100):
        requests.get(BASE_URL)


@pytest.fixture
def check():
    return Apache(CHECK_NAME, {}, {})
