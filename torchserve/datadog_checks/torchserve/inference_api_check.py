# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urljoin

from datadog_checks.base import AgentCheck


class TorchserveInferenceAPICheck(AgentCheck):
    __NAMESPACE__ = 'torchserve.inference_api'
    SERVICE_CHECK_NAME = 'health'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tags = []
        self.check_initializations.append(self.parse_config)

    def parse_config(self):
        self.tags = self.instance.get("tags", [])
        self.tags.append(f"inference_api_url:{self.instance['inference_api_url']}")

    def check(self, _):
        ping_url = urljoin(self.instance['inference_api_url'], 'ping')

        try:
            self.log.debug("Querying URL: [%s]", ping_url)
            response = self.http.get(ping_url)
            self.log.debug("Inference API `response`: [%s]", response)
            response.raise_for_status()
        except Exception as e:
            self.log.debug('Error querying the endpoint: %s', e)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.tags)
