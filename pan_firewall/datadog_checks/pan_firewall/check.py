# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin
from .firewalls import FirewallSource, StaticFirewallSource
from .panorama import PanoramaFirewallSource
from .poller import FirewallPoller


class PanFirewallCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'pan_firewall'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._source: FirewallSource | None = None
        self._pollers: dict[str, FirewallPoller] = {}

    def check(self, _: Any) -> None:
        if self._source is None:
            self._source = (
                PanoramaFirewallSource(self, self.config)
                if self.config.panorama_host
                else StaticFirewallSource(self.config)
            )
        targets = self._source.list_firewalls()

        for ip in set(self._pollers) - {target.ip for target in targets}:
            del self._pollers[ip]
        pollers = []

        for target in targets:
            poller = self._pollers.get(target.ip)
            if poller is None or poller.target.poller_key != target.poller_key:
                poller = self._pollers[target.ip] = FirewallPoller(self, target, self.config)
            else:
                poller.target = target
            pollers.append(poller)

        with ThreadPoolExecutor(max_workers=self.config.max_concurrency, thread_name_prefix='pan_firewall') as pool:
            futures = {pool.submit(poller.run): poller for poller in pollers}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log.warning('pan_firewall %s: polling failed: %s', futures[future].ip, e, exc_info=True)
