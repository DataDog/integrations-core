# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import json
import logging
import os

import pytest
import requests

from datadog_checks.dev import docker_run
from datadog_checks.go_expvar import GoExpvar

from . import common

log = logging.getLogger(__file__)


@pytest.fixture
def go_expvar_mock(fake_http_response):
    filepath = os.path.join(common.HERE, 'fixtures', 'expvar_output')
    with open(filepath, 'r') as f:
        json_data = json.load(f)
    fake_http_response(common.URL_WITH_PATH, json_data=json_data)


@pytest.fixture(scope="session")
def dd_environment():
    """
    Spin up a simple container that contains a simple go expvar app
    """

    with docker_run(os.path.join(common.HERE, 'compose', 'docker-compose.yaml'), endpoints=[common.URL]):
        for _ in range(9):
            requests.get(common.URL + "?user=123456")
        yield common.INSTANCE


@pytest.fixture
def check():
    return GoExpvar(common.CHECK_NAME, {}, [common.INSTANCE])
