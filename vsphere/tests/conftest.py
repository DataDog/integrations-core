# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest
import mock

from datadog_checks.vsphere import VSphereCheck

from .utils import disable_thread_pool, get_mocked_server


def _instance():
    """
    Create a default instance, used by multiple fixtures
    """
    return {'name': 'vsphere_mock', 'tags': ['foo:bar']}


@pytest.fixture
def instance():
    """
    Return a default instance
    """
    return _instance()


@pytest.fixture
def vsphere():
    """
    Provide a check instance with mocked parts
    """
    # mock the server
    server_mock = get_mocked_server()
    # create a check instance
    check = VSphereCheck('vsphere', {}, {}, [_instance()])
    # patch the check instance
    check._get_server_instance = mock.MagicMock(return_value=server_mock)
    # return the check after disabling the thread pool
    return disable_thread_pool(check)


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator
