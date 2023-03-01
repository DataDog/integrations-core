# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient

from datadog_checks.base import ConfigurationError
from confluent_kafka import ConsumerGroupTopicPartitions, KafkaException


class ConfluentKafkaClient(KafkaClient):
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
            # validate_consumer_groups(self.config._consumer_groups)
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


    def get_broker_offset(self):
        raise NotImplementedError
