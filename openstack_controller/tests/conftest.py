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

    def method(method, url, file='response', headers=None, params=None):
        filename = file
        request_path = url
        request_path = request_path.replace('?', '/')
        if params:
            param_string = '/'.join('{}={}'.format(key, str(val)) for key, val in params.items())
            request_path = '{}/{}'.format(url, param_string)
        if any(re.search(pattern, request_path) for pattern in NOVA_ENDPOINTS):
            microversion = headers.get('X-OpenStack-Nova-API-Version') if headers else None
            filename = f'{file}-{microversion}' if microversion else file
        if any(re.search(pattern, request_path) for pattern in IRONIC_ENDPOINTS):
            microversion = headers.get('X-OpenStack-Ironic-API-Version') if headers else None
            filename = f'{file}-{microversion}' if microversion else file

        response = responses_map.get(method, {}).get(request_path, {}).get(filename)
        return response

    create_responses_tree()
    yield method


@pytest.fixture
def mock_http_call(mock_responses):
    def call(method, url, file='response', headers=None, params=None):
        response = mock_responses(method, url, file=file, headers=headers, params=params)
        if response is not None:
            return response
        http_response = requests.models.Response()
        http_response.status_code = 404
        http_response.reason = "Not Found"
        http_response.url = url
        raise requests.exceptions.HTTPError(response=http_response)

    yield call


def get_url_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path


@pytest.fixture
def mock_http_get(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    http_error = param.pop('http_error', {})
    data = param.pop('mock_data', {})
    elapsed_total_seconds = param.pop('elapsed_total_seconds', {})

    def get(url, *args, **kwargs):
        method = 'GET'
        url = get_url_path(url)
        if http_error and url in http_error:
            return http_error[url]
        if data and url in data:
            return MockResponse(json_data=data[url], status_code=200)
        headers = kwargs.get('headers')
        params = kwargs.get('params')
        mock_elapsed = mock.MagicMock(total_seconds=mock.MagicMock(return_value=elapsed_total_seconds.get(url, 0.0)))
        mock_json = mock.MagicMock(return_value=mock_http_call(method, url, headers=headers, params=params))
        mock_status_code = mock.MagicMock(return_value=200)
        return mock.MagicMock(elapsed=mock_elapsed, json=mock_json, status_code=mock_status_code)

    mock_get = mock.MagicMock(side_effect=get)
    monkeypatch.setattr('requests.Session.get', mock_get)
    return mock_get


@pytest.fixture
def mock_http_post(request, monkeypatch, mock_http_call):
    param = request.param if hasattr(request, 'param') and request.param is not None else {}
    replace = param.get('replace')
    http_error = param.get('http_error')

    def post(url, *args, **kwargs):
        method = 'POST'
        url = get_url_path(url)
        if http_error and url in http_error:
            return http_error[url]
        if url == '/identity/v3/auth/tokens':
            data = kwargs['json']
            file = data.get('auth', {}).get('scope', 'unscoped')
            if isinstance(file, dict):
                if 'system' in file:
                    file = 'system'
                else:
                    file = file.get('project', {}).get('id')
            json_data = mock_http_call(method, url, file, headers=kwargs.get('headers'))
            headers = {'X-Subject-Token': f'token_{file}'}
        else:
            json_data = mock_http_call(method, url)
        if replace and url in replace:
            json_data = replace[url](json_data)
        return MockResponse(json_data=json_data, status_code=200, headers=headers)

    mock_post = mock.MagicMock(side_effect=post)
    monkeypatch.setattr('requests.Session.post', mock_post)
    return mock_post
