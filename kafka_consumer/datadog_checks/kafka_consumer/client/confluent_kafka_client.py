# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient

from datadog_checks.base import ConfigurationError

from .common import validate_consumer_groups

EXCLUDED_TOPICS = ['__consumer_offsets', '__transaction_state']


class ConfluentKafkaClient:
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._highwater_offsets = {}
        self._consumer_offsets = {}
        self._tls_context = tls_context

        if isinstance(self.config._kafka_connect_str, list):
            self.config._kafka_connect_str = ','.join(self.config._kafka_connect_str)

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            # self.conf is just the config options from librdkafka
            self._kafka_client = AdminClient(
                {
                    "bootstrap.servers": self.config._kafka_connect_str,
                    "socket.timeout.ms": self.config._request_timeout_ms,
                    "client.id": "dd-agent",
                }
            )

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
        offset_futures = {}

        if self.config._monitor_unlisted_consumer_groups:
            consumer_groups_future = self.kafka_client.list_consumer_groups()
            try:
                list_consumer_groups_result = consumer_groups_future.result()
                for valid_consumer_group in list_consumer_groups_result.valid:
                    offset_futures.update(
                        self.kafka_client.list_consumer_group_offsets(
                            [ConsumerGroupTopicPartitions(valid_consumer_group.group_id)]
                        )
                    )
            except Exception as e:
                self.log.error("Failed to collect consumer offsets %s", e)
        elif self.config._consumer_groups:
            validate_consumer_groups(self.config._consumer_groups)
            for consumer_group in self.config._consumer_groups:
                offset_futures.update(
                    self.kafka_client.list_consumer_group_offsets([ConsumerGroupTopicPartitions(consumer_group)])
                )
        else:
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self.config._monitor_unlisted_consumer_groups
            )

        for group_id, future in offset_futures.items():
            try:
                response_offset_info = future.result()
                consumer_group = response_offset_info.group_id
                topic_partitions = response_offset_info.topic_partitions
                for topic_partition in topic_partitions:
                    topic = topic_partition.topic
                    partition = topic_partition.partition
                    offset = topic_partition.offset

                    if topic_partition.error:
                        self.log.debug(
                            "Encountered error: %s. Occurred with topic: %s; partition: [%s]",
                            topic_partition.error.str(),
                            topic_partition.topic,
                            str(topic_partition.partition),
                        )
                    if not self.config._monitor_unlisted_consumer_groups and self.config._consumer_groups.get(
                        consumer_group
                    ):
                        # if topics is None => collect all topics and partitions for the consumer group
                        # if partitions is None => collect all partitions from the consumer group's topic
                        if (
                            self.config._consumer_groups[consumer_group]
                            and topic not in self.config._consumer_groups[consumer_group]
                        ):
                            continue
                        if (
                            self.config._consumer_groups[consumer_group].get(topic)
                            and partition not in self.config._consumer_groups[consumer_group][topic]
                        ):
                            continue
                    self._consumer_offsets[(consumer_group, topic, partition)] = offset
            except KafkaException as e:
                self.log.debug("Failed to read consumer offsets for %s: %s", group_id, e)

        return self._consumer_offsets

    def get_consumer_offsets_dict(self):
        return self._consumer_offsets

    def get_highwater_offsets_dict(self):
        return self._highwater_offsets

    def get_partitions_for_topic(self, topic):
        cluster_metadata = self.kafka_client.list_topics(topic)
        topics = cluster_metadata.topics
        partitions = list(topics[topic].partitions.keys())
        return partitions or []

    def request_metadata_update(self):
        # May not need this
        pass

    def collect_broker_version(self):
        pass

    def reset_offsets(self):
        self._consumer_offsets = {}
        self._highwater_offsets = {}
