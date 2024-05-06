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
        self._add_microversion_headers()

        self._interface = self.config.endpoint_interface if self.config.endpoint_interface else 'public'
        self._region_id = self.config.endpoint_region_id
        self._catalog = None
        self._current_project_id = None
        self._role_names = None

    def auth_url(self):
        return self.config.keystone_server_url

    def has_admin_role(self):
        return 'admin' in self._role_names

    def component_in_catalog(self, component_types):
        return self._catalog.has_component(component_types)

    def get_response_time(self, endpoint_types):
        endpoint = (
            self._catalog.get_endpoint_by_type(endpoint_types).replace(self._current_project_id, "")
            if self._current_project_id
            else self._catalog.get_endpoint_by_type(endpoint_types)
        )
        response = self.http.get(endpoint)
        response.raise_for_status()
        return response.elapsed.total_seconds() * 1000

    def get_auth_projects(self):
        response = self.http.get('{}/v3/auth/projects'.format(self.config.keystone_server_url))
        response.raise_for_status()
        return response.json().get('projects', [])

    def authorize_user(self):
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
            }
        }
        # Testing purposes (we need this header to redirect requests correctly with caddy)
        self.http.options['headers']['X-Auth-Type'] = "unscoped"
        self._authorize_data(data)
        self._current_project_id = None

    def authorize_system(self):
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
                "scope": {"system": {"all": True}},
            }
        }
        # Testing purposes (we need this header to redirect requests correctly with caddy)
        self.http.options['headers']['X-Auth-Type'] = "system"
        self._authorize_data(data)
        self._current_project_id = None

    def authorize_project(self, project_id):
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
                "scope": {"project": {"id": project_id}},
            }
        }
        # Testing purposes (we need this header to redirect requests correctly with caddy)
        self.http.options['headers']['X-Auth-Type'] = project_id
        self._authorize_data(data)
        self._current_project_id = project_id

    def _authorize_data(self, data):
        self.log.debug("creating auth token")
        response = self.http.post('{}/v3/auth/tokens'.format(self.config.keystone_server_url), json=data)
        response.raise_for_status()
        response_json = response.json()
        self.log.debug("response: %s", response_json)
        self._catalog = Catalog(
            response_json.get('token', {}).get('catalog', []),
            self._interface,
            self._region_id,
        )
        self._role_names = [role.get('name') for role in response_json.get('token', {}).get('roles', [])]
        self.http.options['headers']['X-Auth-Token'] = response.headers['X-Subject-Token']

    def _add_microversion_headers(self):
        if self.config.nova_microversion:
            self.log.debug("adding X-OpenStack-Nova-API-Version header to `%s`", self.config.nova_microversion)
            self.http.options['headers']['X-OpenStack-Nova-API-Version'] = self.config.nova_microversion

        if self.config.ironic_microversion:
            self.log.debug("adding X-OpenStack-Ironic-API-Version header to `%s`", self.config.ironic_microversion)
            self.http.options['headers']['X-OpenStack-Ironic-API-Version'] = self.config.ironic_microversion

        if self.config.cinder_microversion:
            self.log.debug("adding OpenStack-API-Version header to `%s`", self.config.cinder_microversion)
            self.http.options['headers']['OpenStack-API-Version'] = self.config.cinder_microversion

    def get_identity_regions(self):
        response = self.http.get(
            '{}/v3/regions'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('regions', [])

    def get_identity_domains(self):
        response = self.http.get(
            '{}/v3/domains'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('domains', [])

    def get_identity_projects(self):
        response = self.http.get(
            '{}/v3/projects'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('projects', [])

    def get_identity_users(self):
        response = self.http.get(
            '{}/v3/users'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('users', [])

    def get_identity_groups(self):
        response = self.http.get(
            '{}/v3/groups'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('groups', [])

    def get_identity_group_users(self, group_id):
        response = self.http.get(
            '{}/v3/groups/{}/users'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value), group_id)
        )
        response.raise_for_status()
        return response.json().get('users', [])

    def get_identity_services(self):
        response = self.http.get(
            '{}/v3/services'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('services', [])

    def get_identity_registered_limits(self):
        response = self.http.get(
            '{}/v3/registered_limits'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('registered_limits', [])

    def get_identity_limits(self):
        response = self.http.get(
            '{}/v3/limits'.format(self._catalog.get_endpoint_by_type(Component.Types.IDENTITY.value))
        )
        response.raise_for_status()
        return response.json().get('limits', [])

    def get_block_storage_volumes(self, project_id):
        params = {}
        return self.make_paginated_request(
            '{}/volumes/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.BLOCK_STORAGE.value)),
            'volumes',
            'id',
            next_signifier='volumes_links',
            params=params,
        )

    def get_block_storage_transfers(self, project_id):
        response = self.http.get(
            '{}/os-volume-transfer/detail'.format(
                self._catalog.get_endpoint_by_type(Component.Types.BLOCK_STORAGE.value)
            )
        )
        response.raise_for_status()
        return response.json().get('transfers', {})

    def get_block_storage_snapshots(self, project_id):
        params = {}
        return self.make_paginated_request(
            '{}/snapshots/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.BLOCK_STORAGE.value)),
            'snapshots',
            'id',
            next_signifier='snapshots_links',
            params=params,
        )

    def get_block_storage_pools(self, project_id):
        response = self.http.get(
            '{}/scheduler-stats/get_pools'.format(
                self._catalog.get_endpoint_by_type(Component.Types.BLOCK_STORAGE.value)
            )
        )
        response.raise_for_status()
        return response.json().get('pools', {})

    def get_block_storage_clusters(self, project_id):
        response = self.http.get(
            '{}/clusters/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.BLOCK_STORAGE.value))
        )
        response.raise_for_status()
        return response.json().get('clusters', {})

    def get_compute_limits(self, project_id):
        params = {'tenant_id': project_id}
        response = self.http.get(
            '{}/limits'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value)), params=params
        )
        response.raise_for_status()
        return response.json().get('limits', {})

    def get_compute_aggregates(self):
        response = self.http.get(
            '{}/os-aggregates'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('aggregates', [])

    def get_compute_quota_sets(self, project_id):
        response = self.http.get(
            '{}/os-quota-sets/{}'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), project_id)
        )
        response.raise_for_status()
        return response.json().get('quota_set', {})

    def get_compute_servers(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/servers/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value)),
            'servers',
            'id',
            next_signifier='servers_links',
            params=params,
        )

    def get_compute_server_diagnostics(self, server_id):
        response = self.http.get(
            '{}/servers/{}/diagnostics'.format(
                self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), server_id
            )
        )
        response.raise_for_status()
        return response.json()

    def get_compute_flavor(self, flavor_id):
        response = self.http.get(
            '{}/flavors/{}'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), flavor_id)
        )
        response.raise_for_status()
        return response.json().get('flavor', {})

    def get_compute_services(self):
        response = self.http.get(
            '{}/os-services'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('services', [])

    def get_compute_flavors(self):
        response = self.http.get(
            '{}/flavors/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('flavors', [])

    def get_compute_hypervisors(self):
        response = self.http.get(
            '{}/os-hypervisors/detail'.format(self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value))
        )
        response.raise_for_status()
        return response.json().get('hypervisors', [])

    def get_compute_hypervisor_uptime(self, hypervisor_id):
        response = self.http.get(
            '{}/os-hypervisors/{}/uptime'.format(
                self._catalog.get_endpoint_by_type(Component.Types.COMPUTE.value), hypervisor_id
            )
        )
        response.raise_for_status()
        return response.json().get('hypervisor', {})

    def get_network_agents(self):
        response = self.http.get(
            '{}/v2.0/agents'.format(self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value))
        )
        response.raise_for_status()
        return response.json().get('agents', [])

    def get_network_networks(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/v2.0/networks'.format(self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value)),
            'networks',
            'id',
            next_signifier='networks_links',
            params=params,
        )

    def get_network_quota(self, project_id):
        response = self.http.get(
            '{}/v2.0/quotas/{}'.format(self._catalog.get_endpoint_by_type(Component.Types.NETWORK.value), project_id)
        )
        response.raise_for_status()
        return response.json().get('quota', [])

    def make_paginated_request(self, url, resource_name, marker_name, next_signifier='next', params=None):
        def make_request(url, params):
            resp = self.http.get(url, params=params)
            resp.raise_for_status()
            response_json = resp.json()
            return response_json

        marker = None
        item_list = []
        params = {} if params is None else params

        if self.config.paginated_limit is None:
            response_json = make_request(url, params)
            objects = response_json.get(resource_name, [])
            return objects

        while True:
            self.log.debug(
                "making paginated request [limit=%s, marker=%s]",
                self.config.paginated_limit,
                marker,
            )

            params['limit'] = self.config.paginated_limit
            if marker is not None:
                params['marker'] = marker

            response_json = make_request(url, params)
            resources = response_json.get(resource_name, [])
            if len(resources) > 0:
                last_item = resources[-1]
                item_list.extend(resources)

                if next_signifier == '{}_links'.format(resource_name):
                    has_next_link = False
                    links = response_json.get(next_signifier, [])
                    for link in links:
                        link_type = link.get('rel')
                        if link_type == 'next':
                            has_next_link = True
                            break
                    if not has_next_link:
                        break
                else:
                    next_item = response_json.get(next_signifier)
                    if next_item is None:
                        break

                marker = last_item.get(marker_name)
            else:
                break

            if marker is None:
                break

        return item_list

    def get_baremetal_nodes(self):
        def use_legacy_nodes_resource(microversion):
            self.log.debug("Configured ironic microversion: %s", microversion)
            if not microversion:
                return True
            legacy_microversion = True
            try:
                legacy_microversion = float(microversion) < 1.43
            except Exception as e:
                if microversion.lower() == 'latest':
                    legacy_microversion = False
                else:
                    raise Exception(f"Invalid ironic microversion, cannot collect baremetal nodes: {str(e)}")
            self.log.debug("Collecting baremetal nodes with use_legacy_nodes_resource =%s", legacy_microversion)
            return legacy_microversion

        ironic_endpoint = self._catalog.get_endpoint_by_type(Component.Types.BAREMETAL.value)

        params = {}
        if use_legacy_nodes_resource(self.config.ironic_microversion):
            url = '{}/v1/nodes/detail'.format(ironic_endpoint)
        else:
            params = {'detail': True}
            url = '{}/v1/nodes'.format(ironic_endpoint)

        return self.make_paginated_request(url, 'nodes', 'uuid', params=params)

    def get_baremetal_conductors(self):

        ironic_endpoint = self._catalog.get_endpoint_by_type(Component.Types.BAREMETAL.value)

        url = '{}/v1/conductors'.format(ironic_endpoint)

        return self.make_paginated_request(url, 'conductors', 'hostname', params={})

    def get_load_balancer_loadbalancers(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/v2/lbaas/loadbalancers'.format(self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)),
            'loadbalancers',
            'id',
            next_signifier='loadbalancers_links',
            params=params,
        )

    def get_load_balancer_loadbalancer_stats(self, loadbalancer_id):
        response = self.http.get(
            '{}/v2/lbaas/loadbalancers/{}/stats'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), loadbalancer_id
            )
        )
        response.raise_for_status()
        return response.json().get('stats', {})

    def get_load_balancer_listeners(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/v2/lbaas/listeners'.format(self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)),
            'listeners',
            'id',
            next_signifier='listeners_links',
            params=params,
        )

    def get_load_balancer_listener_stats(self, listener_id):
        response = self.http.get(
            '{}/v2/lbaas/listeners/{}/stats'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), listener_id
            )
        )
        response.raise_for_status()
        return response.json().get('stats', {})

    def get_load_balancer_pools(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/v2/lbaas/pools'.format(self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)),
            'pools',
            'id',
            next_signifier='pools_links',
            params=params,
        )

    def get_load_balancer_pool_members(self, pool_id, project_id):
        params = {'project_id': project_id}
        response = self.http.get(
            '{}/v2/lbaas/pools/{}/members'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), pool_id
            ),
            params=params,
        )
        response.raise_for_status()
        return response.json().get('members', [])

    def get_load_balancer_healthmonitors(self, project_id):
        params = {'project_id': project_id}
        response = self.http.get(
            '{}/v2/lbaas/healthmonitors'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)
            ),
            params=params,
        )
        response.raise_for_status()
        return response.json().get('healthmonitors', [])

    def get_load_balancer_quotas(self, project_id):
        params = {'project_id': project_id}
        response = self.http.get(
            '{}/v2/lbaas/quotas'.format(self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)),
            params=params,
        )
        response.raise_for_status()
        return response.json().get('quotas', [])

    def get_load_balancer_amphorae(self, project_id):
        params = {'project_id': project_id}
        return self.make_paginated_request(
            '{}/v2/octavia/amphorae'.format(self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value)),
            'amphorae',
            'id',
            next_signifier='amphorae_links',
            params=params,
        )

    def get_load_balancer_amphora_stats(self, amphora_id):
        response = self.http.get(
            '{}/v2/octavia/amphorae/{}/stats'.format(
                self._catalog.get_endpoint_by_type(Component.Types.LOAD_BALANCER.value), amphora_id
            )
        )
        response.raise_for_status()
        return response.json().get('amphora_stats', [])

    def get_glance_images(self):
        return self.make_paginated_request(
            '{}/v2/images'.format(self._catalog.get_endpoint_by_type(Component.Types.IMAGE.value)),
            'images',
            'id',
            next_signifier='next',
        )

    def get_glance_members(self, image_id):
        response = self.http.get(
            '{}/v2/images/{}/members'.format(self._catalog.get_endpoint_by_type(Component.Types.IMAGE.value), image_id)
        )
        response.raise_for_status()
        return response.json().get('members', [])
