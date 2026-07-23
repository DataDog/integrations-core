# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import json
import logging
import os
import urllib.error
import urllib.request

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.go_expvar import GoExpvar

from . import common

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
def dd_environment():
    """
    Spin up a simple container that contains a simple go expvar app
    """

    with docker_run(os.path.join(common.HERE, 'compose', 'docker-compose.yaml'), endpoints=[common.URL]):
        for _ in range(9):
            try:
                response = urllib.request.urlopen(common.URL + "?user=123456")
            except urllib.error.HTTPError as e:
                e.close()
            else:
                response.close()
        yield common.INSTANCE


@pytest.fixture
def check():
    return GoExpvar(common.CHECK_NAME, {}, [common.INSTANCE])
