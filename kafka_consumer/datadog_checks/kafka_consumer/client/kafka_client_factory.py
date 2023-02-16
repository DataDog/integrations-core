# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient
from datadog_checks.kafka_consumer.client.kafka_python_client import KafkaPythonClient


def make_client(check, config) -> KafkaClient:
    return KafkaPythonClient(check, config)
