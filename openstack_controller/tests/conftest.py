# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
import tempfile
from copy import deepcopy
from urllib.parse import urlparse

import mock
import pytest

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import CHECK_NAME, CONFIG, CONFIG_NOVA_MICROVERSION_LATEST, USE_OPENSTACK_SANDBOX
from .ssh_tunnel import socks_proxy
from .terraform import terraform_run


def mock_endpoint_response_time(endpoint):
    mock_total_seconds = mock.MagicMock(return_value=3)
    mock_elapsed = mock.MagicMock()
    mock_elapsed.total_seconds = mock_total_seconds
    mock_endpoint = MockResponse(
        file_path=os.path.join(get_here(), endpoint),
        status_code=200,
    )
    mock_endpoint.elapsed = mock_elapsed
    return mock_endpoint


@pytest.fixture(scope='session')
def dd_environment():
    if USE_OPENSTACK_SANDBOX:
        with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
            ip = outputs['ip']['value']
            internal_ip = outputs['internal_ip']['value']
            private_key = outputs['ssh_private_key']['value']
            instance = {
                'keystone_server_url': 'http://{}/identity'.format(internal_ip),
                # 'domain_id': '03e40b01788d403e98e4b9a20210492e',
                # 'username': 'new_admin',
                'username': 'admin',
                'password': 'password',
                'ssl_verify': False,
                'nova_microversion': 'latest',
            }
            config_file = os.path.join(tempfile.gettempdir(), 'openstack_controller_instance.json')
            with open(config_file, 'wb') as f:
                output = json.dumps(instance).encode('utf-8')
                f.write(output)
            env = dict(os.environ)
            with socks_proxy(
                ip,
                re.sub('([.@])', '_', env['TF_VAR_user']).lower(),
                private_key,
            ) as socks:
                print("socks: %s", socks)
                socks_ip, socks_port = socks
                agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
                yield instance, agent_config
    else:
        compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
        conditions = [
            CheckDockerLogs(identifier='openstack-keystone', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-nova', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-neutron', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-ironic', patterns=['server running']),
        ]
        with docker_run(compose_file, conditions=conditions):
            instance = {
                'keystone_server_url': 'http://127.0.0.1:8080/identity',
                'username': 'admin',
                'password': 'password',
                'ssl_verify': False,
            }
            yield instance


@pytest.fixture
def instance():
    return deepcopy(CONFIG)


@pytest.fixture
def instance_nova_microversion_latest():
    return deepcopy(CONFIG_NOVA_MICROVERSION_LATEST)


@pytest.fixture
def check(instance):
    return OpenStackControllerCheck(CHECK_NAME, {}, [instance])


@pytest.fixture
def requests_wrapper():
    instance = {'timeout': 10, 'ssl_verify': False}
    yield RequestsWrapper(instance, {})


@pytest.fixture
def mock_http_exception():
    with mock.patch('datadog_checks.openstack_controller.check.OpenStackControllerCheck.http') as http:
        http.get.side_effect = [Exception()]
        yield http


@pytest.fixture
def mock_http_error():
    with mock.patch('datadog_checks.openstack_controller.check.OpenStackControllerCheck.http') as http:
        http.get.side_effect = [MockResponse(status_code=500)]
        yield http


@pytest.fixture
def mock_http_nova_down():
    with mock.patch('datadog_checks.openstack_controller.check.OpenStackControllerCheck.http') as http:
        http.get.side_effect = [
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/get.json'),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/auth/projects/get.json'),
                status_code=200,
            ),
            MockResponse(status_code=500),
            mock_endpoint_response_time('fixtures/networking/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/networking/v2.0/quotas/1e6e233e637d4d55a50a62b63398ad15/get.json',
                ),
                status_code=200,
            ),
            MockResponse(status_code=500),
            mock_endpoint_response_time('fixtures/networking/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/networking/v2.0/quotas/6e39099cccde4f809b003d9e0dd09304/get.json',
                ),
                status_code=200,
            ),
        ]
        http.post.side_effect = [
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/auth/tokens/os_token.json'),
                status_code=200,
                headers={'X-Subject-Token': 'token_test1234'},
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(), 'fixtures/identity/v3/auth/tokens/1e6e233e637d4d55a50a62b63398ad15_token.json'
                ),
                status_code=200,
                headers={'X-Subject-Token': 'token_project_1'},
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(), 'fixtures/identity/v3/auth/tokens/6e39099cccde4f809b003d9e0dd09304_token.json'
                ),
                status_code=200,
                headers={'X-Subject-Token': 'token_project_2'},
            ),
        ]
        yield http


@pytest.fixture
def mock_http_latest():
    with mock.patch('datadog_checks.openstack_controller.check.OpenStackControllerCheck.http') as http:
        http.get.side_effect = [
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/get.json'),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/auth/projects/get.json'),
                status_code=200,
            ),
            mock_endpoint_response_time('fixtures/compute/latest/v2.1/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/limits?tenant_id=1e6e233e637d4d55a50a62b63398ad15/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-quota-sets/1e6e233e637d4d55a50a62b63398ad15/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/flavors/detail/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-hypervisors/detail?with_servers=true/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-aggregates/get.json',
                ),
                status_code=200,
            ),
            mock_endpoint_response_time('fixtures/networking/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/networking/v2.0/quotas/1e6e233e637d4d55a50a62b63398ad15/get.json',
                ),
                status_code=200,
            ),
            mock_endpoint_response_time('fixtures/compute/latest/v2.1/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/limits?tenant_id=6e39099cccde4f809b003d9e0dd09304/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-quota-sets/6e39099cccde4f809b003d9e0dd09304/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/servers/2c653a68-b520-4582-a05d-41a68067d76c/diagnostics/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/flavors/detail/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-hypervisors/detail?with_servers=true/get.json',
                ),
                status_code=200,
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/compute/latest/v2.1/os-aggregates/get.json',
                ),
                status_code=200,
            ),
            mock_endpoint_response_time('fixtures/networking/get.json'),
            MockResponse(
                file_path=os.path.join(
                    get_here(),
                    'fixtures/networking/v2.0/quotas/6e39099cccde4f809b003d9e0dd09304/get.json',
                ),
                status_code=200,
            ),
        ]
        http.post.side_effect = [
            MockResponse(
                file_path=os.path.join(get_here(), 'fixtures/identity/v3/auth/tokens/os_token.json'),
                status_code=200,
                headers={'X-Subject-Token': 'token_test1234'},
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(), 'fixtures/identity/v3/auth/tokens/1e6e233e637d4d55a50a62b63398ad15_token.json'
                ),
                status_code=200,
                headers={'X-Subject-Token': 'token_project_1'},
            ),
            MockResponse(
                file_path=os.path.join(
                    get_here(), 'fixtures/identity/v3/auth/tokens/6e39099cccde4f809b003d9e0dd09304_token.json'
                ),
                status_code=200,
                headers={'X-Subject-Token': 'token_project_2'},
            ),
        ]
        yield http


def mock_post(url, *args, **kwargs):
    path = urlparse(url).path
    path_parts = path.split('/')
    nova_microversion_header = kwargs['headers'].get('X-OpenStack-Nova-API-Version')
    if path == '/identity/v3/auth/tokens':
        data = json.loads(kwargs['data'])
        project_id = data.get('auth', {}).get('scope', {}).get('project', {}).get('id')
        if project_id:
            file_path = os.path.join(
                get_here(),
                'fixtures',
                nova_microversion_header if nova_microversion_header is not None else "default",
                *path_parts,
                f'{project_id}.json',
            )
            headers = {'X-Subject-Token': f'token_{project_id}'}
        else:
            file_path = os.path.join(
                get_here(),
                'fixtures',
                nova_microversion_header if nova_microversion_header is not None else "default",
                *path_parts,
                'unscoped.json',
            )
            headers = {'X-Subject-Token': 'token_test1234'}
    else:
        file_path = os.path.join(
            get_here(),
            'fixtures',
            nova_microversion_header if nova_microversion_header is not None else "default",
            *path_parts,
            'post.json',
        )
    return MockResponse(file_path=file_path, status_code=200, headers=headers)
