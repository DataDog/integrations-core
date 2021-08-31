# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.dev.http import MockResponse

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return common.MOCKED_INSTANCE


def mock_requests_get(url, *args, **kwargs):
    url_parts = url.split('/')

    if url_parts[0] != 'mocked':
        return MockResponse(status_code=404)

    path = os.path.join(common.HERE, 'fixtures', '{}.json'.format(url_parts[1]))
    if not os.path.exists(path):
        return MockResponse(status_code=404)

    return MockResponse(file_path=path)


@pytest.fixture
def mock_responses():
    with mock.patch('requests.get', side_effect=mock_requests_get):
        yield


@pytest.fixture
def host_is_master():
    with mock.patch(
        'datadog_checks.citrix_hypervisor.CitrixHypervisorCheck.open_session',
        return_value={'Status': 'Success', 'Value': 'OpaqueRef:c908ccc4-4355-4328-b07d-c85dc7242b03'},
    ):
        yield


@pytest.fixture
def host_is_slave():
    with mock.patch(
        'datadog_checks.citrix_hypervisor.CitrixHypervisorCheck.open_session',
        return_value={'Status': 'Failure', 'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102']},
    ):
        yield
