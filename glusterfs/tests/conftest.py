# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {}


@pytest.fixture()
def mock_gstatus_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'gstatus.json')
    with open(f_name) as f:
        data = f.read()
    with mock.patch('datadog_checks.glusterfs.check.get_subprocess_output', return_value=(data, '', 0)):
        yield
