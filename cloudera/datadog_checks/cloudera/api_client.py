from abc import abstractmethod


class ApiClient:
    def __init__(self, check, api_client):
        self._check = check
        self._log = check.log
        self._api_client = api_client

    @abstractmethod
    def collect_data(self):
        raise NotImplementedError
