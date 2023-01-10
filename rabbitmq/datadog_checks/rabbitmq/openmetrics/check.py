from datadog_checks.base import OpenMetricsBaseCheckV2


class RabbitMQOpenMetrics(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "rabbitmq"
