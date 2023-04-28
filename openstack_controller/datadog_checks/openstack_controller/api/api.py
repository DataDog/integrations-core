# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod


class Api(ABC):
    @abstractmethod
    def get_identity_response_time(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_domains(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_projects(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_users(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_groups(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_group_users(self, group_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_services(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_identity_limits(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_auth_projects(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_response_time(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_loadbalancers(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_listeners(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_pools(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_members_by_pool(self, project_id, pool_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_healthmonitors(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_loadbalancer_statistics(self, project_id, loadbalancer_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_listener_statistics(self, project_id, listener_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_listeners_by_loadbalancer(self, project_id, loadbalancer_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_pools_by_loadbalancer(self, project_id, loadbalancer_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_healthmonitors_by_pool(self, project_id, pool_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_amphorae(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_amphorae_by_loadbalancer(self, project_id, loadbalancer_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_load_balancer_amphora_statistics(self, project_id, loadbalancer_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_response_time(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_limits(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_quota_set(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_services(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_servers(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_flavors(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_hypervisors(self, project, collect_hypervisor_load):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_os_aggregates(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_response_time(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_quotas(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_agents(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_response_time(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_conductors(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_nodes(self):
        pass  # pragma: no cover
