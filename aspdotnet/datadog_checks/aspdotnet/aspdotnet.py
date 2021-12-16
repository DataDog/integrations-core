# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import PY3

from datadog_checks.base import PDHBaseCheck

from .metrics import DEFAULT_COUNTERS

EVENT_TYPE = SOURCE_TYPE_NAME = 'aspdotnet'


class AspdotnetCheck(PDHBaseCheck):
    def __new__(cls, name, init_config, instances):
        if PY3:
            from .check import AspdotnetCheckV2

            return AspdotnetCheckV2(name, init_config, instances)
        else:
            return super(AspdotnetCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):
        super(AspdotnetCheck, self).__init__(name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS)
