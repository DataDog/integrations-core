# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

from .config_models import ConfigMixin


class PanFirewallCheck(AgentCheck, ConfigMixin):
    __NAMESPACE__ = 'pan_firewall'

    def check(self, _: Any) -> None:
        # Collection is added by later tasks.
        pass
