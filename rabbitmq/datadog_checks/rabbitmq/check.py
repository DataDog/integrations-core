# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

from .openmetrics import RabbitMQOpenMetrics


class RabbitMQ(AgentCheck):
    __NAMESPACE__ = 'rabbitmq'

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'prometheus_plugin' in instance:

            return RabbitMQOpenMetrics(name, init_config, instances)
        else:
            from .rabbitmq import RabbitMQManagement

            return RabbitMQManagement(name, init_config, instances)
