# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import mock
import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import read_file

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


@pytest.fixture
def mock_data(fake_http_response):
    # The check scrapes both exporter ports of every broker endpoint that `list_nodes` reports.
    # The custom metric path test scrapes `/` instead of the default `/metrics`.
    exporter_bodies = {
        port: read_file(common.get_metrics_fixture_path(exporter_type))
        for port, exporter_type in ((common.JMX_PORT, 'jmx'), (common.NODE_PORT, 'node'))
    }
    for node_info in json.loads(common.read_api_fixture())['NodeInfoList']:
        for endpoint in (node_info.get('BrokerNodeInfo') or {}).get('Endpoints', []):
            for port, body in exporter_bodies.items():
                for path in ('/metrics', '/'):
                    fake_http_response('http://{}:{}{}'.format(endpoint, port, path), body)


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
