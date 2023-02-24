# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient

EXCLUDED_TOPICS = ['__consumer_offsets', '__transaction_state']


class ConfluentKafkaClient:
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self._tls_context = tls_context

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            # self.conf is just the config options from librdkafka
            self._kafka_client = AdminClient(self.conf)

        return self._kafka_client

    def get_highwater_offsets(self):
        # {(topic, partition): offset}
        topics_with_consumer_offset = {}
        if not self.config._monitor_all_broker_highwatermarks:
            topics_with_consumer_offset = {(topic, partition) for (_, topic, partition) in self._consumer_offsets}

        for consumer_group in self._consumer_offsets.items():
            config = {
                "bootstrap.servers": self.config._kafka_connect_str,
                "group.id": consumer_group,
            }
            consumer = Consumer(config)
            topics = consumer.list_topics()

            for topic in topics.topics:
                topic_partitions = [
                    TopicPartition(topic, partition) for partition in list(topics.topics[topic].partitions.keys())
                ]

                for topic_partition in topic_partitions:
                    partition = topic_partition.partition
                    if topic not in EXCLUDED_TOPICS and (
                        self.config._monitor_all_broker_highwatermarks
                        or (topic, partition) in topics_with_consumer_offset
                    ):
                        _, high_offset = consumer.get_watermark_offsets(topic_partition)

                        self._highwater_offsets[(topic, partition)] = high_offset

        return self._highwater_offsets

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        # client.list_consumer_group_offsets(list_consumer_group_offsets_request)
        # ConsumerGroupTopicPartitions object
        return {}

    def get_partitions_for_topic(self):
        pass

    def request_metadata_update(self):
        # May not need this
        pass

    def collect_broker_version(self):
        pass

    def reset_offsets(self):
        self._consumer_offsets = {}
        self._highwater_offsets = {}
