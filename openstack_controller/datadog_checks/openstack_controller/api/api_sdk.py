# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os import environ

from keystoneauth1 import session
from keystoneauth1.identity import v3
from openstack import connection
from openstack.config import loader

from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.catalog import Catalog
from datadog_checks.openstack_controller.components.component import Component


class ApiSdk(Api):
    def __init__(self, config, logger, http):
        super(ApiSdk, self).__init__()
        self.log = logger
        self.config = config
        self.http = http
        self._add_microversion_headers()

        # Set the environment variable to the path of the config file for openstacksdk to find it
        environ["OS_CLIENT_CONFIG_FILE"] = self.config.openstack_config_file_path
        self.cloud_config = loader.OpenStackConfig(config_files=[self.config.openstack_config_file_path]).get_one_cloud(
            cloud=self.config.openstack_cloud_name
        )
        self._interface = (
            self.config.endpoint_interface
            if self.config.endpoint_interface
            else self.cloud_config.get_auth_args().get('interface', 'public')
        )
        self._region_id = (
            self.config.endpoint_region_id
            if self.config.endpoint_region_id
            else self.cloud_config.get_auth_args().get('region_name')
        )

        self.connection = None
        self._access = None
        self._catalog = None

    def _add_microversion_headers(self):
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion

        if self.config.ironic_microversion:
            self.log.debug("adding X-OpenStack-Ironic-API-Version header to `%s`", self.config.ironic_microversion)
            self.http.options['headers']['X-OpenStack-Ironic-API-Version'] = self.config.ironic_microversion

    def auth_url(self):
        return self.cloud_config.get_auth_args().get('auth_url')

    def has_admin_role(self):
        return 'admin' in self._access.role_names

    def component_in_catalog(self, component_types):
        return self._catalog.has_component(component_types)

    def authorize_user(self):
        v3_auth = v3.Password(
            auth_url=self.cloud_config.get_auth_args().get('auth_url'),
            username=self.cloud_config.get_auth_args().get('username'),
            password=self.cloud_config.get_auth_args().get('password'),
            user_domain_name=self.cloud_config.get_auth_args().get('user_domain_name', 'default'),
        )
        keystone_session = session.Session(auth=v3_auth, session=self.http.session)
        self.connection = connection.Connection(
            cloud=self.config.openstack_cloud_name, session=keystone_session, region_name=self._region_id
        )
        self._access = self.connection.session.auth.get_access(self.connection.session)
        self._catalog = Catalog(self._access.service_catalog.catalog, self._interface, self._region_id)
        self.connection.authorize()
        self.http.options['headers']['X-Auth-Token'] = self.connection.session.auth.get_token(self.connection.session)

    def authorize_system(self):
        v3_auth = v3.Password(
            auth_url=self.cloud_config.get_auth_args().get('auth_url'),
            username=self.cloud_config.get_auth_args().get('username'),
            password=self.cloud_config.get_auth_args().get('password'),
            user_domain_name=self.cloud_config.get_auth_args().get('user_domain_name', 'default'),
            system_scope="all",
        )
        keystone_session = session.Session(auth=v3_auth, session=self.http.session)
        self.connection = connection.Connection(
            cloud=self.config.openstack_cloud_name, session=keystone_session, region_name=self._region_id
        )
        self._access = self.connection.session.auth.get_access(self.connection.session)
        self._catalog = Catalog(self._access.service_catalog.catalog, self._interface, self._region_id)
        self.connection.authorize()
        self.http.options['headers']['X-Auth-Token'] = self.connection.session.auth.get_token(self.connection.session)

    def authorize_project(self, project_id):
        v3_auth = v3.Password(
            auth_url=self.cloud_config.get_auth_args().get('auth_url'),
            username=self.cloud_config.get_auth_args().get('username'),
            password=self.cloud_config.get_auth_args().get('password'),
            user_domain_name=self.cloud_config.get_auth_args().get('user_domain_name', 'default'),
            project_id=project_id,
            project_domain_name=self.cloud_config.get_auth_args().get('project_domain_name', 'default'),
        )
        keystone_session = session.Session(auth=v3_auth, session=self.http.session)
        self.connection = connection.Connection(
            cloud=self.config.openstack_cloud_name, session=keystone_session, region_name=self._region_id
        )
        self._access = self.connection.session.auth.get_access(self.connection.session)
        self._catalog = Catalog(self._access.service_catalog.catalog, self._interface, self._region_id)
        self.connection.authorize()
        self.http.options['headers']['X-Auth-Token'] = self.connection.session.auth.get_token(self.connection.session)

    def get_response_time(self, endpoint_types):
        endpoint = self._catalog.get_endpoint_by_type(endpoint_types)
        endpoint = endpoint.replace(self._access.project_id, "") if self._access.project_id else endpoint
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.elapsed.total_seconds() * 1000

    def get_identity_regions(self):
        return [region.to_dict(original_names=True) for region in self.connection.identity.regions()]

    def get_identity_domains(self):
        return [domain.to_dict(original_names=True) for domain in self.connection.identity.domains()]

    def get_identity_projects(self):
        return [project.to_dict(original_names=True) for project in self.connection.identity.projects()]

    def get_identity_users(self):
        return [user.to_dict(original_names=True) for user in self.connection.identity.users()]

    def get_identity_groups(self):
        return [group.to_dict(original_names=True) for group in self.connection.identity.groups()]

    def get_identity_group_users(self, group_id):
        return [user.to_dict(original_names=True) for user in self.connection.identity.group_users(group_id)]

    def get_identity_services(self):
        return [service.to_dict(original_names=True) for service in self.connection.identity.services()]

    def get_identity_registered_limits(self):
        return [
            registered_limit.to_dict(original_names=True)
            for registered_limit in self.connection.identity.registered_limits()
        ]

    def get_identity_limits(self):
        return [limit.to_dict(original_names=True) for limit in self.connection.identity.limits()]

    def get_compute_limits(self):
        return self.connection.compute.get_limits(microversion=self.config.nova_microversion).to_dict(
            original_names=True
        )

    def get_compute_services(self):
        return [
            service.to_dict(original_names=True)
            for service in self.connection.compute.services(microversion=self.config.nova_microversion)
        ]

    def get_compute_flavors(self):
        return [
            flavor.to_dict(original_names=True)
            for flavor in self.connection.compute.flavors(microversion=self.config.nova_microversion, details=True)
        ]

    def get_compute_hypervisors(self):
        return [
            hypervisor.to_dict(original_names=True)
            for hypervisor in self.connection.compute.hypervisors(
                microversion=self.config.nova_microversion, details=True
            )
        ]

    def get_compute_hypervisor_uptime(self, hypervisor_id):
        return self.connection.compute.get_hypervisor_uptime(
            hypervisor_id, microversion=self.config.nova_microversion
        ).to_dict(original_names=True)

    def get_compute_quota_sets(self, project_id):
        return self.connection.compute.get_quota_set(project_id, microversion=self.config.nova_microversion).to_dict(
            original_names=True
        )

    def get_compute_servers(self, project_id):
        return [
            server.to_dict(original_names=True)
            for server in self.connection.compute.servers(
                details=True, project_id=project_id, microversion=self.config.nova_microversion
            )
        ]

    def get_compute_server_diagnostics(self, server_id):
        return self.connection.compute.get_server_diagnostics(
            server_id, microversion=self.config.nova_microversion
        ).to_dict(original_names=True)

    def get_compute_flavor(self, flavor_id):
        return self.connection.compute.get_flavor(flavor_id).to_dict(original_names=True)

    def get_network_agents(self):
        return [agent.to_dict(original_names=True) for agent in self.connection.network.agents()]

    def get_network_networks(self, project_id):
        return [
            network.to_dict(original_names=True) for network in self.connection.network.networks(project_id=project_id)
        ]

    def get_network_quota(self, project_id):
        return self.connection.network.get_quota(project_id, details=True).to_dict(original_names=True)

    def get_baremetal_nodes(self):
        return [
            node.to_dict(original_names=True)
            for node in self.connection.baremetal.nodes(details=True, microversion=self.config.ironic_microversion)
        ]

    def get_baremetal_conductors(self):
        return [
            conductor.to_dict(original_names=True)
            for conductor in self.connection.baremetal.conductors(microversion=self.config.ironic_microversion)
        ]

    def get_auth_projects(self):
        response = self.http.get('{}/v3/auth/projects'.format(self.cloud_config.get_auth_args().get('auth_url')))
        response.raise_for_status()
        return response.json().get('projects', [])

    def get_load_balancer_loadbalancers(self, project_id):
        return [
            load_balancer.to_dict(original_names=True)
            for load_balancer in self.connection.load_balancer.load_balancers(project_id=project_id)
        ]

    def get_load_balancer_loadbalancer_stats(self, loadbalancer_id):
        return self.connection.load_balancer.get_load_balancer_statistics(loadbalancer_id).to_dict(original_names=True)

    def get_load_balancer_listeners(self, project_id):
        return [
            listener.to_dict(original_names=True)
            for listener in self.connection.load_balancer.listeners(project_id=project_id)
        ]

    def get_load_balancer_listener_stats(self, listener_id):
        return self.connection.load_balancer.get_listener_statistics(listener_id).to_dict(original_names=True)

    def get_load_balancer_pools(self, project_id):
        return [
            pool.to_dict(original_names=True) for pool in self.connection.load_balancer.pools(project_id=project_id)
        ]

    def get_load_balancer_pool_members(self, pool_id, project_id):
        return [
            member.to_dict(original_names=True)
            for member in self.connection.load_balancer.members(pool_id, project_id=project_id)
        ]

    def get_load_balancer_healthmonitors(self, project_id):
        return [
            healthmonitor.to_dict(original_names=True)
            for healthmonitor in self.connection.load_balancer.health_monitors(project_id=project_id)
        ]

    def get_load_balancer_quotas(self, project_id):
        return [
            quota.to_dict(original_names=True) for quota in self.connection.load_balancer.quotas(project_id=project_id)
        ]

    def get_load_balancer_amphorae(self, project_id):
        return [
            amphora.to_dict(original_names=True)
            for amphora in self.connection.load_balancer.amphorae(project_id=project_id)
        ]

    def get_load_balancer_amphora_stats(self, amphora_id):
        response = self.http.get(
            '{}/v2/octavia/amphorae/{}/stats'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), amphora_id
            )
        )
        response.raise_for_status()
        return response.json().get('amphora_stats', [])
