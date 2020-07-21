# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import pytest
from mock import MagicMock, Mock, patch

from .common import LAB_INSTANCE
from .mocked_api import MockedAPI, mock_http_rest_api

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


@pytest.fixture(scope='session')
def dd_environment():
    yield LAB_INSTANCE


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


@pytest.fixture()
def events_only_instance():
    return {
        'use_legacy_check_version': False,
        'host': os.environ.get('VSPHERE_URL', 'FAKE'),
        'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
        'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
        'ssl_verify': False,
        'collect_events_only': True,
    }


@pytest.fixture
def mock_type():
    """
    mock the result of the `type` built-in function to work on mock.MagicMock().
    Without the fixture, type(MagicMock(spec=int)) = MagicMock
    With the fixture, type(MagicMock(spec=int)) = int
    """
    paths = [
        'datadog_checks.vsphere.cache.type',
        'datadog_checks.vsphere.utils.type',
        'datadog_checks.vsphere.vsphere.type',
        'datadog_checks.vsphere.api_rest.type',
    ]
    with ExitStack() as stack:
        new_type_function = lambda x: x.__class__ if isinstance(x, Mock) else type(x)  # noqa: E731
        for path in paths:
            type_function = stack.enter_context(patch(path))
            type_function.side_effect = new_type_function
        yield


@pytest.fixture
def mock_threadpool():
    with patch('datadog_checks.vsphere.vsphere.ThreadPoolExecutor') as pool, patch(
        'datadog_checks.vsphere.vsphere.as_completed', side_effect=lambda x: x
    ):
        pool.return_value.submit = lambda f, args: MagicMock(
            done=MagicMock(return_value=True), result=MagicMock(return_value=f(args)), exception=lambda: None
        )
        yield


@pytest.fixture
def mock_api():
    with patch('datadog_checks.vsphere.vsphere.VSphereAPI', MockedAPI):
        yield


@pytest.fixture
def mock_rest_api():
    with patch('requests.api.request', mock_http_rest_api):
        yield
