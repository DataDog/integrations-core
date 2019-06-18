# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import AgentCheck, is_affirmative

from .legacy_0_10_2 import LegacyKafkaCheck_0_10_2


class KafkaCheck(AgentCheck):
    """
    Check the offsets and lag of Kafka consumers.

    This check also returns broker highwater offsets.
    """

    __NAMESPACE__ = 'kafka'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('mode_0_10_2', False)):
            return super(KafkaCheck, cls).__new__(cls)
        else:
            return LegacyKafkaCheck_0_10_2(name, init_config, instances)

    def check(self, instance):
        raise NotImplementedError()
