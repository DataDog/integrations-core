# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime
import json
import os
from urllib.parse import urlparse

from packaging import version

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
TEST_OPENSTACK_CONFIG_PATH = os.path.join(FIXTURES_DIR, 'openstack_config.yaml')
TEST_OPENSTACK_UPDATED_CONFIG_PATH = os.path.join(FIXTURES_DIR, 'openstack_config_updated.yaml')
TEST_OPENSTACK_BAD_PASSWORD_CONFIG_PATH = os.path.join(FIXTURES_DIR, 'openstack_bad_password.yaml')
TEST_OPENSTACK_NO_AUTH_CONFIG_PATH = os.path.join(FIXTURES_DIR, 'openstack_bad_config.yaml')


def check_microversion(instance, metric):
    nova_microversion = version.parse(instance.get("nova_microversion", "2.1"))
    min_version = version.parse(metric.get("min_version", "2.1"))
    max_version = version.parse(metric.get("max_version", "2.93"))
    return min_version <= nova_microversion <= max_version


def is_mandatory(metric):
    return not metric.get("optional", False)


def get_microversion_path(headers):
    nova_microversion_header = headers.get('X-OpenStack-Nova-API-Version')
    ironic_microversion_header = headers.get('X-OpenStack-Ironic-API-Version')

    nova_microversion = nova_microversion_header if nova_microversion_header is not None else "default"
    ironic_microversion = ironic_microversion_header if ironic_microversion_header is not None else "default"
    microversion_path = 'nova-{}-ironic-{}'.format(nova_microversion, ironic_microversion)
    return microversion_path


def get_url_path(url):
    parsed_url = urlparse(url)
    return parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path


# class MockHttp:
#     def __init__(self, host, **kwargs):
#         self._host = host
#         self._exceptions = kwargs.get('exceptions')
#         self._defaults = kwargs.get('defaults')
#         self._replace = kwargs.get('replace')

#     def get(self, url, *args, **kwargs):
#         parsed_url = urlparse(url)
#         path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
#         path_parts = path_and_args.split('/')
#         microversion_path = _get_microversion_path(kwargs['headers'])
#         subpath = os.path.join(
#             *path_parts,
#         )
#         if self._exceptions and subpath in self._exceptions:
#             raise self._exceptions[subpath]
#         elif self._defaults and subpath in self._defaults:
#             return self._defaults[subpath]
#         else:
#             file_path = os.path.join(
#                 get_here(),
#                 'fixtures',
#                 self._host,
#                 microversion_path,
#                 subpath,
#                 'GET.json',
#             )
#             response = MockResponse(file_path=file_path, status_code=200).json()
#             if self._replace and subpath in self._replace:
#                 response = self._replace[subpath](response)
#             return MockResponse(json_data=response, status_code=200)

#     def post(self, url, *args, **kwargs):
#         parsed_url = urlparse(url)
#         path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
#         path_parts = path_and_args.split('/')
#         microversion_path = _get_microversion_path(kwargs['headers'])
#         subpath = os.path.join(
#             *path_parts,
#         )
#         if self._exceptions and subpath in self._exceptions:
#             return self._exceptions[subpath]
#         elif self._defaults and subpath in self._defaults:
#             return self._defaults[subpath]
#         elif path_and_args == '/identity/v3/auth/tokens':
#             data = kwargs['json']
#             scope = data.get('auth', {}).get('scope', None)
#             if scope:
#                 if isinstance(scope, str) and scope == "unscoped":
#                     if self._defaults and f'{subpath}/unscoped' in self._defaults:
#                         return self._defaults[f'{subpath}/unscoped']
#                     file_path = os.path.join(
#                         get_here(),
#                         'fixtures',
#                         self._host,
#                         microversion_path,
#                         *path_parts,
#                         'unscoped.json',
#                     )
#                     headers = {'X-Subject-Token': 'token_test1234'}
#                 elif isinstance(scope, dict):
#                     project_id = scope.get('project', {}).get('id')
#                     if project_id:
#                         if self._defaults and f'{subpath}/project' in self._defaults:
#                             return self._defaults[f'{subpath}/project']
#                         file_path = os.path.join(
#                             get_here(),
#                             'fixtures',
#                             self._host,
#                             microversion_path,
#                             *path_parts,
#                             f'project_{project_id}.json',
#                         )
#                         headers = {'X-Subject-Token': f'token_{project_id}'}
#         else:
#             file_path = os.path.join(
#                 get_here(),
#                 'fixtures',
#                 self._host,
#                 microversion_path,
#                 subpath,
#                 'POST.json',
#             )
#         response = MockResponse(file_path=file_path, status_code=200).json()
#         if self._replace and subpath in self._replace:
#             response = self._replace[subpath](response)
#         return MockResponse(json_data=response, status_code=200, headers=headers)


def get_json_value_from_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


def remove_service_from_catalog(d, services):
    catalog = d.get('token', {}).get('catalog', {})
    new_catalog = []
    for service in catalog:
        if service['type'] not in services:
            new_catalog.append(service)
    return {**d, **{'token': {**d['token'], 'catalog': new_catalog}}}


# def responses_map(
#     host='agent-integrations-openstack-default',
#     nova_microversion='default',
#     ironic_microversion='default',
# ):
#     microversion_folder = f'nova-{nova_microversion}-ironic-{ironic_microversion}'
#     responses_map = {}
#     root_dir_path = os.path.join(get_here(), 'fixtures', host, microversion_folder)
#     subdirectories = [d for d in Path(root_dir_path).iterdir() if d.is_dir()]
#     for subdir in subdirectories:
#         if subdir.name not in ['GET', 'POST']:
#             continue
#         responses_map[subdir.name] = {}
#         for file in subdir.rglob('*'):
#             if file.is_file():
#                 relative_dir_path = str(file.parent.relative_to(subdir))
#                 print(relative_dir_path)
#                 if relative_dir_path not in responses_map[subdir.name]:
#                     responses_map[subdir.name][relative_dir_path] = {}
#                 responses_map[subdir.name][relative_dir_path][file.stem] = get_json_value_from_file(file)
#         # if directory.is_dir():
#         #     for file_path in Path(root_dir_path).rglob('*'):
#         #         if file_path.is_file():
#         #             if file_path.stem not in responses_map:
#         #                 responses_map[file_path.stem] = {}
#         #             relative_dir_path = str(file_path.parent.relative_to(root_dir_path))
#         #             responses_map[file_path.stem][relative_dir_path] = get_json_value_from_file(file_path)
#     print(responses_map)
#     return responses_map
