# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from datadog_checks.base import AgentCheck


class RethinkdbCheck(AgentCheck):
    def check(self, instance):
        # type: (Dict[str, Any]) -> None
        pass
