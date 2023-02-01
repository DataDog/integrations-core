# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod

from packaging.version import Version


class Client(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_version(self) -> Version:
        """Collect metrics and service checks via the Cloudera API Client"""
        pass

    @abstractmethod
    def read_clusters(self) -> list:
        pass

    @abstractmethod
    def query_time_series(self, category, query) -> list:
        pass

    @abstractmethod
    def list_hosts(self, cluster_name) -> list:
        pass

    @abstractmethod
    def read_events(self, query) -> list:
        pass
