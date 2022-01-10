# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from six import PY3

from datadog_checks.base.checks.win import PDHBaseCheck

from .metrics import DEFAULT_COUNTERS


class ActiveDirectoryCheck(PDHBaseCheck):
    def __new__(cls, name, init_config, instances):
        if PY3:
            from .check import ActiveDirectoryCheckV2

            return ActiveDirectoryCheckV2(name, init_config, instances)
        else:
            return super(ActiveDirectoryCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):
        super(ActiveDirectoryCheck, self).__init__(
            name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS
        )
