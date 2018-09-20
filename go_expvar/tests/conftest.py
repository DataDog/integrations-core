# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
import mock
import os
import requests
import logging
import json

from . import common

from datadog_checks.dev import docker_run
from datadog_checks.go_expvar import GoExpvar

log = logging.getLogger(__file__)


@pytest.fixture
def go_expvar_mock():
    filepath = os.path.join(common.HERE, 'fixtures', 'expvar_output')
    with open(filepath, 'r') as f:
        data = f.read()
    json_data = json.loads(data)
    with mock.patch('datadog_checks.go_expvar.GoExpvar._get_data', return_value=json_data):
        yield


@pytest.fixture(scope="session")
def spin_up_go_expvar():
    """
    Spin up a simple container that contains a simple go expvar app
    """

    with docker_run(
        os.path.join(common.HERE, 'compose', 'docker-compose.yaml'),
        endpoints=[common.URL]
    ):
        for _ in range(9):
            requests.get(common.URL + "?user=123456")
        yield


@pytest.fixture
def check():
    return GoExpvar(common.CHECK_NAME, {}, {})
