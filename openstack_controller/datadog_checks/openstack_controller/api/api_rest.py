# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.baremetal_rest import BaremetalRest
from datadog_checks.openstack_controller.api.compute_rest import ComputeRest
from datadog_checks.openstack_controller.api.network_rest import NetworkRest


class ApiRest(Api):
    def __init__(self, logger, config, http):
        super(ApiRest, self).__init__()
        self.log = logger
        self.config = config
        self.http = http
        self.project_auth_tokens = {}
        self.endpoints = {}
        self.components = {}

    def create_connection(self):
        self.log.debug("creating connection")
        self.log.debug("config: %s", self.config)
        keystone_server_url = self.config.get("keystone_server_url")
        response = self.http.get('{}/v3'.format(keystone_server_url))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self._get_x_auth_token(keystone_server_url)
        self._get_auth_projects(keystone_server_url)

    def get_projects(self):
        self.log.debug("getting projects")
        return [{'id': key, 'name': value['name']} for key, value in self.project_auth_tokens.items()]

    def get_compute_response_time(self, project):
        self.log.debug("getting compute response time")
        component = self._get_component(project['id'], 'compute')
        if component:
            return component.get_response_time()
        return None

    def get_network_response_time(self, project):
        self.log.debug("getting network response time")
        component = self._get_component(project['id'], 'network')
        if component:
            return component.get_response_time()
        return None

    def get_baremetal_response_time(self, project):
        self.log.debug("getting baremetal response time")
        component = self._get_component(project['id'], 'baremetal')
        if component:
            return component.get_response_time()
        return None

    def get_compute_limits(self, project):
        self.log.debug("getting compute limits")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], 'compute')
        if component:
            return component.get_limits(project['id'])
        return None

    def get_compute_quotas(self, project):
        self.log.debug("getting compute quotas")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], 'compute')
        if component:
            return component.get_quotas(project['id'])
        return None

    def get_compute_servers(self, project):
        self.log.debug("getting compute servers")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], 'compute')
        if component:
            return component.get_servers(project['id'])
        return None

    def get_compute_flavors(self, project):
        self.log.debug("getting compute flavors")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], 'compute')
        if component:
            return component.get_flavors()
        return None

    def get_networking_quotas(self, project):
        self.log.debug("getting networking quotas")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], 'network')
        if component:
            return component.get_quotas(project['id'])
        return None

    def _get_x_auth_token(self, keystone_server_url):
        self.log.debug("getting `X-Subject-Token`")
        payload = (
            '{{"auth": {{"identity": {{"methods": ["password"], '
            '"password": {{"user": {{"name": "{}", "domain": {{ "id": "{}" }}, "password": "{}"}}}}}}}}}}'.format(
                self.config.get("user_name"), self.config.get("user_domain"), self.config.get("user_password")
            )
        )
        self.log.debug("payload: %s", payload)
        response = self.http.post('{}/v3/auth/tokens'.format(keystone_server_url), data=payload)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self.http.options['headers']['X-Auth-Token'] = response.headers['X-Subject-Token']

    def _get_auth_projects(self, keystone_server_url):
        self.log.debug("getting auth/projects")
        response = self.http.get('{}/v3/auth/projects'.format(keystone_server_url))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        json_resp = response.json()
        for project in json_resp['projects']:
            self._get_auth_project(keystone_server_url, project)
        self.log.debug("project_auth_tokens: %s", self.project_auth_tokens)

    def _get_auth_project(self, keystone_server_url, project):
        payload = (
            '{{"auth": {{"identity": {{"methods": ["password"], '
            '"password": {{"user": {{"name": "{}", "domain": {{ "id": "{}" }}, "password": "{}"}}}}}}, '
            '"scope": {{"project": {{"id": "{}"}}}}}}}}'.format(
                self.config.get("user_name"),
                self.config.get("user_domain"),
                self.config.get("user_password"),
                project['id'],
            )
        )
        self.log.debug("payload: %s", payload)
        response = self.http.post('{}/v3/auth/tokens'.format(keystone_server_url), data=payload)
        self.log.debug("project name: %s", project['name'])
        self.log.debug("response: %s", response.json())
        self.project_auth_tokens[project['id']] = {
            'auth_token': response.headers['X-Subject-Token'],
            'name': project['name'],
            'catalog': response.json()['token']['catalog'],
        }

    def _get_component(self, project_id, endpoint_type):
        if project_id in self.components:
            if endpoint_type in self.components[project_id]:
                self.log.debug("cached component of type %s", endpoint_type)
                return self.components[project_id][endpoint_type]
        else:
            self.components[project_id] = {}
        endpoint = self._get_endpoint(project_id, endpoint_type)
        if endpoint:
            self.components[project_id][endpoint_type] = self._make_component(endpoint_type, endpoint)
            return self.components[project_id][endpoint_type]
        return None

    def _get_endpoint(self, project_id, endpoint_type):
        if project_id in self.endpoints:
            if endpoint_type in self.endpoints[project_id]:
                self.log.debug("cached endpoint of type %s", endpoint_type)
                return self.endpoints[project_id][endpoint_type]
        else:
            self.endpoints[project_id] = {}
        for item in self.project_auth_tokens[project_id]['catalog']:
            if item['type'] == endpoint_type:
                for endpoint in item['endpoints']:
                    if endpoint['interface'] == 'public':
                        self.endpoints[project_id][endpoint_type] = endpoint['url']
                        return self.endpoints[project_id][endpoint_type]
        return None

    def _make_component(self, endpoint_type, endpoint):
        if endpoint_type == 'compute':
            return ComputeRest(self.log, self.http, endpoint)
        elif endpoint_type == 'network':
            return NetworkRest(self.log, self.http, endpoint)
        elif endpoint_type == 'baremetal':
            return BaremetalRest(self.log, self.http, endpoint)
        return None
