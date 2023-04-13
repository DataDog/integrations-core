# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from enum import Enum

from datadog_checks.base.utils.serialization import json
from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.baremetal_rest import BaremetalRest
from datadog_checks.openstack_controller.api.block_storage_rest import BlockStorageRest
from datadog_checks.openstack_controller.api.compute_rest import ComputeRest
from datadog_checks.openstack_controller.api.identity_rest import IdentityRest
from datadog_checks.openstack_controller.api.load_balancer_rest import LoadBalancerRest
from datadog_checks.openstack_controller.api.network_rest import NetworkRest


class ComponentType(str, Enum):
    IDENTITY = 'identity'
    COMPUTE = 'compute'
    NETWORK = 'network'
    BLOCK_STORAGE = 'block-storage'
    BAREMETAL = 'baremetal'
    LOAD_BALANCER = 'load-balancer'


class ApiRest(Api):
    def __init__(self, config, logger, http):
        super(ApiRest, self).__init__()
        self.log = logger
        self.config = config
        self.http = http
        self.auth_projects = {}
        self.auth_domain_id_tokens = {}
        self.auth_project_tokens = {}
        self.endpoints = {}
        self.components = {}
        self.add_microversion_headers()

    def add_microversion_headers(self):
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion

        if self.config.ironic_microversion:
            self.log.debug("adding X-OpenStack-Ironic-API-Version header to `%s`", self.config.ironic_microversion)
            self.http.options['headers']['X-OpenStack-Ironic-API-Version'] = self.config.ironic_microversion

    def get_identity_response_time(self):
        self.log.debug("getting identity response time")
        self._post_auth_unscoped()
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_response_time()

    def get_identity_domains(self):
        self.log.debug("getting identity domains")
        self._post_auth_domain(self.config.domain_id)
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        projects = component.get_domains()
        return projects

    def get_identity_projects(self):
        self.log.debug("getting identity projects")
        self._post_auth_domain(self.config.domain_id)
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        projects = component.get_projects()
        return projects

    def get_identity_users(self):
        self.log.debug("getting identity users")
        self._post_auth_domain(self.config.domain_id)
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        users = component.get_users()
        return users

    def get_auth_projects(self):
        self.log.debug("getting auth projects")
        self._get_auth_projects()
        return [{'id': project_id, 'name': project_name} for project_id, project_name in self.auth_projects.items()]

    def get_compute_response_time(self, project_id):
        self.log.debug("getting compute response time")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_response_time()
        return None

    def get_network_response_time(self, project_id):
        self.log.debug("getting network response time")
        component = self._get_component(project_id, ComponentType.NETWORK)
        if component:
            return component.get_response_time()
        return None

    def get_block_storage_response_time(self, project_id):
        self.log.debug("getting block-storage response time")
        component = self._get_component(project_id, ComponentType.BLOCK_STORAGE)
        if component:
            return component.get_response_time(project_id)
        return None

    def get_baremetal_response_time(self, project_id):
        self.log.debug("getting baremetal response time")
        component = self._get_component(project_id, ComponentType.BAREMETAL)
        if component:
            return component.get_response_time()
        return None

    def get_load_balancer_response_time(self, project_id):
        self.log.debug("getting load-balancer response time")
        component = self._get_component(project_id, ComponentType.LOAD_BALANCER)
        if component:
            return component.get_response_time()
        return None

    def get_compute_limits(self, project_id):
        self.log.debug("getting compute limits")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_limits(project_id)
        return None

    def get_compute_quota_set(self, project_id):
        self.log.debug("getting compute quotas")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_quota_set(project_id)
        return None

    def get_compute_servers(self, project_id):
        self.log.debug("getting compute servers")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_servers(project_id)
        return None

    def get_compute_flavors(self, project_id):
        self.log.debug("getting compute flavors")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_flavors()
        return None

    def get_compute_hypervisors(self, project_id):
        self.log.debug("getting compute hypervisors")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_hypervisors()
        return None

    def get_compute_os_aggregates(self, project_id):
        self.log.debug("getting compute os-aggregates")
        self._post_auth_project(project_id)
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_os_aggregates()
        return None

    def get_network_quotas(self, project_id):
        self.log.debug("getting network quotas")
        component = self._get_component(project_id, ComponentType.NETWORK)
        if component:
            return component.get_quotas(project_id)
        return None

    def _post_auth_unscoped(self):
        self.log.debug("getting `X-Subject-Token`")
        data = '{{"auth": {{"identity": {{"methods": ["password"], ' '"password": {{"user": {}}}}}}}}}'.format(
            json.dumps(self.config.user),
        )
        url = '{}/v3/auth/tokens'.format(self.config.keystone_server_url)
        self.log.debug("POST %s data: %s", url, data)
        response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), data=data)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self.http.options['headers']['X-Auth-Token'] = response.headers['X-Subject-Token']

    def _post_auth_domain(self, domain_id):
        if domain_id not in self.auth_domain_id_tokens:
            data = (
                '{{"auth": {{"identity": {{"methods": ["password"], '
                '"password": {{"user": {}}}}}, '
                '"scope": {{"domain": {{"id": "{}"}}}}}}}}'.format(
                    json.dumps(self.config.user),
                    domain_id,
                )
            )
            url = '{}/v3/auth/tokens'.format(self.config.keystone_server_url)
            self.log.debug("POST %s data: %s", url, data)
            response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), data=data)
            self.log.debug("response: %s", response.json())
            self.auth_domain_id_tokens[domain_id] = {
                'auth_token': response.headers['X-Subject-Token'],
                'catalog': response.json()['token']['catalog'],
            }
        self.http.options['headers']['X-Auth-Token'] = self.auth_domain_id_tokens[domain_id]['auth_token']

    def _get_auth_projects(self):
        self.log.debug("getting auth/projects")
        url = '{}/v3/auth/projects'.format(self.config.keystone_server_url)
        self.log.debug("GET %s", url)
        response = self.http.get('{}/v3/auth/projects'.format(self.config.keystone_server_url))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        json_resp = response.json()
        for project in json_resp['projects']:
            self.auth_projects[project['id']] = project['name']
        self.log.debug("auth_projects: %s", self.auth_projects)

    def _post_auth_project(self, project_id):
        if project_id not in self.auth_project_tokens:
            data = (
                '{{"auth": {{"identity": {{"methods": ["password"], '
                '"password": {{"user": {}}}}}, '
                '"scope": {{"project": {{"id": "{}"}}}}}}}}'.format(
                    json.dumps(self.config.user),
                    project_id,
                )
            )
            url = '{}/v3/auth/tokens'.format(self.config.keystone_server_url)
            self.log.debug("POST %s data: %s", url, data)
            response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), data=data)
            self.log.debug("response: %s", response.json())
            self.auth_project_tokens[project_id] = {
                'auth_token': response.headers['X-Subject-Token'],
                'catalog': response.json()['token']['catalog'],
            }
        self.http.options['headers']['X-Auth-Token'] = self.auth_project_tokens[project_id]['auth_token']

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
        for item in self.auth_project_tokens[project_id]['catalog']:
            if item['type'] == endpoint_type:
                for endpoint in item['endpoints']:
                    if endpoint['interface'] == 'public':
                        self.endpoints[project_id][endpoint_type] = endpoint['url']
                        return self.endpoints[project_id][endpoint_type]
        return None

    def _make_component(self, endpoint_type, endpoint):
        if endpoint_type == ComponentType.COMPUTE:
            return ComputeRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.NETWORK:
            return NetworkRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.BLOCK_STORAGE:
            return BlockStorageRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.BAREMETAL:
            return BaremetalRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.LOAD_BALANCER:
            return LoadBalancerRest(self.log, self.http, endpoint)
        return None
