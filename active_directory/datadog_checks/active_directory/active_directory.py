# (C) Datadog, Inc. 2013-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import PDHBaseCheck, is_affirmative

from .check import ActiveDirectoryCheckV2
from .metrics import DEFAULT_COUNTERS


class ActiveDirectoryCheck(PDHBaseCheck):
    def __new__(cls, name, init_config, instances):
        if not is_affirmative(instances[0].get('use_legacy_check_version', False)):
            return ActiveDirectoryCheckV2(name, init_config, instances)
        else:
            return super(ActiveDirectoryCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances=None):
        super(ActiveDirectoryCheck, self).__init__(
            name, init_config, instances=instances, counter_list=DEFAULT_COUNTERS
        )
