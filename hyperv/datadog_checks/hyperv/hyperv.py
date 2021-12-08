# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY3

from datadog_checks.base import PDHBaseCheck

from .metrics import DEFAULT_COUNTERS


class HypervCheck(PDHBaseCheck):
    def __new__(cls, name, init_config, instances):
        if PY3:
            from .check import HypervCheckV2

            return HypervCheckV2(name, init_config, instances)
        else:
            return super(HypervCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):
        super(HypervCheck, self).__init__(name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS)
