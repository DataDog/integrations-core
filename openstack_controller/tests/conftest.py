# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import mock
import pytest
import requests
import yaml

import tests.configs as configs
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .endpoints import IRONIC_ENDPOINTS, NOVA_ENDPOINTS
from .ssh_tunnel import socks_proxy
from .terraform import terraform_run

USE_OPENSTACK_GCP = os.environ.get('USE_OPENSTACK_GCP')
OPENSTACK_E2E_LEGACY = os.environ.get('OPENSTACK_E2E_LEGACY')


@pytest.fixture(scope='session')
def dd_environment():
    if USE_OPENSTACK_GCP:

        def replace_env_vars(match):
            # Extract variable name from the matched string
            var_name = match.group(1)
            # Return the environment variable value or the original string if not found
            return os.environ.get(var_name, match.group(0))

        # Read the YAML file
        with open(configs.TEST_OPENSTACK_CONFIG_E2E_PATH, 'r') as file:
            content = file.read()
            # Replace environment variable placeholders
            content = re.sub(r'\$\{([^}]+)\}', replace_env_vars, content)
        # Parse the YAML with substituted values
        data = yaml.safe_load(content)
        # Write the modified content back to a file:
        with open(configs.TEST_OPENSTACK_UPDATED_CONFIG_E2E_PATH, 'w') as file:
            yaml.dump(data, file)

        with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
            ip = outputs['ip']['value']
            internal_ip = outputs['internal_ip']['value']
            private_key = outputs['ssh_private_key']['value']
            instance = {
                'keystone_server_url': 'http://{}/identity'.format(internal_ip),
                'username': 'admin',
                'password': 'password',
                'ssl_verify': False,
                'nova_microversion': '2.93',
                'ironic_microversion': '1.80',
                '#openstack_cloud_name': 'test_cloud',
                '#openstack_config_file_path': '/home/openstack_controller/tests/config/openstack_config_updated.yaml',
                'endpoint_region_id': 'RegionOne',
                'use_legacy_check_version': False,
            }
            env = dict(os.environ)
            with socks_proxy(
                ip,
                re.sub('([.@])', '_', env['TF_VAR_user']).lower(),
                private_key,
            ) as socks:
                socks_ip, socks_port = socks
                agent_config = {'proxy': {'http': 'socks5://{}:{}'.format(socks_ip, socks_port)}}
                yield instance, agent_config
    elif OPENSTACK_E2E_LEGACY:
        compose_file = os.path.join(get_here(), 'legacy', 'docker', 'docker-compose.yaml')
        conditions = [
            CheckDockerLogs(identifier='openstack-keystone', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-nova', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-neutron', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-ironic', patterns=['server running']),
        ]
        with docker_run(compose_file, conditions=conditions):
            instance = {
                'name': 'test',
                'keystone_server_url': 'http://127.0.0.1:8080/identity/v3',
                'user': {'name': 'admin', 'password': 'labstack', 'domain': {'id': 'default'}},
                'ssl_verify': False,
            }
            yield instance
    else:
        compose_file = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
        conditions = [
            CheckDockerLogs(identifier='openstack-keystone', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-nova', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-cinder', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-neutron', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-ironic', patterns=['server running']),
            CheckDockerLogs(identifier='openstack-octavia', patterns=['server running']),
        ]
        with docker_run(compose_file, conditions=conditions):
            instance = {
                'keystone_server_url': 'http://127.0.0.1:8080/identity',
                'username': 'admin',
                'password': 'password',
                'ssl_verify': False,
                'use_legacy_check_version': False,
            }
            yield instance


@pytest.fixture
def openstack_controller_check():
    return lambda instance: OpenStackControllerCheck('openstack', {}, [instance])


@pytest.fixture
def check(instance):
    return OpenStackControllerCheck('openstack', {}, [instance])


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


@pytest.fixture(scope='function')
def microversion_headers():
    headers = [None, None]
    yield headers


@pytest.fixture
def mock_responses(microversion_headers):
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

    def method(method, url, file='response', headers=None, params=None):
        filename = file
        request_path = url
        request_path = request_path.replace('?', '/')
        if params:
            param_string = '/'.join('{}={}'.format(key, str(val)) for key, val in params.items())
            request_path = '{}/{}'.format(url, param_string)
        if any(re.search(pattern, request_path) for pattern in NOVA_ENDPOINTS):
            microversion = headers.get('X-OpenStack-Nova-API-Version') if headers else microversion_headers[0]
            filename = f'{file}-{microversion}' if microversion else file
        if any(re.search(pattern, request_path) for pattern in IRONIC_ENDPOINTS):
            microversion = headers.get('X-OpenStack-Ironic-API-Version') if headers else microversion_headers[1]
            filename = f'{file}-{microversion}' if microversion else file

        response = responses_map.get(method, {}).get(request_path, {}).get(filename)
        return response

    create_responses_tree()
    yield method


@pytest.fixture
def mock_http_call(mock_responses):
    def call(method, url, file='response', headers=None, params=None):
        response = mock_responses(method, url, file=file, headers=headers, params=params)
        if response:
            return response
        http_response = requests.models.Response()
        http_response.status_code = 404
        http_response.reason = "Not Found"
        http_response.url = url
        raise requests.exceptions.HTTPError(response=http_response)

    yield call


@pytest.fixture
def session_auth(request, mock_responses):
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
def openstack_session(session_auth, microversion_headers):
    def session(auth, session):
        microversion_headers[0] = session.headers.get('X-OpenStack-Nova-API-Version')
        microversion_headers[1] = session.headers.get('X-OpenStack-Ironic-API-Version')
        return mock.MagicMock(
            return_value=mock.MagicMock(project_id=auth.project_id),
            auth=session_auth,
        )

    with mock.patch('keystoneauth1.session.Session', side_effect=session) as mock_session:
        yield mock_session


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
def connection_block_storage(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def volumes(project_id, limit=None):
        if http_error and 'volumes' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['volumes'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=volume,
                )
            )
            for volume in mock_responses('GET', f'/volume/v3/{project_id}/volumes/detail')['volumes']
        ]

    def transfers(project_id, details):
        if http_error and 'transfers' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['transfers'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=transfer,
                )
            )
            for transfer in mock_responses('GET', f'/volume/v3/{project_id}/os-volume-transfer/detail')['transfers']
        ]

    def snapshots(project_id, limit=None):
        if http_error and 'snapshots' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['snapshots'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=snapshot,
                )
            )
            for snapshot in mock_responses('GET', f'/volume/v3/{project_id}/snapshots/detail')['snapshots']
        ]

    def pools(project_id, details):
        if http_error and 'pools' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['pools'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=pool,
                )
            )
            for pool in mock_responses('GET', f'/volume/v3/{project_id}/scheduler-stats/get_pools')['pools']
        ]

    def clusters(project_id, details):
        if http_error and 'clusters' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['clusters'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=cluster,
                )
            )
            for cluster in mock_responses('GET', f'/volume/v3/{project_id}/clusters/detail')['clusters']
        ]

    return mock.MagicMock(
        volumes=mock.MagicMock(side_effect=volumes),
        transfers=mock.MagicMock(side_effect=transfers),
        snapshots=mock.MagicMock(side_effect=snapshots),
        pools=mock.MagicMock(side_effect=pools),
        clusters=mock.MagicMock(side_effect=clusters),
    )


@pytest.fixture
def connection_compute(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def get_limits(tenant_id):
        if http_error and 'limits' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['limits'])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/compute/v2.1/limits?tenant_id={tenant_id}')['limits'],
            )
        )

    def services():
        if http_error and 'services' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['services'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=service,
                )
            )
            for service in mock_responses('GET', '/compute/v2.1/os-services')['services']
        ]

    def aggregates():
        if http_error and 'aggregates' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['aggregates'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=aggregate,
                )
            )
            for aggregate in mock_responses('GET', '/compute/v2.1/os-aggregates')['aggregates']
        ]

    def flavors(details):
        if http_error and 'flavors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['flavors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=service,
                )
            )
            for service in mock_responses('GET', '/compute/v2.1/flavors/detail')['flavors']
        ]

    def hypervisors(details):
        if http_error and 'hypervisors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['hypervisors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=hypervisor,
                )
            )
            for hypervisor in mock_responses('GET', '/compute/v2.1/os-hypervisors/detail')['hypervisors']
        ]

    def get_hypervisor_uptime(hypervisor_id):
        if http_error and 'hypervisor_uptime' in http_error and hypervisor_id in http_error['hypervisor_uptime']:
            raise requests.exceptions.HTTPError(response=http_error['hypervisor_uptime'][hypervisor_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/compute/v2.1/os-hypervisors/{hypervisor_id}/uptime')[
                    'hypervisor'
                ],
            )
        )

    def get_quota_set(project_id):
        if http_error and 'quota_sets' in http_error and project_id in http_error['quota_sets']:
            raise requests.exceptions.HTTPError(response=http_error['quota_sets'][project_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/compute/v2.1/os-quota-sets/{project_id}')['quota_set']
            )
        )

    def servers(project_id, details, limit=None):
        if http_error and 'servers' in http_error and project_id in http_error['servers']:
            raise requests.exceptions.HTTPError(response=http_error['servers'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=server,
                )
            )
            for server in mock_responses('GET', f'/compute/v2.1/servers/detail?project_id={project_id}')['servers']
        ]

    def get_flavor(flavor_id):
        if http_error and 'flavors' in http_error and flavor_id in http_error['flavors']:
            raise requests.exceptions.HTTPError(response=http_error['flavors'][flavor_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(return_value=mock_responses('GET', f'/compute/v2.1/flavors/{flavor_id}')['flavor'])
        )

    def get_server_diagnostics(server_id):
        if http_error and 'server_diagnostics' in http_error and server_id in http_error['server_diagnostics']:
            raise requests.exceptions.HTTPError(response=http_error['server_diagnostics'][server_id])
        return mock.MagicMock(
            to_dict=mock.MagicMock(
                return_value=mock_responses('GET', f'/compute/v2.1/servers/{server_id}/diagnostics'),
            )
        )

    return mock.MagicMock(
        get_limits=mock.MagicMock(side_effect=get_limits),
        services=mock.MagicMock(side_effect=services),
        aggregates=mock.MagicMock(side_effect=aggregates),
        flavors=mock.MagicMock(side_effect=flavors),
        hypervisors=mock.MagicMock(side_effect=hypervisors),
        get_hypervisor_uptime=mock.MagicMock(side_effect=get_hypervisor_uptime),
        get_quota_set=mock.MagicMock(side_effect=get_quota_set),
        servers=mock.MagicMock(side_effect=servers),
        get_flavor=mock.MagicMock(side_effect=get_flavor),
        get_server_diagnostics=mock.MagicMock(side_effect=get_server_diagnostics),
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

    def networks(project_id, limit=None):
        if http_error and 'networks' in http_error and project_id in http_error['networks']:
            raise requests.exceptions.HTTPError(response=http_error['networks'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=network,
                )
            )
            for network in mock_responses('GET', f'/networking/v2.0/networks?project_id={project_id}')['networks']
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
        networks=mock.MagicMock(side_effect=networks),
        get_quota=mock.MagicMock(side_effect=get_quota),
    )


@pytest.fixture
def connection_baremetal(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def nodes(details, limit=None):
        if http_error and 'nodes' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['nodes'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', '/baremetal/v1/nodes/detail')['nodes']
        ]

    def conductors(limit=None):
        if http_error and 'conductors' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['conductors'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', '/baremetal/v1/conductors')['conductors']
        ]

    return mock.MagicMock(nodes=mock.MagicMock(side_effect=nodes), conductors=mock.MagicMock(side_effect=conductors))


@pytest.fixture
def connection_image(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def images(limit=None):
        if http_error and 'images' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['images'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', '/image/v2/images')['images']
        ]

    def members(image_id):
        if http_error and 'members' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['members'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', f'/image/v2/images/{image_id}/members')['members']
        ]

    def tasks(image_id):
        if http_error and 'tasks' in http_error:
            raise requests.exceptions.HTTPError(response=http_error['tasks'])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=node,
                )
            )
            for node in mock_responses('GET', f'/image/v2/images/{image_id}/tasks')['tasks']
        ]

    return mock.MagicMock(
        images=mock.MagicMock(side_effect=images),
        members=mock.MagicMock(side_effect=members),
        tasks=mock.MagicMock(side_effect=tasks),
    )


@pytest.fixture
def connection_load_balancer(request, mock_responses):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.get('http_error')

    def load_balancers(project_id, limit=None):
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

    def listeners(project_id, limit=None):
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

    def pools(project_id, limit=None):
        if http_error and 'pools' in http_error and project_id in http_error['pools']:
            raise requests.exceptions.HTTPError(response=http_error['pools'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=pool,
                )
            )
            for pool in mock_responses('GET', f'/load-balancer/v2/lbaas/pools?project_id={project_id}')['pools']
        ]

    def members(pool_id, project_id):
        if http_error and 'pool_members' in http_error and pool_id in http_error['pool_members']:
            raise requests.exceptions.HTTPError(response=http_error['pool_members'][pool_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=member,
                )
            )
            for member in mock_responses(
                'GET', f'/load-balancer/v2/lbaas/pools/{pool_id}/members?project_id={project_id}'
            )['members']
        ]

    def health_monitors(project_id):
        if http_error and 'health_monitors' in http_error and project_id in http_error['health_monitors']:
            raise requests.exceptions.HTTPError(response=http_error['health_monitors'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=pool,
                )
            )
            for pool in mock_responses('GET', f'/load-balancer/v2/lbaas/healthmonitors?project_id={project_id}')[
                'healthmonitors'
            ]
        ]

    def quotas(project_id):
        if http_error and 'quotas' in http_error and project_id in http_error['quotas']:
            raise requests.exceptions.HTTPError(response=http_error['quotas'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=pool,
                )
            )
            for pool in mock_responses('GET', f'/load-balancer/v2/lbaas/quotas?project_id={project_id}')['quotas']
        ]

    def amphorae(project_id, limit=None):
        if http_error and 'amphorae' in http_error and project_id in http_error['amphorae']:
            raise requests.exceptions.HTTPError(response=http_error['amphorae'][project_id])
        return [
            mock.MagicMock(
                to_dict=mock.MagicMock(
                    return_value=amphora,
                )
            )
            for amphora in mock_responses('GET', f'/load-balancer/v2/octavia/amphorae?project_id={project_id}')[
                'amphorae'
            ]
        ]

    return mock.MagicMock(
        load_balancers=mock.MagicMock(side_effect=load_balancers),
        get_load_balancer_statistics=mock.MagicMock(side_effect=get_load_balancer_statistics),
        listeners=mock.MagicMock(side_effect=listeners),
        get_listener_statistics=mock.MagicMock(side_effect=get_listener_statistics),
        pools=mock.MagicMock(side_effect=pools),
        members=mock.MagicMock(side_effect=members),
        health_monitors=mock.MagicMock(side_effect=health_monitors),
        quotas=mock.MagicMock(side_effect=quotas),
        amphorae=mock.MagicMock(side_effect=amphorae),
    )


@pytest.fixture
def openstack_connection(
    openstack_session,
    connection_authorize,
    connection_identity,
    connection_compute,
    connection_network,
    connection_baremetal,
    connection_block_storage,
    connection_load_balancer,
    connection_image,
):
    def connection(cloud, session, region_name):
        return mock.MagicMock(
            session=session,
            authorize=connection_authorize,
            identity=connection_identity,
            compute=connection_compute,
            network=connection_network,
            baremetal=connection_baremetal,
            block_storage=connection_block_storage,
            load_balancer=connection_load_balancer,
            image=connection_image,
        )

    with mock.patch('openstack.connection.Connection', side_effect=connection) as mock_connection:
        yield mock_connection


def get_url_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path


@pytest.fixture
def mock_http_get(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})
    data = param.pop('mock_data', {})

    def get(url, *args, **kwargs):
        method = 'GET'
        url = get_url_path(url)
        if http_error and url in http_error:
            raise requests.exceptions.HTTPError(response=http_error[url])

        if data and url in data:
            return MockResponse(json_data=data[url], status_code=200)

        json_data = mock_http_call(method, url, headers=kwargs.get('headers'), params=kwargs.get('params'))
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
            scope = data.get('auth', {}).get('scope', 'unscoped')
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
