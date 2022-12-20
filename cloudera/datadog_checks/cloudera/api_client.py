from abc import ABC, abstractmethod


class ApiClient(ABC):
    def __init__(self, check, api_client):
        self._check = check
        self._log = check.log
        self._api_client = api_client

    @abstractmethod
    def collect_data(self):
        """Collect metrics and service checks via the Cloudera API Client"""
        pass
