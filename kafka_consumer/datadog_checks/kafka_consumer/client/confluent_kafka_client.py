# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka.admin import AdminClient

from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient


class ConfluentKafkaClient(KafkaClient):
    @property
    def kafka_client(self):
        if self._kafka_client is None:
            self._kafka_client = AdminClient(
                {
                    "bootstrap.servers": self.config._kafka_connect_str,
                    "socket.timeout.ms": self.config._request_timeout_ms,
                    "client.id": "dd-agent",
                }
            )
        return self._kafka_client

    def create_kafka_admin_client(self):
        raise NotImplementedError

    def get_consumer_offsets_dict(self):
        raise NotImplementedError

    def get_highwater_offsets(self):
        raise NotImplementedError

    def get_highwater_offsets_dict(self):
        raise NotImplementedError

    def reset_offsets(self):
        raise NotImplementedError

    def get_partitions_for_topic(self, topic):
        cluster_metadata = self.kafka_client.list_topics(topic)
        topics = cluster_metadata.topics
        partitions = list(topics[topic].partitions.keys())
        return partitions or []

    def request_metadata_update(self):
        raise NotImplementedError

    def get_consumer_offsets(self):
        raise NotImplementedError

    def get_broker_offset(self):
        raise NotImplementedError
