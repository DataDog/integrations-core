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
        self.project_endpoints = {}
        self.domain_endpoints = {}
        self.domain_components = {}
        self.project_components = {}
        self._add_microversion_headers()

    def _add_microversion_headers(self):
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion

        if self.config.ironic_microversion:
            self.log.debug("adding X-OpenStack-Ironic-API-Version header to `%s`", self.config.ironic_microversion)
            self.http.options['headers']['X-OpenStack-Ironic-API-Version'] = self.config.ironic_microversion

    def get_identity_response_time(self):
        self.log.debug("getting identity response time")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_response_time()

    def get_identity_domains(self):
        self.log.debug("getting identity domains")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_domains()

    def get_identity_projects(self):
        self.log.debug("getting identity projects")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_projects()

    def get_identity_users(self):
        self.log.debug("getting identity users")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_users()

    def get_identity_groups(self):
        self.log.debug("getting identity groups")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_groups()

    def get_identity_group_users(self, group_id):
        self.log.debug("getting identity group users")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_group_users(group_id)

    def get_identity_services(self):
        self.log.debug("getting identity services")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        return component.get_services()

    def get_identity_limits(self):
        identity_limits = {}
        self.log.debug("getting identity services")
        component = IdentityRest(self.log, self.http, '{}/v3'.format(self.config.keystone_server_url))
        registered_limits = component.get_registered_limits()
        self.log.debug("registered_limits: %s", registered_limits)
        for limit in registered_limits:
            identity_limits[limit['id']] = {
                'resource_name': limit.get('resource_name'),
                'service_id': limit.get('service_id'),
                'region_id': limit.get('region_id'),
                'limit': limit.get('default_limit'),
            }
        limits = component.get_limits()
        self.log.debug("limits: %s", limits)
        for limit in limits:
            identity_limits[limit['id']] = {
                'resource_name': limit.get('resource_name'),
                'service_id': limit.get('service_id'),
                'region_id': limit.get('region_id'),
                'domain_id': limit.get('domain_id'),
                'project_id': limit.get('project_id'),
                'limit': limit.get('resource_limit'),
            }
        return identity_limits

    def get_auth_projects(self):
        self.log.debug("getting auth projects")
        self._get_auth_projects()
        return [{'id': project_id, 'name': project_name} for project_id, project_name in self.auth_projects.items()]

    def get_compute_response_time(self):
        self.log.debug("getting compute response time")
        component = self._get_component(ComponentType.COMPUTE)
        if component:
            return component.get_response_time()
        return None

    def get_network_response_time(self):
        self.log.debug("getting network response time")
        component = self._get_component(ComponentType.NETWORK)
        if component:
            return component.get_response_time()
        return None

    def get_block_storage_response_time(self, project_id):
        self.log.debug("getting block-storage response time")
        component = self._get_component(ComponentType.BLOCK_STORAGE, project_id=project_id)
        if component:
            return component.get_response_time(project_id)
        return None

    def get_baremetal_response_time(self):
        self.log.debug("getting baremetal response time")
        component = self._get_component(ComponentType.BAREMETAL)
        if component:
            return component.get_response_time()
        return None

    def get_load_balancer_response_time(self):
        self.log.debug("getting load-balancer response time")
        component = self._get_component(ComponentType.LOAD_BALANCER)
        if component:
            return component.get_response_time()
        return None

    def get_load_balancer_loadbalancers(self, project_id):
        self.log.debug("getting load-balancer loadbalancers")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_loadbalancers(project_id)
        return None

    def get_load_balancer_listeners(self, project_id):
        self.log.debug("getting load-balancer listeners")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_listeners(project_id)
        return None

    def get_load_balancer_pools(self, project_id):
        self.log.debug("getting load-balancer pools")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_pools(project_id)
        return None

    def get_load_balancer_members_by_pool(self, project_id, pool_id):
        self.log.debug("getting load-balancer members by pool")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_members_by_pool(pool_id, project_id)
        return None

    def get_load_balancer_healthmonitors(self, project_id):
        self.log.debug("getting load-balancer healthmonitors")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_healthmonitors(project_id)
        return None

    def get_load_balancer_loadbalancer_statistics(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer loadbalancer statistics")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_loadbalancer_statistics(loadbalancer_id)
        return None

    def get_load_balancer_listener_statistics(self, project_id, listener_id):
        self.log.debug("getting load-balancer listener statistics")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_listener_statistics(listener_id)
        return None

    def get_load_balancer_listeners_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer listeners by loadbalancer")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_listeners_by_loadbalancer(loadbalancer_id, project_id)
        return None

    def get_load_balancer_pools_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer pools by loadbalancer")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_pools_by_loadbalancer(loadbalancer_id, project_id)
        return None

    def get_load_balancer_healthmonitors_by_pool(self, project_id, pool_id):
        self.log.debug("getting load-balancer healthmonitors by pool")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_healthmonitors_by_pool(pool_id, project_id)
        return None

    def get_load_balancer_amphorae(self, project_id):
        self.log.debug("getting load-balancer amphorae")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_amphorae()
        return None

    def get_load_balancer_amphorae_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer amphorae by loadbalancer")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_amphorae_by_loadbalancer(loadbalancer_id)
        return None

    def get_load_balancer_amphora_statistics(self, project_id, amphora_id):
        self.log.debug("getting load-balancer amphora statistics")
        component = self._get_component(ComponentType.LOAD_BALANCER, project_id=project_id)
        if component:
            return component.get_amphora_statistics(amphora_id)
        return None

    def get_compute_limits(self, project_id):
        self.log.debug("getting compute limits")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_limits(project_id)
        return None

    def get_compute_quota_set(self, project_id):
        self.log.debug("getting compute quotas")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_quota_set(project_id)
        return None

    def get_compute_services(self, project_id):
        self.log.debug("getting compute services")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_services()
        return None

    def get_compute_servers(self, project_id):
        self.log.debug("getting compute servers")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_servers(project_id)
        return None

    def get_compute_flavors(self, project_id):
        self.log.debug("getting compute flavors")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_flavors()
        return None

    def get_compute_hypervisors(self, project_id):
        self.log.debug("getting compute hypervisors")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_hypervisors()
        return None

    def get_compute_os_aggregates(self, project_id):
        self.log.debug("getting compute os-aggregates")
        component = self._get_component(ComponentType.COMPUTE, project_id=project_id)
        if component:
            return component.get_os_aggregates()
        return None

    def get_network_quotas(self, project_id):
        self.log.debug("getting network quotas")
        component = self._get_component(ComponentType.NETWORK, project_id=project_id)
        if component:
            return component.get_quotas(project_id)
        return None

    def get_baremetal_nodes(self):
        self.log.debug("getting baremetal nodes")
        component = self._get_component(ComponentType.BAREMETAL)
        if component:
            return component.get_nodes()
        return None

    def get_baremetal_conductors(self):
        self.log.debug("getting baremetal conductors")
        component = self._get_component(ComponentType.BAREMETAL)
        if component and component.collect_conductor_metrics():
            return component.get_conductors()
        else:
            self.log.info(
                "Ironic conductors metrics are not available. "
                "Please specify an `ironic_microversion` greater than 1.49 to recieve these metrics"
            )
            return None

    def get_network_agents(self):
        self.log.debug("getting network agents")
        component = self._get_component(ComponentType.NETWORK)
        if component:
            return component.get_agents()
        return None

    def post_auth_domain(self, domain_id):
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

    def post_auth_project(self, project_id):
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

    def _get_component(self, endpoint_type, project_id=None):
        if project_id is not None:
            if project_id in self.project_components:
                if endpoint_type in self.project_components[project_id]:
                    self.log.debug("cached component of type %s", endpoint_type)
                    return self.project_components[project_id][endpoint_type]
            else:
                self.project_components[project_id] = {}
            endpoint = self._get_endpoint(endpoint_type, project_id=project_id)
            if endpoint:
                self.project_components[project_id][endpoint_type] = self._make_component(endpoint_type, endpoint)
                return self.project_components[project_id][endpoint_type]
            return None
        else:
            if self.config.domain_id in self.domain_components:
                if endpoint_type in self.domain_components[self.config.domain_id]:
                    self.log.debug("cached component of type %s", endpoint_type)
                    return self.domain_components[self.config.domain_id][endpoint_type]
            else:
                self.domain_components[self.config.domain_id] = {}
            endpoint = self._get_endpoint(endpoint_type)
            if endpoint:
                self.domain_components[self.config.domain_id][endpoint_type] = self._make_component(
                    endpoint_type, endpoint
                )
                return self.domain_components[self.config.domain_id][endpoint_type]
            return None

    def _get_endpoint(self, endpoint_type, project_id=None):
        if project_id is not None:
            if project_id in self.project_endpoints:
                if endpoint_type in self.project_endpoints[project_id]:
                    self.log.debug("cached endpoint of type %s", endpoint_type)
                    return self.project_endpoints[project_id][endpoint_type]
            else:
                self.project_endpoints[project_id] = {}
            for item in self.auth_project_tokens[project_id]['catalog']:
                if item['type'] == endpoint_type:
                    for endpoint in item['endpoints']:
                        if endpoint['interface'] == 'public':
                            self.project_endpoints[project_id][endpoint_type] = endpoint['url']
                            return self.project_endpoints[project_id][endpoint_type]
            return None
        else:
            if self.config.domain_id in self.domain_endpoints:
                if endpoint_type in self.domain_endpoints[self.config.domain_id]:
                    self.log.debug("cached endpoint of type %s", endpoint_type)
                    return self.domain_endpoints[self.config.domain_id][endpoint_type]
            else:
                self.project_endpoints[self.config.domain_id] = {}

            for item in self.auth_domain_id_tokens[self.config.domain_id]['catalog']:
                if item['type'] == endpoint_type:
                    for endpoint in item['endpoints']:
                        if endpoint['interface'] == 'public':
                            self.auth_domain_id_tokens[self.config.domain_id][endpoint_type] = endpoint['url']
                            return self.auth_domain_id_tokens[self.config.domain_id][endpoint_type]
            return None

    def _make_component(self, endpoint_type, endpoint):
        if endpoint_type == ComponentType.COMPUTE:
            return ComputeRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.NETWORK:
            return NetworkRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.BLOCK_STORAGE:
            return BlockStorageRest(self.log, self.http, endpoint)
        elif endpoint_type == ComponentType.BAREMETAL:
            return BaremetalRest(self.log, self.http, endpoint, self.config.ironic_microversion)
        elif endpoint_type == ComponentType.LOAD_BALANCER:
            return LoadBalancerRest(self.log, self.http, endpoint)
        return None
