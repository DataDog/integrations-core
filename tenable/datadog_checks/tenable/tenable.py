# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck


class TenableCheck(AgentCheck):
    def check(self, instance):
        pass
