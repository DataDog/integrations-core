# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import PDHBaseCheck

from .metrics import DEFAULT_COUNTERS


class HypervCheck(PDHBaseCheck):
    def __init__(self, name, init_config, agentConfig, instances=None):
        super(HypervCheck, self).__init__(
            name, init_config, agentConfig, instances=instances, counter_list=DEFAULT_COUNTERS
        )
