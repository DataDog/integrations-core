# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin


class DellPowerflexCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'dell_powerflex'

    def __init__(self, name, init_config, instances):
        super(DellPowerflexCheck, self).__init__(name, init_config, instances)
        self._base_tags: list[str] = []
        self.check_initializations.append(self._parse_config)

    def _parse_config(self) -> None:
        self._base_tags = [f'powerflex_gateway_url:{self.config.powerflex_gateway_url}']

    def check(self, _: Any) -> None:
        try:
            response = self.http.get(self.config.powerflex_gateway_url)
            response.raise_for_status()
            self.gauge('api.can_connect', 1, tags=self._base_tags)
        except (ConnectionError, HTTPError, InvalidURL, Timeout) as e:
            self.log.warning('Could not connect to PowerFlex Gateway: %s', e)
            self.gauge('api.can_connect', 0, tags=self._base_tags)
