# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# 3p
import psutil

# project
from datadog_checks.base import AgentCheck


class SystemSwap(AgentCheck):
    def check(self, _):
        swap_mem = psutil.swap_memory()
        tags = self.instance.get('tags', [])
        self.rate('system.swap.swapped_in', swap_mem.sin, tags=tags)
        self.rate('system.swap.swapped_out', swap_mem.sout, tags=tags)
