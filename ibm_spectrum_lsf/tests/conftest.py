# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from unittest import mock

import pytest

from datadog_checks.ibm_spectrum_lsf.client import LSFClient


def get_mock_output(method):
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', f"{method}.txt")
    with open(fixture_path, 'r') as f:
        return f.read().strip(), None, 0


@pytest.fixture
def mock_client():
    client = mock.create_autospec(LSFClient)
    client.lsid.return_value = get_mock_output('lsid')
    client.lsclusters.return_value = get_mock_output('lsclusters')
    client.bhosts.return_value = get_mock_output('bhosts')
    client.lshosts.return_value = get_mock_output('lshosts')
    client.lsload.return_value = get_mock_output('lsload')
    client.bslots.return_value = get_mock_output('bslots')
    client.bqueues.return_value = get_mock_output('bqueues')
    client.bjobs.return_value = get_mock_output('bjobs')
    client.gpuload.return_value = get_mock_output('lsload_gpuload')
    client.bhosts_gpu.return_value = get_mock_output('bhosts_gpu')

    yield client


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {'cluster_name': 'test-cluster'}
