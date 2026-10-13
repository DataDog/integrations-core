# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin
from .firewalls import StaticFirewallSource
from .poller import FirewallPoller


class PanFirewallCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'pan_firewall'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._source: StaticFirewallSource | None = None
        self._pollers: dict[str, FirewallPoller] = {}

    def check(self, _: Any) -> None:
        if self.config.panorama_host:
            self.log.warning('Panorama mode (`panorama_host`) is not supported yet: no firewall is polled')
            return
        if self._source is None:
            self._source = StaticFirewallSource(self.config)
        for target in self._source.list_firewalls():
            poller = self._pollers.get(target.ip)
            if poller is None:
                poller = self._pollers[target.ip] = FirewallPoller(self, target, self.config)
            poller.run()
