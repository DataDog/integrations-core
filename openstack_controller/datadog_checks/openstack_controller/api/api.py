# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod


class Api(ABC):
    @abstractmethod
    def create_connection(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_projects(self):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_response_time(self, project_id):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_limits(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_quota_set(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_servers(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_flavors(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_compute_hypervisors_detail(self, project, collect_hypervisor_load):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_response_time(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_network_quotas(self, project):
        pass  # pragma: no cover

    @abstractmethod
    def get_baremetal_response_time(self, project):
        pass  # pragma: no cover
