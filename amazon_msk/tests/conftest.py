# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from copy import deepcopy
from pathlib import Path

import mock
import pytest

from datadog_checks.dev import docker_run

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
def mock_data(fake_http, fake_http_response):
    expected = []

    def register(instance: dict) -> None:
        for node in json.loads(common.read_api_fixture())['NodeInfoList']:
            broker = node.get('BrokerNodeInfo')
            if not broker:
                continue
            for endpoint in broker['Endpoints']:
                for exporter, default_port in [('jmx', common.JMX_PORT), ('node', common.NODE_PORT)]:
                    port = instance.get(f'{exporter}_exporter_port', default_port)
                    if not port:
                        continue
                    url = f"http://{endpoint}:{port}{instance.get('prometheus_metrics_path', '/metrics')}"
                    fake_http_response(url, Path(common.get_metrics_fixture_path(exporter)).read_bytes())
                    expected.append(('GET', url))

    yield register
    fake_http.assert_all_responses_consumed()
    assert [(r.method, r.url) for r in fake_http.requests] == expected


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
    return deepcopy(common.INSTANCE)


@pytest.fixture
def instance_legacy():
    return deepcopy(common.INSTANCE_LEGACY)
