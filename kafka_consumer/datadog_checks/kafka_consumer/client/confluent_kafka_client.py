# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import KafkaException
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
        self._consumer_offsets = {}
        self._highwater_offsets = {}

    def get_partitions_for_topic(self, topic):

        try:
            cluster_metadata = self.kafka_client.list_topics(topic)
            topic_metadata = cluster_metadata.topics[topic]
            partitions = list(topic_metadata.partitions.keys())
            return partitions
        except KafkaException as e:
            self.log.error("Received exception when getting partitions for topic %s: %s", topic, e)
            return None

    def request_metadata_update(self):
        raise NotImplementedError

    def get_consumer_offsets(self):
        raise NotImplementedError

    def get_broker_offset(self):
        raise NotImplementedError
