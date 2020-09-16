# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck, is_affirmative

from .legacy.haproxy import HAProxyCheckLegacy


class HAProxyCheck(AgentCheck):
    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_legacy', True)):
            return HAProxyCheckLegacy(name, init_config, instances)
        else:
            return super(HAProxyCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(HAProxyCheck, self).__init__(name, init_config, instances)

    def check(self, _):
        raise NotImplementedError()
