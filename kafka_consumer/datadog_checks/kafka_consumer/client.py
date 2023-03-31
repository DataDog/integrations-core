# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient
from six import string_types

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS


class KafkaClient:
    def __init__(self, config, tls_context, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._tls_context = tls_context

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            config = {
                "bootstrap.servers": self.config._kafka_connect_str,
                "socket.timeout.ms": self.config._request_timeout_ms,
                "client.id": "dd-agent",
            }
            config.update(self.__get_authentication_config())

            self._kafka_client = AdminClient(config)

        return self._kafka_client

    def __create_consumer(self, consumer_group):
        config = {
            "bootstrap.servers": self.config._kafka_connect_str,
            "group.id": consumer_group,
        }
        config.update(self.__get_authentication_config())

        return Consumer(config)

    def __get_authentication_config(self):
        config = {
            "security.protocol": self.config._security_protocol.lower(),
        }

        extras_parameters = {
            "ssl.ca.location": self.config._tls_ca_cert,
            "ssl.certificate.location": self.config._tls_cert,
            "ssl.key.location": self.config._tls_private_key,
            "ssl.key.password": self.config._tls_private_key_password,
            "ssl.endpoint.identification.algorithm": "https" if self.config._tls_validate_hostname else "none",
            "ssl.crl.location": self.config._crlfile,
            "enable.ssl.certificate.verification": self.config._tls_verify,
            "sasl.mechanism": self.config._sasl_mechanism,
            "sasl.username": self.config._sasl_plain_username,
            "sasl.password": self.config._sasl_plain_password,
            "sasl.kerberos.keytab": self.config._sasl_kerberos_keytab,
            "sasl.kerberos.principal": self.config._sasl_kerberos_principal,
            "sasl.kerberos.service.name": self.config._sasl_kerberos_service_name,
        }

        if self.config._sasl_mechanism == "OAUTHBEARER":
            extras_parameters['sasl.oauthbearer.method'] = "oidc"
            extras_parameters["sasl.oauthbearer.client.id"] = self.config._sasl_oauth_token_provider.get("client_id")
            extras_parameters["sasl.oauthbearer.token.endpoint.url"] = self.config._sasl_oauth_token_provider.get("url")
            extras_parameters["sasl.oauthbearer.client.secret"] = self.config._sasl_oauth_token_provider.get(
                "client_secret"
            )

        for key, value in extras_parameters.items():
            # Do not add the value if it's not specified
            if value:
                config[key] = value

        return config

    def get_highwater_offsets(self, consumer_offsets):
        highwater_offsets = {}
        topics_with_consumer_offset = {}
        if not self.config._monitor_all_broker_highwatermarks:
            topics_with_consumer_offset = {(topic, partition) for (_, topic, partition) in consumer_offsets}

        for consumer_group in consumer_offsets.items():
            consumer = self.__create_consumer(consumer_group)
            topics = consumer.list_topics(timeout=self.config._request_timeout)

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

                        highwater_offsets[(topic, partition)] = high_offset

        return highwater_offsets

    def get_partitions_for_topic(self, topic):
        try:
            cluster_metadata = self.kafka_client.list_topics(topic, timeout=self.config._request_timeout)
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
        consumer_offsets = {}

        if self.config._monitor_unlisted_consumer_groups:
            # Get all consumer groups
            consumer_groups = []
            consumer_groups_future = self.kafka_client.list_consumer_groups()
            self.log.debug('MONITOR UNLISTED CG FUTURES: %s', consumer_groups_future)
            try:
                list_consumer_groups_result = consumer_groups_future.result()
                self.log.debug('MONITOR UNLISTED FUTURES RESULT: %s', list_consumer_groups_result)

                consumer_groups.extend(
                    valid_consumer_group.group_id for valid_consumer_group in list_consumer_groups_result.valid
                )
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

        for future in self._get_consumer_offset_futures(consumer_groups):
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
                    consumer_offsets[(consumer_group, topic, partition)] = offset
            except KafkaException as e:
                self.log.debug("Failed to read consumer offsets for %s: %s", consumer_group, e)

        return consumer_offsets

    def _get_consumer_offset_futures(self, consumer_groups):
        topics = self.kafka_client.list_topics(timeout=self.config._request_timeout)
        # {(consumer_group, topic, partition): offset}

        for consumer_group in consumer_groups:
            self.log.debug('CONSUMER GROUP: %s', consumer_group)

            for topic_partition in self._get_topic_partitions(topics, consumer_group):
                yield self.kafka_client.list_consumer_group_offsets(
                    [ConsumerGroupTopicPartitions(consumer_group, [topic_partition])]
                )[consumer_group]

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
                        self.log.debug(
                            "Partition %s skipped because the topic %s is not in the consumer_group.", partition, topic
                        )
                        continue
                    if (
                        self.config._consumer_groups[consumer_group].get(topic)
                        and partition not in self.config._consumer_groups[consumer_group][topic]
                    ):
                        self.log.debug(
                            "Partition %s skipped because it is not defined in the consumer group for the topic %s",
                            partition,
                            topic,
                        )
                        continue

                self.log.debug("TOPIC PARTITION: %s", TopicPartition(topic, partition))

                yield TopicPartition(topic, partition)
