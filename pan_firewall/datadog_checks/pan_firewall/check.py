# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import hashlib
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

    def persistent_cache_id(self) -> str:
        """Keyed by namespace only, so a config edit keeps the threat watermarks, identities and Panorama list.

        Safe: the keys hold the serial, IP or Panorama host, and the base class still isolates the cache per check.
        """
        namespace = self.config.namespace or 'default'
        return hashlib.sha256(f'pan_firewall:{namespace}'.encode()).hexdigest()[:16]

    def check(self, _: Any) -> None:
        if self._source is None:
            self._source = (
                PanoramaFirewallSource(self, self.config)
                if self.config.panorama_host
                else StaticFirewallSource(self.config)
            )
        targets = self._source.list_firewalls()
        # A dropped poller's HTTP session is closed when the RequestsWrapper is garbage collected.
        for ip in set(self._pollers) - {target.ip for target in targets}:
            del self._pollers[ip]
        pollers = []
        for target in targets:
            poller = self._pollers.get(target.ip)
            # A replaced firewall at the same IP gets a new poller, so its identity and tags are not stale.
            if poller is None or poller.target.poller_key != target.poller_key:
                poller = self._pollers[target.ip] = FirewallPoller(self, target, self.config)
            else:
                poller.target = target
            pollers.append(poller)
        # A pool per run: no thread outlives the run, so nothing is left to stop when the check is unscheduled.
        with ThreadPoolExecutor(max_workers=self.config.max_concurrency, thread_name_prefix='pan_firewall') as pool:
            futures = {pool.submit(poller.run): poller for poller in pollers}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log.warning('pan_firewall %s: polling failed: %s', futures[future].ip, e, exc_info=True)
