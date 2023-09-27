# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re

# import tempfile
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlparse

import mock
import pytest
import requests

# from keystoneauth1 import access
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import (
    CHECK_NAME,
    CONFIG_NOVA_IRONIC_MICROVERSION_LATEST,
    CONFIG_NOVA_MICROVERSION_LATEST,
    CONFIG_REST,
    CONFIG_SDK,
    # TEST_OPENSTACK_CONFIG_PATH,
    USE_OPENSTACK_GCP,
    # MockHttp,
    get_json_value_from_file,
    # get_microversion_path,
    get_url_path,
)
from .endpoints import IRONIC_ENDPOINTS, NOVA_ENDPOINTS
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
    if USE_OPENSTACK_GCP:
        with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
            ip = outputs['ip']['value']
            private_key = outputs['ssh_private_key']['value']
            instance = {
                'keystone_server_url': 'http://{}/identity'.format(ip),
                'username': 'admin',
                'password': 'password',
                'ssl_verify': False,
                'nova_microversion': '2.93',
                'ironic_microversion': '1.80',
                'openstack_cloud_name': 'test_cloud',
                'openstack_config_file_path': '/home/openstack_controller/tests/fixtures/openstack_config.yaml',
                'endpoint_region_id': 'RegionOne',
            }
            env = dict(os.environ)
            with socks_proxy(
                ip,
                re.sub('([.@])', '_', env['TF_VAR_user']).lower(),
                private_key,
            ) as socks:
                socks_ip, socks_port = socks
                agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
                # agent_config = {'proxy': {'http': 'http://{}:80'.format(ip)}}
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
def instance_rest():
    return deepcopy(CONFIG_REST)


@pytest.fixture
def instance_nova_microversion_latest():
    return deepcopy(CONFIG_NOVA_MICROVERSION_LATEST)


@pytest.fixture
def instance_ironic_nova_microversion_latest():
    return deepcopy(CONFIG_NOVA_IRONIC_MICROVERSION_LATEST)


@pytest.fixture
def instance_sdk():
    return deepcopy(CONFIG_SDK)


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


@pytest.fixture
def mock_responses():
    responses_map = {}

    def process_files(dir, response_parent):
        for file in dir.rglob('*'):
            if file.is_file() and file.stem != ".slash":
                relative_dir_path = (
                    "/" + str(file.parent.relative_to(dir)) + ("/" if (file.parent / ".slash").is_file() else "")
                )
                if relative_dir_path not in response_parent:
                    response_parent[relative_dir_path] = {}
                json_data = get_json_value_from_file(file)
                response_parent[relative_dir_path][file.stem] = json_data

    def process_dir(dir, response_parent):
        response_parent[dir.name] = {}
        process_files(dir, response_parent[dir.name])

    def create_responses_tree():
        root_dir_path = os.path.join(get_here(), 'fixtures')
        method_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name in ['GET', 'POST']]
        for method_subdir in method_subdirs:
            process_dir(method_subdir, responses_map)
        nova_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name.startswith('nova')]
        for nova_subdir in nova_subdirs:
            process_dir(nova_subdir, responses_map)
        ironic_subdirs = [d for d in Path(root_dir_path).iterdir() if d.is_dir() and d.name.startswith('ironic')]
        for ironic_subdir in ironic_subdirs:
            process_dir(ironic_subdir, responses_map)

    def method(method, url, file='response', headers=None, microversion=None):
        filename = file
        if any(re.search(pattern, url) for pattern in NOVA_ENDPOINTS):
            microversion = (
                microversion if microversion else headers.get('X-OpenStack-Nova-API-Version') if headers else None
            )
            filename = f'{file}-{microversion}' if microversion else file
        if any(re.search(pattern, url) for pattern in IRONIC_ENDPOINTS):
            microversion = (
                microversion if microversion else headers.get('X-OpenStack-Ironic-API-Version') if headers else None
            )
            filename = f'{file}-{microversion}' if microversion else file
        response = responses_map.get(method, {}).get(url, {}).get(filename)
        return response

    create_responses_tree()
    yield method


@pytest.fixture
def mock_http_call(mock_responses):
    def call(method, url, file='response', headers=None):
        response = mock_responses(method, url, file=file, headers=headers)
        if response:
            return response
        http_response = requests.models.Response()
        http_response.status_code = 404
        http_response.reason = "Not Found"
        http_response.url = url
        raise requests.exceptions.HTTPError(response=http_response)

    yield call


@pytest.fixture
def openstack_session():
    def create_session(auth, session):
        session = mock.MagicMock()
        session.project_id = auth.project_id
        return session

    with mock.patch('keystoneauth1.session.Session', side_effect=create_session) as mock_session:
        yield mock_session


@pytest.fixture
def connection_session_auth(request, openstack_session, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    catalog = param.get('catalog')

    def get_access(session):
        project_id = session.return_value.project_id if session.return_value.project_id else 'unscoped'
        token = mock_responses('POST', '/identity/v3/auth/tokens', project_id)['token']
        return mock.MagicMock(
            service_catalog=mock.MagicMock(catalog=catalog if catalog is not None else token.get('catalog', [])),
            project_id=token.get('project', {}).get('id'),
            role_names=[role.get('name') for role in token.get('roles', [])],
        )

    return mock.MagicMock(get_access=mock.MagicMock(side_effect=get_access))


@pytest.fixture
def connection_authorize(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')
    exception = param.get('exception')

    def authorize():
        if exception is not None:
            raise exception
        if http_error is not None:
            raise requests.exceptions.HTTPError(response=http_error)
        return mock.MagicMock(return_value=["test_token"])

    return mock.MagicMock(side_effect=authorize)


@pytest.fixture
def connection_identity(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def regions():
        if http_error and 'regions' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['regions'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=region,
                )
            )
            for region in mock_responses('GET', '/identity/v3/regions')['regions']
        ]

    def domains():
        if http_error and 'domains' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['domains'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=domain,
                )
            )
            for domain in mock_responses('GET', '/identity/v3/domains')['domains']
        ]

    def projects():
        if http_error and 'projects' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['projects'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=project,
                )
            )
            for project in mock_responses('GET', '/identity/v3/projects')['projects']
        ]

    def users():
        if http_error and 'users' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['users'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=user,
                )
            )
            for user in mock_responses('GET', '/identity/v3/users')['users']
        ]

    def groups():
        if http_error and 'groups' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['groups'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=group,
                )
            )
            for group in mock_responses('GET', '/identity/v3/groups')['groups']
        ]

    def group_users(group_id):
        if http_error and 'group_users' in http_error and group_id in http_error['group_users']:
            raise requests.exceptions.HTTPError(response=http_error['group_users'][group_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=user,
                )
            )
            for user in mock_responses('GET', f'/identity/v3/groups/{group_id}/users')['users']
        ]

    def services():
        if http_error and 'services' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['services'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=service,
                )
            )
            for service in mock_responses('GET', '/identity/v3/services')['services']
        ]

    def registered_limits():
        if http_error and 'registered_limits' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['registered_limits'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=registered_limit,
                )
            )
            for registered_limit in mock_responses('GET', '/identity/v3/registered_limits')['registered_limits']
        ]

    def limits():
        if http_error and 'limits' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['limits'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=registered_limit,
                )
            )
            for registered_limit in mock_responses('GET', '/identity/v3/limits')['limits']
        ]

    return mock.MagicMock(
        regions=mock.MagicMock(side_effect=regions),
        domains=mock.MagicMock(side_effect=domains),
        projects=mock.MagicMock(side_effect=projects),
        users=mock.MagicMock(side_effect=users),
        groups=mock.MagicMock(side_effect=groups),
        group_users=mock.MagicMock(side_effect=group_users),
        services=mock.MagicMock(side_effect=services),
        registered_limits=mock.MagicMock(side_effect=registered_limits),
        limits=mock.MagicMock(side_effect=limits),
    )


@pytest.fixture
def connection_compute(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def get_limits(microversion):
        if http_error and 'limits' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['limits'])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', '/compute/v2.1/limits', microversion=microversion)['limits'],
            )
        )

    def services(microversion):
        if http_error and 'services' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['services'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=service,
                )
            )
            for service in mock_responses('GET', '/compute/v2.1/os-services', microversion=microversion)['services']
        ]

    def flavors(microversion, details):
        if http_error and 'flavors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['flavors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=service,
                )
            )
            for service in mock_responses('GET', '/compute/v2.1/flavors/detail', microversion=microversion)['flavors']
        ]

    def hypervisors(microversion, details):
        if http_error and 'hypervisors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['hypervisors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=hypervisor,
                )
            )
            for hypervisor in mock_responses('GET', '/compute/v2.1/os-hypervisors/detail', microversion=microversion)[
                'hypervisors'
            ]
        ]

    def get_hypervisor_uptime(hypervisor_id, microversion):
        if http_error and 'hypervisor_uptime' in http_error and hypervisor_id in http_error['hypervisor_uptime']:
            raise requests.exceptions.HTTPError(response=http_error['hypervisor_uptime'][hypervisor_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses(
                    'GET', f'/compute/v2.1/os-hypervisors/{hypervisor_id}/uptime', microversion=microversion
                )['hypervisor'],
            )
        )

    def get_quota_set(project_id, microversion):
        if http_error and 'quota_sets' in http_error and project_id in http_error['quota_sets']:
            raise requests.exceptions.HTTPError(response=http_error['quota_sets'][project_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses(
                    'GET', f'/compute/v2.1/os-quota-sets/{project_id}', microversion=microversion
                )['quota_set']
            )
        )

    def servers(project_id, details, microversion):
        if http_error and 'servers' in http_error and project_id in http_error['servers']:
            raise requests.exceptions.HTTPError(response=http_error['servers'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=server,
                )
            )
            for server in mock_responses(
                'GET', f'/compute/v2.1/servers/detail?project_id={project_id}', microversion=microversion
            )['servers']
        ]

    def server_diagnostics(server_id, microversion):
        if http_error and 'server_diagnostics' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['server_diagnostics'])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses(
                    'GET', f'/compute/v2.1/servers/{server_id}/diagnostics', microversion=microversion
                ),
            )
        )

    return mock.MagicMock(
        get_limits=mock.MagicMock(side_effect=get_limits),
        services=mock.MagicMock(side_effect=services),
        flavors=mock.MagicMock(side_effect=flavors),
        hypervisors=mock.MagicMock(side_effect=hypervisors),
        get_hypervisor_uptime=mock.MagicMock(side_effect=get_hypervisor_uptime),
        get_quota_set=mock.MagicMock(side_effect=get_quota_set),
        servers=mock.MagicMock(side_effect=servers),
        get_server_diagnostics=mock.MagicMock(side_effect=server_diagnostics),
    )


@pytest.fixture
def connection_network(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def agents():
        if http_error and 'agents' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['agents'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=agent,
                )
            )
            for agent in mock_responses('GET', '/networking/v2.0/agents')['agents']
        ]

    def get_quota(project_id, details):
        if http_error and 'quotas' in http_error and project_id in http_error['quotas']:
            raise requests.exceptions.HTTPError(response=http_error['quotas'][project_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/networking/v2.0/quotas/{project_id}')['quota'],
            )
        )

    return mock.MagicMock(
        agents=mock.MagicMock(side_effect=agents),
        get_quota=mock.MagicMock(side_effect=get_quota),
    )


@pytest.fixture
def connection_baremetal(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def nodes(details, microversion):
        if http_error and 'nodes' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['nodes'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', '/baremetal/v1/nodes/detail', microversion=microversion)['nodes']
        ]

    def conductors(microversion):
        if http_error and 'conductors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['conductors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', '/baremetal/v1/conductors', microversion=microversion)['conductors']
        ]

    return mock.MagicMock(nodes=mock.MagicMock(side_effect=nodes), conductors=mock.MagicMock(side_effect=conductors))


@pytest.fixture
def connection_load_balancer(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def load_balancers(project_id):
        if http_error and 'load_balancers' in http_error and project_id in http_error['load_balancers']:
            raise requests.exceptions.HTTPError(response=http_error['load_balancers'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=loadbalancer,
                )
            )
            for loadbalancer in mock_responses('GET', f'/load-balancer/v2/lbaas/loadbalancers?project_id={project_id}')[
                'loadbalancers'
            ]
        ]

    def get_load_balancer_statistics(loadbalancer_id):
        if (
            http_error
            and 'load_balancer_statistics' in http_error
            and loadbalancer_id in http_error['load_balancer_statistics']
        ):
            raise requests.exceptions.HTTPError(response=http_error['load_balancer_statistics'][loadbalancer_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses(
                    'GET', f'/load-balancer/v2/lbaas/loadbalancers/{loadbalancer_id}/stats'
                ).get('stats', {}),
            )
        )

    def listeners(project_id):
        if http_error and 'listeners' in http_error and project_id in http_error['listeners']:
            raise requests.exceptions.HTTPError(response=http_error['listeners'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=listener,
                )
            )
            for listener in mock_responses('GET', f'/load-balancer/v2/lbaas/listeners?project_id={project_id}')[
                'listeners'
            ]
        ]

    def get_listener_statistics(listener_id):
        if http_error and 'listener_statistics' in http_error and listener_id in http_error['listener_statistics']:
            raise requests.exceptions.HTTPError(response=http_error['listener_statistics'][listener_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/load-balancer/v2/lbaas/listeners/{listener_id}/stats').get(
                    'stats', {}
                ),
            )
        )

    return mock.MagicMock(
        load_balancers=mock.MagicMock(side_effect=load_balancers),
        get_load_balancer_statistics=mock.MagicMock(side_effect=get_load_balancer_statistics),
        listeners=mock.MagicMock(side_effect=listeners),
        get_listener_statistics=mock.MagicMock(side_effect=get_listener_statistics),
    )


@pytest.fixture
def openstack_connection(
    connection_session_auth,
    connection_authorize,
    connection_identity,
    connection_compute,
    connection_network,
    connection_baremetal,
    connection_load_balancer,
):
    def connection(cloud, session, region_name):
        return mock.MagicMock(
            session=mock.MagicMock(
                return_value=session,
                auth=connection_session_auth,
            ),
            authorize=connection_authorize,
            identity=connection_identity,
            compute=connection_compute,
            network=connection_network,
            baremetal=connection_baremetal,
            load_balancer=connection_load_balancer,
        )

    with mock.patch('openstack.connection.Connection', side_effect=connection) as mock_connection:
        yield mock_connection


@pytest.fixture
def mock_http_get(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})

    def get(url, *args, **kwargs):
        method = 'GET'
        url = get_url_path(url)
        if http_error and url in http_error:
            raise requests.exceptions.HTTPError(response=http_error[url])
        json_data = mock_http_call(method, url, headers=kwargs.get('headers'))
        return MockResponse(json_data=json_data, status_code=200)

    mock_get = mock.MagicMock(side_effect=get)
    monkeypatch.setattr('requests.get', mock_get)
    return mock_get


@pytest.fixture
def mock_http_post(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    replace = param.get('replace')
    exception = param.get('exception')
    http_error = param.get('http_error')

    def post(url, *args, **kwargs):
        method = 'POST'
        url = get_url_path(url)
        if exception and url in exception:
            raise exception[url]
        if http_error and url in http_error:
            raise requests.exceptions.HTTPError(response=http_error[url])
        if url == '/identity/v3/auth/tokens':
            data = kwargs['json']
            scope = data.get('auth', {}).get('scope', None)
            if scope:
                if isinstance(scope, dict):
                    scope = scope.get('project', {}).get('id')
                json_data = mock_http_call(method, url, scope, headers=kwargs.get('headers'))
                headers = {'X-Subject-Token': f'token_{scope}'}
        else:
            json_data = mock_http_call(method, url)
        if replace and url in replace:
            json_data = replace[url](json_data)
        return MockResponse(json_data=json_data, status_code=200, headers=headers)

    mock_post = mock.MagicMock(side_effect=post)
    monkeypatch.setattr('requests.post', mock_post)
    return mock_post


@pytest.fixture
def mock_api_rest(request, monkeypatch, mock_http_get, mock_http_post):
    pass
    # monkeypatch.setattr('requests.get', mock_http_get)
    # monkeypatch.setattr('requests.post', mock_http_post)
