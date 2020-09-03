# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck


class SnowflakeCheck(AgentCheck):
    def check(self, _):
        # type: (Any) -> None
        pass
