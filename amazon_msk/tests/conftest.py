# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest
from six.moves.urllib.parse import urlparse

from .common import read_fixture, stream_fixture


def mock_requests_get(url, *args, **kwargs):
    fixture = 'jmx_metrics.txt' if urlparse(url).port == 11001 else 'node_metrics.txt'
    return mock.MagicMock(status_code=200, iter_lines=lambda **kw: stream_fixture(fixture))


@pytest.fixture
def mock_data():
    with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
        yield


@pytest.fixture
def mock_client():
    client = mock.MagicMock()
    client.list_nodes = mock.MagicMock()
    client.list_nodes.side_effect = lambda *args, **kwargs: json.loads(read_fixture('list_nodes.json'))

    with mock.patch('boto3.client', return_value=client) as m:
        yield m, client


@pytest.fixture
def instance():
    return {
        'cluster_arn': 'arn:aws:kafka:us-east-1:1234567890:cluster/msk-integrate/9dabe192-8f48-4421-8b94-191780c69e1c',
        'tags': ['test:msk'],
    }
