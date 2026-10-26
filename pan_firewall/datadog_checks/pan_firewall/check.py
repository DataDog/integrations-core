# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.persistent_cache import config_set_persistent_cache_id

from .config_models import ConfigMixin
from .firewalls import FirewallSource, StaticFirewallSource
from .panorama import PanoramaFirewallSource
from .poller import FirewallPoller


class PanFirewallCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'pan_firewall'
    # The documented default timeout (30 s) instead of the HTTP wrapper's (10 s).
    HTTP_CONFIG_REMAPPER = {'timeout': {'name': 'timeout', 'default': 30}}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._source: FirewallSource | None = None
        self._pollers: dict[str, FirewallPoller] = {}

    def persistent_cache_id(self) -> str:
        # The cache keys already name their device (serial, IP, Panorama host), so the namespace (and the Panorama
        # host) is enough to keep instances apart. Unlike the default config digest, editing credentials, tags or
        # tuning options keeps the threat watermarks, the Panorama firewall list and the device identities.
        return config_set_persistent_cache_id(self, instance_config_options=['namespace', 'panorama_host'])

    def check(self, _: Any) -> None:
        if self._source is None:
            self._source = (
                PanoramaFirewallSource(self, self.config, self.config.panorama_host)
                if self.config.panorama_host
                else StaticFirewallSource(self.config)
            )
        targets = self._source.list_firewalls()

        self._remove_stale_pollers({target.ip for target in targets})
        pollers = []

        for target in targets:
            poller = self._pollers.get(target.ip)
            if poller is None or poller.target.poller_key != target.poller_key:
                poller = self._pollers[target.ip] = FirewallPoller(self, target)
            else:
                poller.target = target
            pollers.append(poller)

        with ThreadPoolExecutor(max_workers=self.config.max_concurrency, thread_name_prefix='pan_firewall') as pool:
            futures = {pool.submit(poller.run): poller for poller in pollers}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log.warning('%s: polling failed: %s', futures[future].ip, e, exc_info=True)

    def _remove_stale_pollers(self, current_ips: set[str]) -> None:
        for ip in set(self._pollers) - current_ips:
            del self._pollers[ip]
