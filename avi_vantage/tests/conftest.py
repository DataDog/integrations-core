# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from pathlib import Path

import pytest

from datadog_checks.base.stubs.http import FakeHTTPClient
from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()

NO_TENANT_METRICS_FOLDER = 'no_tenant'
ADMIN_TENANT_METRICS_FOLDER = 'admin_tenant'
MULTIPLE_TENANTS_METRICS_FOLDER = 'multiple_tenants'
ENTITIES = ('controller', 'pool', 'serviceengine', 'virtualservice')


@pytest.fixture(scope='session')
def dd_environment(integration_instance):
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    # We need a custom condition to wait a bit longer
    with docker_run(
        compose_file=compose_file,
        build=True,
        conditions=[
            CheckDockerLogs(compose_file, 'Running on ', wait=5),
        ],
        attempts=2,
    ):
        yield integration_instance


@pytest.fixture
def get_expected_metrics():
    def _get_metrics(metrics_folder=NO_TENANT_METRICS_FOLDER, endpoint=None):
        with open(os.path.join(HERE, 'compose', 'fixtures', metrics_folder, 'metrics.json')) as f:
            expected_metrics = json.load(f)

        if endpoint is None:
            return expected_metrics

        transformed_expected_metrics = []
        for metric in expected_metrics:
            tags = [t.replace('https://34.123.32.255/', endpoint) for t in metric['tags']]
            transformed_expected_metrics.append(
                {'name': metric['name'], 'type': metric['type'], 'value': metric['value'], 'tags': tags}
            )

        return transformed_expected_metrics

    return _get_metrics


@pytest.fixture(autouse=True)
def fake_http_max_line_size(mocker):
    # The check hands its own client to the scrapers, so they read max_line_size from a client the
    # OpenMetrics scraper never configured. The real client defaults it to None, the fake has no such attribute.
    mocker.patch.object(FakeHTTPClient, 'max_line_size', None, create=True)


@pytest.fixture
def mock_client(fake_http, fake_http_response):
    """Register one controller session for the unit instance, scraping each entity once."""
    base_url = 'https://34.123.32.255'

    def register(metrics_folder=NO_TENANT_METRICS_FOLDER, tenant_query=''):
        fake_http_response(f'{base_url}/login', method='POST', json_data={'results': []})
        # Version metadata is best effort, the unit tests only cover the scraped metrics.
        fake_http_response(f'{base_url}/api/cluster/version', status_code=404)
        for entity in ENTITIES:
            url = f'{base_url}/api/analytics/prometheus-metrics/{entity}'
            if tenant_query:
                url += f'/?{tenant_query}'
            fake_http_response(
                url, (Path(HERE) / 'compose' / 'fixtures' / metrics_folder / f'{entity}_metrics').read_bytes()
            )

    yield register
    fake_http.assert_all_responses_consumed()


@pytest.fixture(scope='session')
def unit_instance():
    return {
        'avi_controller_url': 'https://34.123.32.255/',
        'tls_verify': False,
        'username': 'admin',
    }


@pytest.fixture(scope='session')
def integration_instance():
    return {'avi_controller_url': f'http://{get_docker_hostname()}:5000/', 'username': 'user1', 'password': 'dummyPass'}
