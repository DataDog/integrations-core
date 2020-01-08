# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest
from mock import MagicMock, Mock, patch
from tests.mocked_api import MockedAPI


@pytest.fixture()
def realtime_instance():
    return {
        'collection_level': 4,
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
    }


@pytest.fixture()
def historical_instance():
    return {
        'collection_level': 1,
        'empty_default_hostname': True,
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
        'collection_type': 'historical',
    }


@pytest.fixture
def mock_type():
    with patch('datadog_checks.vsphere.cache.type') as cache_type, patch(
        'datadog_checks.vsphere.utils.type'
    ) as utils_type, patch('datadog_checks.vsphere.vsphere.type') as vsphere_type:
        new_type_function = lambda x: x.__class__ if isinstance(x, Mock) else type(x)  # noqa: E731
        cache_type.side_effect = new_type_function
        utils_type.side_effect = new_type_function
        vsphere_type.side_effect = new_type_function
        yield


@pytest.fixture
def mock_threadpool():
    with patch('datadog_checks.vsphere.vsphere.ThreadPoolExecutor') as pool:
        pool.return_value.submit = lambda f, args: MagicMock(
            done=MagicMock(return_value=True), result=MagicMock(return_value=f(args))
        )
        yield


@pytest.fixture
def mock_api():
    with patch('datadog_checks.vsphere.vsphere.VSphereAPI', MockedAPI):
        yield
