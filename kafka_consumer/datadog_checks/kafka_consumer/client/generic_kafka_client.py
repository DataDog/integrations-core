# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.kafka_consumer.client.confluent_kafka_client import ConfluentKafkaClient
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient
from datadog_checks.kafka_consumer.client.kafka_python_client import KafkaPythonClient


class GenericKafkaClient(KafkaClient):
    def __init__(self, config, tls_context, log) -> None:
        super().__init__(config, tls_context, log)
        self.use_legacy_client = config.use_legacy_client
        self.confluent_kafka_client = (
            ConfluentKafkaClient(config, tls_context, log) if not self.use_legacy_client else None
        )
        self.python_kafka_client = KafkaPythonClient(config, tls_context, log)

    def get_consumer_offsets(self):
        if self.use_legacy_client:
            return self.python_kafka_client.get_consumer_offsets()
        return self.confluent_kafka_client.get_consumer_offsets()

    def get_highwater_offsets(self, consumer_offsets):
        if self.use_legacy_client:
            return self.python_kafka_client.get_highwater_offsets(consumer_offsets)
        return self.confluent_kafka_client.get_highwater_offsets(consumer_offsets)

    def get_highwater_offsets_dict(self):
        if self.use_legacy_client:
            return self.python_kafka_client.get_highwater_offsets_dict()
        return self.confluent_kafka_client.get_highwater_offsets_dict()

    def reset_offsets(self):
        if self.use_legacy_client:
            return self.python_kafka_client.reset_offsets()
        return self.confluent_kafka_client.reset_offsets()

    def get_partitions_for_topic(self, topic):
        if self.use_legacy_client:
            return self.python_kafka_client.get_partitions_for_topic(topic)
        return self.confluent_kafka_client.get_partitions_for_topic(topic)

    def request_metadata_update(self):
        # TODO when this method is implemented in ConfluentKafkaClient, replace this with:
        # if self.use_legacy_client:
        #     return self.python_kafka_client.request_metadata_update()
        # return self.confluent_kafka_client.request_metadata_update()
        return self.python_kafka_client.request_metadata_update()

    def get_consumer_offsets_dict(self):
        if self.use_legacy_client:
            return self.python_kafka_client.get_consumer_offsets_dict()
        return self.confluent_kafka_client.get_consumer_offsets_dict()

