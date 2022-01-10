# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest
from six.moves.urllib.parse import urlparse

from datadog_checks.dev import docker_run
from datadog_checks.dev.http import MockResponse

from . import common


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(
        common.COMPOSE_FILE,
        endpoints=[
            'http://{}:{}/metrics'.format(common.HOST, common.JMX_PORT),
            'http://{}:{}/metrics'.format(common.HOST, common.NODE_PORT),
        ],
    ):
        yield common.INSTANCE, common.E2E_METADATA


def mock_requests_get(url, *args, **kwargs):
    exporter_type = 'jmx' if urlparse(url).port == common.JMX_PORT else 'node'
    return MockResponse(file_path=common.get_metrics_fixture_path(exporter_type))


@pytest.fixture
def mock_data():
    with mock.patch('requests.get', side_effect=mock_requests_get, autospec=True):
        yield


@pytest.fixture
def mock_client():
    client = mock.MagicMock()
    client.list_nodes = mock.MagicMock()
    client.list_nodes.side_effect = lambda *args, **kwargs: json.loads(common.read_api_fixture())

    with mock.patch('boto3.client', return_value=client) as m:
        yield m, client


@pytest.fixture
def mock_e2e_client():
    client = mock.MagicMock()
    client.list_nodes = mock.MagicMock()
    client.list_nodes.side_effect = lambda *args, **kwargs: json.loads(common.read_e2e_api_fixture())

    with mock.patch('boto3.client', return_value=client) as m:
        yield m, client


@pytest.fixture
def instance():
    return common.INSTANCE


@pytest.fixture
def instance_legacy():
    return common.INSTANCE_LEGACY
