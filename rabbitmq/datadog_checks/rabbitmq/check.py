# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative


class RabbitMQ(AgentCheck):
    __NAMESPACE__ = 'rabbitmq'

    def __new__(cls, name, init_config, instances):
        # TODO: can we use init config here?
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            from .openmetrics import RabbitMQOpenMetrics

            return RabbitMQOpenMetrics(name, init_config, instances)
        else:
            from .rabbitmq import RabbitMQManagement

            return RabbitMQManagement(name, init_config, instances)
