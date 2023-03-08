# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
from six import string_types

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_consumer.client.kafka_client import KafkaClient
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS


class ConfluentKafkaClient(KafkaClient):
    @property
    def kafka_client(self):
        if self._kafka_client is None:
            config = {
                "bootstrap.servers": self.config._kafka_connect_str,
                "socket.timeout.ms": self.config._request_timeout * 1000,
                "client.id": "dd-agent",
                "security.protocol": self.config._security_protocol,
            }

            if self.config._sasl_mechanism == "OAUTHBEARER":
                oauth_config = {
                    "sasl.mechanism": self.config._sasl_mechanism,
                    "sasl.oauthbearer.method": "oidc",  # required to be `oidc` for OAUTHBEARER token login
                    "sasl.oauthbearer.client.id": self.config._sasl_oauth_token_provider.get("client_id"),
                    "sasl.oauthbearer.token.endpoint.url": self.config._sasl_oauth_token_provider.get("url"),
                    "sasl.oauthbearer.client.secret": self.config._sasl_oauth_token_provider.get("client_secret"),
                }
                config.update(oauth_config)

            if self.config._sasl_mechanism == "GSSAPI":
                kerb_config = {
                    "sasl.mechanism": self.config._sasl_mechanism,
                    "sasl.username": self.config._sasl_plain_username,
                    "sasl.password": self.config._sasl_plain_password,
                    "sasl.kerberos.service.name": self.config._sasl_kerberos_service_name,
                    # TODO: _sasl_kerberos_domain_name doesn't seem to be used?
                    # looks like in kafka-python, sasl_kerberos_domain name can also be the host address:
                    # https://github.com/dpkp/kafka-python/blob/7ac6c6e29099ccba4d50f5b842972dd7332d0e58/kafka/conn.py#L712
                    # TODO: If `sasl.kerberos.keytab` is not configured, does it automatically
                    # use `KRB5_CLIENT_KTNAME` env var?
                    # TODO: Test if Kerberos works on Windows before merging
                    # See: https://github.com/confluentinc/librdkafka/issues/1259
                    "sasl.kerberos.keytab": self.config._kerberos_keytab,
                }
                config.update(kerb_config)

            self._kafka_client = AdminClient(config)
        return self._kafka_client

    def get_consumer_offsets_dict(self):
        return self._consumer_offsets

    def get_highwater_offsets(self, consumer_offsets):
        # TODO: Remove broker_requests_batch_size as config after
        # kafka-python is removed if we don't need to batch requests in Confluent
        topics_with_consumer_offset = {}
        if not self.config._monitor_all_broker_highwatermarks:
            topics_with_consumer_offset = {(topic, partition) for (_, topic, partition) in consumer_offsets}

        for consumer_group in consumer_offsets.items():
            consumer_config = {
                "bootstrap.servers": self.config._kafka_connect_str,
                "group.id": consumer_group,
            }
            consumer = Consumer(consumer_config)
            # TODO: Update config._request_timeout_ms to config._request_timeout
            topics = consumer.list_topics(timeout=self.config._request_timeout_ms / 1000)

            for topic in topics.topics:
                topic_partitions = [
                    TopicPartition(topic, partition) for partition in list(topics.topics[topic].partitions.keys())
                ]

                for topic_partition in topic_partitions:
                    partition = topic_partition.partition
                    if topic not in KAFKA_INTERNAL_TOPICS and (
                        self.config._monitor_all_broker_highwatermarks
                        or (topic, partition) in topics_with_consumer_offset
                    ):
                        _, high_offset = consumer.get_watermark_offsets(topic_partition)

                        self._highwater_offsets[(topic, partition)] = high_offset

    def get_highwater_offsets_dict(self):
        return self._highwater_offsets

    def reset_offsets(self):
        self._consumer_offsets = {}
        self._highwater_offsets = {}

    def get_partitions_for_topic(self, topic):
        try:
            cluster_metadata = self.kafka_client.list_topics(topic, timeout=self.config._request_timeout_ms / 1000)
            topic_metadata = cluster_metadata.topics[topic]
            partitions = list(topic_metadata.partitions.keys())
            return partitions
        except KafkaException as e:
            self.log.error("Received exception when getting partitions for topic %s: %s", topic, e)
            return None

    def request_metadata_update(self):
        # https://github.com/confluentinc/confluent-kafka-python/issues/594
        self.kafka_client.list_topics(None, timeout=self.config._request_timeout_ms / 1000)

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
                    topics = self.kafka_client.list_topics(timeout=self.config._request_timeout_ms / 1000)
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

        topics = self.kafka_client.list_topics(timeout=self.config._request_timeout_ms / 1000)

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
