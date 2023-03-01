# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
from six import string_types

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS


class ConfluentKafkaClient(KafkaClient):
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

    def create_kafka_admin_client(self):
        raise NotImplementedError

    def get_consumer_offsets_dict(self):
        return self._consumer_offsets

    def get_highwater_offsets(self):
        raise NotImplementedError

    def get_highwater_offsets_dict(self):
        raise NotImplementedError

    def reset_offsets(self):
        raise NotImplementedError

    def get_partitions_for_topic(self, topic):
        raise NotImplementedError

    def request_metadata_update(self):
        raise NotImplementedError

    def collect_broker_version(self):
        raise NotImplementedError

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        offset_futures = []

        if self.config._monitor_unlisted_consumer_groups:
            # Get all consumer groups
            consumer_groups = []
            consumer_groups_future = self.kafka_client.list_consumer_groups()
            self.log.debug('MONITOR UNLISTED CG FUTURES: %s', consumer_groups_future)
            try:
                list_consumer_groups_result = consumer_groups_future.result()
                self.log.debug('MONITOR UNLISTED FUTURES RESULT: %s', list_consumer_groups_result)
                for valid_consumer_group in list_consumer_groups_result.valid:
                    consumer_group = valid_consumer_group.group_id
                    topics = self.kafka_client.list_topics()
                    consumer_groups.append(consumer_group)
            except Exception as e:
                self.log.error("Failed to collect consumer offsets %s", e)

        elif self.config._consumer_groups:
            self._validate_consumer_groups()
            consumer_groups = self.config._consumer_groups

        else:
            raise ConfigurationError(
                "Cannot fetch consumer offsets because no consumer_groups are specified and "
                "monitor_unlisted_consumer_groups is %s." % self.config._monitor_unlisted_consumer_groups
            )

        topics = self.kafka_client.list_topics()

        for consumer_group in consumer_groups:
            self.log.debug('CONSUMER GROUP: %s', consumer_group)
            topic_partitions = self._get_topic_partitions(topics, consumer_group)
            for topic_partition in topic_partitions:
                offset_futures.append(
                    self.kafka_client.list_consumer_group_offsets(
                        [ConsumerGroupTopicPartitions(consumer_group, [topic_partition])]
                    )[consumer_group]
                )

        for future in offset_futures:
            try:
                response_offset_info = future.result()
                self.log.debug('FUTURE RESULT: %s', response_offset_info)
                consumer_group = response_offset_info.group_id
                topic_partitions = response_offset_info.topic_partitions
                self.log.debug('RESULT CONSUMER GROUP: %s', consumer_group)
                self.log.debug('RESULT TOPIC PARTITIONS: %s', topic_partitions)
                for topic_partition in topic_partitions:
                    topic = topic_partition.topic
                    partition = topic_partition.partition
                    offset = topic_partition.offset
                    self.log.debug('RESULTS TOPIC: %s', topic)
                    self.log.debug('RESULTS PARTITION: %s', partition)
                    self.log.debug('RESULTS OFFSET: %s', offset)

                    if topic_partition.error:
                        self.log.debug(
                            "Encountered error: %s. Occurred with topic: %s; partition: [%s]",
                            topic_partition.error.str(),
                            topic_partition.topic,
                            str(topic_partition.partition),
                        )
                    self._consumer_offsets[(consumer_group, topic, partition)] = offset
            except KafkaException as e:
                self.log.debug("Failed to read consumer offsets for %s: %s", consumer_group, e)

    def _validate_consumer_groups(self):
        """Validate any explicitly specified consumer groups.
        consumer_groups = {'consumer_group': {'topic': [0, 1]}}
        """
        assert isinstance(self.config._consumer_groups, dict)
        for consumer_group, topics in self.config._consumer_groups.items():
            assert isinstance(consumer_group, string_types)
            assert isinstance(topics, dict) or topics is None  # topics are optional
            if topics is not None:
                for topic, partitions in topics.items():
                    assert isinstance(topic, string_types)
                    assert isinstance(partitions, (list, tuple)) or partitions is None  # partitions are optional
                    if partitions is not None:
                        for partition in partitions:
                            assert isinstance(partition, int)

    def _get_topic_partitions(self, topics, consumer_group):
        topic_partitions = []
        for topic in topics.topics:
            if topic in KAFKA_INTERNAL_TOPICS:
                continue
            self.log.debug('CONFIGURED TOPICS: %s', topic)

            partitions = list(topics.topics[topic].partitions.keys())

            for partition in partitions:
                # Get all topic-partition combinations allowed based on config
                # if topics is None => collect all topics and partitions for the consumer group
                # if partitions is None => collect all partitions from the consumer group's topic
                if not self.config._monitor_unlisted_consumer_groups and self.config._consumer_groups.get(
                    consumer_group
                ):
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
                self.log.debug("TOPIC PARTITION: %s", TopicPartition(topic, partition))
                topic_partitions.append(TopicPartition(topic, partition))

        return topic_partitions

    def get_broker_offset(self):
        raise NotImplementedError
