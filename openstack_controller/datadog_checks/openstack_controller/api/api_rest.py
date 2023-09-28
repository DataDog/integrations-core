# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.openstack_controller.api.api import Api
from datadog_checks.openstack_controller.api.catalog import Catalog
from datadog_checks.openstack_controller.components.component import Component


class ApiRest(Api):
    def __init__(self, config, logger, http):
        super(ApiRest, self).__init__()
        self.log = logger
        self.config = config
        self.http = http
        self._catalog = None
        self._role_names = []
        self._components = {}
        self._endpoints = {}
        self._add_microversion_headers()
        self._current_project_id = None

    def auth_url(self):
        return self.config.keystone_server_url

    def set_current_project(self, project_id):
        self._current_project_id = project_id

    def has_admin_role(self):
        return 'admin' in self._role_names

    def component_in_catalog(self, component_types):
        return self._catalog.has_component(component_types)

    def get_response_time(self, id, endpoint_types):
        endpoint = self._catalog.get_endpoint_by_type(endpoint_types).replace(self._current_project_id, "")
        self.log.debug("%s endpoint: %s", id.value, endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.elapsed.total_seconds() * 1000

    def authorize(self):
        self._components = {}
        self._endpoints = {}
        scope = {"project": {"id": self._current_project_id}} if self._current_project_id else "unscoped"
        data = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.config.username,
                            "password": self.config.password,
                            "domain": {"id": self.config.domain_id},
                        }
                    },
                },
                "scope": scope,
            }
        }
        # Testing purposes (we need this header to redirect requests correctly with caddy)
        self.http.options['headers']['X-Auth-Type'] = (
            f"{self._current_project_id}" if self._current_project_id else "unscoped"
        )
        auth_tokens_endpoint = '{}/v3/auth/tokens'.format(self.config.keystone_server_url)
        self.log.debug("auth_tokens_endpoint: %s", auth_tokens_endpoint)
        self.log.debug("data: %s", data)
        response = self.http.post(auth_tokens_endpoint, json=data)
        response.raise_for_status()
        self.log.debug("response: %s", response.json())
        self.log.debug("interface: %s", self.config.endpoint_interface)
        self.log.debug("region_name: %s", self.config.endpoint_region_id)
        self._catalog = Catalog(
            response.json().get('token', {}).get('catalog', []),
            self.config.endpoint_interface,
            self.config.endpoint_region_id,
        )
        self._role_names = [role.get('name') for role in response.json().get('token', {}).get('roles', [])]
        self.http.options['headers']['X-Auth-Token'] = response.headers['X-Subject-Token']

    def _add_microversion_headers(self):
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion

        if self.config.ironic_microversion:
            self.log.debug("adding X-OpenStack-Ironic-API-Version header to `%s`", self.config.ironic_microversion)
            self.http.options['headers']['X-OpenStack-Ironic-API-Version'] = self.config.ironic_microversion

    def get_identity_regions(self):
        self.log.debug("getting identity regions")
        endpoint = '{}/v3/regions'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        self.log.debug("endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('regions', [])

    def get_identity_domains(self):
        self.log.debug("getting identity domains")
        response = self.http.get(
            '{}/v3/domains'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('domains', [])

    def get_identity_projects(self):
        self.log.debug("getting identity projects")
        response = self.http.get(
            '{}/v3/projects'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('projects', [])

    def get_identity_users(self):
        self.log.debug("getting identity users")
        response = self.http.get(
            '{}/v3/users'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('users', [])

    def get_identity_groups(self):
        self.log.debug("getting identity groups")
        response = self.http.get(
            '{}/v3/groups'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('groups', [])

    def get_identity_group_users(self, group_id):
        self.log.debug("getting identity group users")
        response = self.http.get(
            '{}/v3/groups/{}/users'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value), group_id)
        )
        response.raise_for_status()
        return response.json().get('users', [])

    def get_identity_services(self):
        self.log.debug("getting identity services")
        response = self.http.get(
            '{}/v3/services'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('services', [])

    def get_identity_registered_limits(self):
        self.log.debug("getting identity registered limits")
        response = self.http.get(
            '{}/v3/registered_limits'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('registered_limits', [])

    def get_identity_limits(self):
        self.log.debug("getting identity limits")
        response = self.http.get(
            '{}/v3/limits'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('limits', [])

    def get_auth_projects(self):
        self.log.debug("getting auth projects")
        endpoint = '{}/v3/auth/projects'.format(self.config.keystone_server_url)
        self.log.debug("auth projects endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('projects', [])

    def get_load_balancer_members_by_pool(self, project_id, pool_id):
        self.log.debug("getting load-balancer members by pool")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_members_by_pool(pool_id, project_id)
        return None

    def get_load_balancer_healthmonitors(self, project_id):
        self.log.debug("getting load-balancer healthmonitors")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_healthmonitors(project_id)
        return None

    def get_load_balancer_loadbalancer_statistics(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer loadbalancer statistics")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_loadbalancer_statistics(loadbalancer_id)
        return None

    def get_load_balancer_listener_statistics(self, project_id, listener_id):
        self.log.debug("getting load-balancer listener statistics")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_listener_statistics(listener_id)
        return None

    def get_load_balancer_listeners_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer listeners by loadbalancer")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_listeners_by_loadbalancer(loadbalancer_id, project_id)
        return None

    def get_load_balancer_pools_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer pools by loadbalancer")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_pools_by_loadbalancer(loadbalancer_id, project_id)
        return None

    def get_load_balancer_healthmonitors_by_pool(self, project_id, pool_id):
        self.log.debug("getting load-balancer healthmonitors by pool")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_healthmonitors_by_pool(pool_id, project_id)
        return None

    def get_load_balancer_amphorae(self, project_id):
        self.log.debug("getting load-balancer amphorae")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_amphorae()
        return None

    def get_load_balancer_amphorae_by_loadbalancer(self, project_id, loadbalancer_id):
        self.log.debug("getting load-balancer amphorae by loadbalancer")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_amphorae_by_loadbalancer(loadbalancer_id)
        return None

    def get_load_balancer_amphora_statistics(self, project_id, amphora_id):
        self.log.debug("getting load-balancer amphora statistics")
        component = self._get_component(Component.Types.LOAD_BALANCER.value)
        if component:
            return component.get_amphora_statistics(amphora_id)
        return None

    def get_compute_limits(self):
        self.log.debug("getting compute limits")
        response = self.http.get('{}/limits'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value)))
        response.raise_for_status()
        return response.json().get('limits', {})

    def get_compute_quota_sets(self, project_id):
        self.log.debug("getting compute quota sets for project %s", project_id)
        endpoint = '{}/os-quota-sets/{}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), project_id
        )
        self.log.debug("compute quota set endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('quota_set', {})

    def get_compute_servers(self, project_id):
        self.log.debug("getting compute servers for project %s", project_id)
        endpoint = '{}/servers/detail?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), project_id
        )
        self.log.debug("compute servers endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('servers', [])

    def get_compute_server_diagnostics(self, server_id):
        endpoint = '{}/servers/{}/diagnostics'.format(
            self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), server_id
        )
        self.log.debug("compute server diagnostics endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json()

    def get_compute_flavor(self, flavor_id):
        self.log.debug("getting compute flavor `%s`", flavor_id)
        response = self.http.get(
            '{}/flavors/{}'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), flavor_id)
        )
        response.raise_for_status()
        return response.json().get('flavor', {})

    def get_compute_services(self):
        self.log.debug("getting compute services")
        response = self.http.get(
            '{}/os-services'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('services', [])

    def get_compute_flavors(self):
        self.log.debug("getting compute flavors")
        response = self.http.get(
            '{}/flavors/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('flavors', [])

    def get_compute_hypervisors(self):
        self.log.debug("getting compute hypervisors")
        response = self.http.get(
            '{}/os-hypervisors/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('hypervisors', [])

    def get_compute_hypervisor_uptime(self, hypervisor_id):
        self.log.debug("getting compute hypervisor `%s` uptime", hypervisor_id)
        response = self.http.get(
            '{}/os-hypervisors/{}/uptime'.format(
                self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), hypervisor_id
            )
        )
        response.raise_for_status()
        return response.json().get('hypervisor', {})

    def get_network_agents(self):
        self.log.debug("getting network agents")
        endpoint = '{}/v2.0/agents'.format(self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value))
        self.log.debug("network agents endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('agents', [])

    def get_network_networks(self, project_id):
        self.log.debug("getting network networks")
        endpoint = '{}/v2.0/networks?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value), project_id
        )
        self.log.debug("network networks endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('networks', [])

    def get_network_quota(self, project_id):
        self.log.debug("getting network quotas")
        endpoint = '{}/v2.0/quotas/{}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value), project_id
        )
        self.log.debug("network agents endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('quota', [])

    def get_baremetal_nodes(self):
        def use_legacy_nodes_resource(microversion):
            self.log.debug("microversion=%s", microversion)
            if not microversion:
                return True
            legacy_microversion = False
            try:
                legacy_microversion = float(microversion) < 1.43
            except Exception as e:
                if microversion.lower() == 'latest':
                    legacy_microversion = False
                else:
                    raise e
            self.log.debug("legacy_microversion=%s", legacy_microversion)
            return legacy_microversion

        self.log.debug("getting baremetal nodes [microversion=%s]", self.config.ironic_microversion)
        endpoint = '{}/v1/{}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.BAREMETAL.value),
            ('nodes/detail' if use_legacy_nodes_resource(self.config.ironic_microversion) else 'nodes?detail=True'),
        )
        self.log.debug("baremetal nodes endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('nodes', [])

    def get_baremetal_conductors(self):
        self.log.debug("getting baremetal conductors")
        endpoint = '{}/v1/conductors'.format(self._catalog.get_endpoint_by_type(Component.Types.BAREMETAL.value))
        self.log.debug("baremetal conductors endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('conductors', [])

    def get_load_balancer_loadbalancers(self, project_id):
        self.log.debug("getting load balancer loadbalancers")
        endpoint = '{}/v2/lbaas/loadbalancers?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), project_id
        )
        self.log.debug("load balancer loadbalancers endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('loadbalancers', [])

    def get_load_balancer_loadbalancer_stats(self, loadbalancer_id):
        self.log.debug("getting load balancer loadbalancer stats")
        endpoint = '{}/v2/lbaas/loadbalancers/{}/stats'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), loadbalancer_id
        )
        self.log.debug("load balancer loadbalancer stats endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('stats', {})

    def get_load_balancer_listeners(self, project_id):
        self.log.debug("getting load balancer listeners for project `%s`", project_id)
        endpoint = '{}/v2/lbaas/listeners?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), project_id
        )
        self.log.debug("load balancer listeners endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('listeners', [])

    def get_load_balancer_listener_stats(self, listener_id):
        self.log.debug("getting load balancer listener stats")
        endpoint = '{}/v2/lbaas/listeners/{}/stats'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), listener_id
        )
        self.log.debug("load balancer listener stats endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('stats', {})

    def get_load_balancer_pools(self, project_id):
        self.log.debug("getting load balancer pools for project `%s`", project_id)
        endpoint = '{}/v2/lbaas/pools?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), project_id
        )
        self.log.debug("load balancer pools endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('pools', [])

    def get_load_balancer_pool_members(self, pool_id, project_id):
        self.log.debug("getting load balancer pools for project `%s`", project_id)
        endpoint = '{}/v2/lbaas/pools/{}/members?project_id={}'.format(
            self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), pool_id, project_id
        )
        self.log.debug("load balancer pool members endpoint: %s", endpoint)
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.json().get('members', [])

    def get_compute_os_aggregates(self):
        self.log.debug("getting compute os-aggregates")
        component = self._get_component(Component.Types.COMPUTE.value)
        if component:
            return component.get_os_aggregates()
        return None
