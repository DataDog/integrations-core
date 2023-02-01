# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from abc import ABC, abstractmethod


class Api(ABC):
    def __init__(self, check, api_client):
        self._check = check
        self._log = check.log
        self._api_client = api_client

    @abstractmethod
    def collect_data(self):
        """Collect metrics and service checks via the Cloudera API Client"""
        pass
