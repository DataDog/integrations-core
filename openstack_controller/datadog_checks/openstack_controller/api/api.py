# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod


class Api(ABC):
    @abstractmethod
    def auth_url(self):
        pass  # pragma: no cover

    @abstractmethod
    def has_admin_role(self):
        pass  # pragma: no cover

    @abstractmethod
    def authorize_user(self):
        pass  # pragma: no cover

    @abstractmethod
    def authorize_system(self):
        pass  # pragma: no cover

    @abstractmethod
    def authorize_project(self, project_id):
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
    def get_compute_limits(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_quota_sets(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_services(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_servers(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_flavors(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_hypervisors(self, project, collect_hypervisor_load):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_quota(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_agents(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_conductors(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_nodes(self):
        pass  # pragma: no cover
