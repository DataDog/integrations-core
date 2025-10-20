# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest


def get_mock_output(method):
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', f"{method}.txt")
    with open(fixture_path, 'r') as f:
        return f.read().strip(), None, 0


@pytest.fixture
def mock_client():
    client = mock.MagicMock()
    client.lsid.side_effect = lambda: get_mock_output('lsid')
    client.lsclusters.side_effect = lambda: get_mock_output('lsclusters')
    client.bhosts.side_effect = lambda: get_mock_output('bhosts')
    client.lshosts.side_effect = lambda: get_mock_output('lshosts')
    client.lsload.side_effect = lambda: get_mock_output('lsload')

    yield client


@pytest.fixture(scope='session')
def dd_environment():
    yield


@pytest.fixture
def instance():
    return {'cluster_name': 'test-cluster'}
