# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, is_affirmative

from .legacy import Win32EventLogWMI


class Win32EventLogCheck(AgentCheck):
    def __init__(self, name, init_config, instances):
        super(Win32EventLogCheck, self).__init__(name, init_config, instances)

    def check(self, _):
        raise NotImplementedError()

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if not is_affirmative(instance.get('use_wmi', True)):
            return super(Win32EventLogCheck, cls).__new__(cls)
        else:
            return Win32EventLogWMI(name, init_config, instances)
