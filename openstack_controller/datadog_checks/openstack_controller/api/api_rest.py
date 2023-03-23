# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from enum import Enum

from datadog_checks.base.utils.serialization import json
from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.baremetal_rest import BaremetalRest
from datadog_checks.openstack_controller.api.compute_rest import ComputeRest
from datadog_checks.openstack_controller.api.load_balancer_rest import LoadBalancerRest
from datadog_checks.openstack_controller.api.network_rest import NetworkRest


class ComponentType(str, Enum):
    COMPUTE = 'compute'
    NETWORK = 'network'
    BAREMETAL = 'baremetal'
    LOAD_BALANCER = 'load-balancer'


class ApiRest(Api):
    def __init__(self, config, logger, http):
        super(ApiRest, self).__init__()
        self.log = logger
        self.config = config
        self.http = http
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion
        self.project_auth_tokens = {}
        self.endpoints = {}
        self.components = {}

    def create_connection(self):
        self.log.debug("creating connection")
        response = self.http.get('{}/v3'.format(self.config.keystone_server_url))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self._get_x_auth_token()
        self._get_auth_projects()

    def get_projects(self):
        self.log.debug("getting projects")
        return [{'id': key, 'name': value['name']} for key, value in self.project_auth_tokens.items()]

    def get_compute_response_time(self, project_id):
        self.log.debug("getting compute response time")
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_response_time()
        return None

    def get_network_response_time(self, project):
        self.log.debug("getting network response time")
        component = self._get_component(project['id'], ComponentType.NETWORK)
        if component:
            return component.get_response_time()
        return None

    def get_baremetal_response_time(self, project):
        self.log.debug("getting baremetal response time")
        component = self._get_component(project['id'], ComponentType.BAREMETAL)
        if component:
            return component.get_response_time()
        return None

    def get_load_balancer_response_time(self, project):
        self.log.debug("getting load-balancer response time")
        component = self._get_component(project['id'], ComponentType.LOAD_BALANCER)
        if component:
            return component.get_response_time()
        return None

    def get_compute_limits(self, project_id):
        self.log.debug("getting compute limits")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_limits(project_id)
        return None

    def get_compute_quota_set(self, project_id):
        self.log.debug("getting compute quotas")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_quota_set(project_id)
        return None

    def get_compute_servers(self, project_id):
        self.log.debug("getting compute servers")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_servers(project_id)
        return None

    def get_compute_flavors(self, project_id):
        self.log.debug("getting compute flavors")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_flavors()
        return None

    def get_compute_hypervisors_detail(self, project_id, collect_hypervisor_load):
        self.log.debug("getting compute hypervisors detail")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_hypervisors_detail(collect_hypervisor_load)
        return None

    def get_compute_os_aggregates(self, project_id):
        self.log.debug("getting compute os-aggregates")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project_id]['auth_token']
        component = self._get_component(project_id, ComponentType.COMPUTE)
        if component:
            return component.get_os_aggregates()
        return None

    def get_network_quotas(self, project):
        self.log.debug("getting network quotas")
        self.http.options['headers']['X-Auth-Token'] = self.project_auth_tokens[project['id']]['auth_token']
        component = self._get_component(project['id'], ComponentType.NETWORK)
        if component:
            return component.get_quotas(project['id'])
        return None

    def _get_x_auth_token(self):
        self.log.debug("getting `X-Subject-Token`")
        payload = '{{"auth": {{"identity": {{"methods": ["password"], ' '"password": {{"user": {}}}}}}}}}'.format(
            json.dumps(self.config.user),
        )
        self.log.debug("payload: %s", payload)
        response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), data=payload)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self.http.options['headers']['X-Auth-Token'] = response.headers['X-Subject-Token']

    def _get_auth_projects(self):
        self.log.debug("getting auth/projects")
        response = self.http.get('{}/v3/auth/projects'.format(self.config.keystone_server_url))
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        json_resp = response.json()
        for project in json_resp['projects']:
            self._post_auth_project(project)
        self.log.debug("project_auth_tokens: %s", self.project_auth_tokens)

    def _post_auth_project(self, project):
        payload = (
            '{{"auth": {{"identity": {{"methods": ["password"], '
            '"password": {{"user": {}}}}}, '
            '"scope": {{"project": {{"id": "{}"}}}}}}}}'.format(
                json.dumps(self.config.user),
                project['id'],
            )
        )
        self.log.debug("payload: %s", payload)
        response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), data=payload)
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
        if endpoint_type == ComponentType.COMPUTE:
            return ComputeRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.NETWORK:
            return NetworkRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.BAREMETAL:
            return BaremetalRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.LOAD_BALANCER:
            return LoadBalancerRest(self.log, self.http, endpoint)
        return None
