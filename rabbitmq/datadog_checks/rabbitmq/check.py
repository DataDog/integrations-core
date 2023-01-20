# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2

from datadog_checks.base import AgentCheck, ConfigurationError


class RabbitMQ(AgentCheck):
    __NAMESPACE__ = 'rabbitmq'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'prometheus_plugin' in instance:
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the `rabbitmq_api_url` config."
                )
            from .openmetrics import RabbitMQOpenMetrics

            return RabbitMQOpenMetrics(name, init_config, instances)
        else:
            from .rabbitmq import RabbitMQManagement

            return RabbitMQManagement(name, init_config, instances)
