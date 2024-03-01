# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import as_completed

from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient

from datadog_checks.kafka_consumer.constants import KAFKA_INTERNAL_TOPICS, OFFSET_INVALID


class KafkaClient:
    def __init__(self, config, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self.topic_partition_cache = {}

    @property
    def kafka_client(self):
        if self._kafka_client is None:
            config = {
                "bootstrap.servers": self.config._kafka_connect_str,
                "socket.timeout.ms": self.config._request_timeout_ms,
                "client.id": "dd-agent",
                "log_level": self.config._librdkafka_log_level,
            }
            config.update(self.__get_authentication_config())

            self._kafka_client = AdminClient(config)

        return self._kafka_client

    def __create_consumer(self, consumer_group):
        config = {
            "bootstrap.servers": self.config._kafka_connect_str,
            "group.id": consumer_group,
            "enable.auto.commit": False,  # To avoid offset commit to broker during close
            "queued.max.messages.kbytes": self.config._consumer_queued_max_messages_kbytes,
            "log_level": self.config._librdkafka_log_level,
        }
        config.update(self.__get_authentication_config())

        return Consumer(config, logger=self.log)

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
        self.log.debug('Getting highwater offsets')

        cluster_id = ""
        highwater_offsets = {}
        topics_with_consumer_offset = set()
        topic_partition_with_consumer_offset = set()

        if not self.config._monitor_all_broker_highwatermarks:
            for _, topic, partition in consumer_offsets:
                topics_with_consumer_offset.add(topic)
                topic_partition_with_consumer_offset.add((topic, partition))

        topic_partition_checked = set()

        for consumer_group, _topic, _partition in consumer_offsets:
            self.log.debug('CONSUMER GROUP: %s', consumer_group)
            if (_topic, _partition) in topic_partition_checked:
                self.log.debug('Highwater offset already collected for topic %s with partition %s', _topic, _partition)
                continue

            topic_partitions_for_highwater_offsets = set()

            consumer = self.__create_consumer(consumer_group)
            self.log.debug("Consumer instance %s created for group %s", consumer, consumer_group)
            cluster_metadata = consumer.list_topics(timeout=self.config._request_timeout)
            try:
                cluster_id = cluster_metadata.cluster_id
            except AttributeError:
                self.log.error("Failed to get cluster metadata for consumer group %s", consumer_group)
            topics = cluster_metadata.topics

            for topic in topics:
                if topic in KAFKA_INTERNAL_TOPICS:
                    self.log.debug("Skipping internal topic %s", topic)
                    continue
                if not self.config._monitor_all_broker_highwatermarks and topic not in topics_with_consumer_offset:
                    self.log.debug("Skipping non-relevant topic %s", topic)
                    continue

                for partition in topics[topic].partitions:
                    if (
                        self.config._monitor_all_broker_highwatermarks
                        or (topic, partition) in topic_partition_with_consumer_offset
                    ):
                        # Setting offset to -1 will return the latest highwater offset while calling offsets_for_times
                        #   Reference: https://github.com/fede1024/rust-rdkafka/issues/460
                        topic_partitions_for_highwater_offsets.add(
                            TopicPartition(topic=topic, partition=partition, offset=-1)
                        )
                        self.log.debug('TOPIC: %s', topic)
                        self.log.debug('PARTITION: %s', partition)
                    else:
                        self.log.debug("Skipping non-relevant partition %s of topic %s", partition, topic)

            if len(topic_partitions_for_highwater_offsets) > 0:
                self.log.debug(
                    'Querying %s highwater offsets for consumer group %s',
                    len(topic_partitions_for_highwater_offsets),
                    consumer_group,
                )
                for topic_partition_with_highwater_offset in consumer.offsets_for_times(
                    partitions=list(topic_partitions_for_highwater_offsets),
                    timeout=self.config._request_timeout,
                ):
                    self.log.debug('Topic partition with highwater offset: %s', topic_partition_with_highwater_offset)
                    topic = topic_partition_with_highwater_offset.topic
                    partition = topic_partition_with_highwater_offset.partition
                    offset = topic_partition_with_highwater_offset.offset
                    highwater_offsets[(topic, partition)] = offset
                    self.log.debug("Adding %s %s to checked set to facilitate early exit", topic, partition)
                    topic_partition_checked.add((topic, partition))
            else:
                self.log.debug('No new highwater offsets to query for consumer group %s', consumer_group)

            self.log.debug("Closing consumer instance %s", consumer)
            consumer.close()

        self.log.debug('Got %s highwater offsets', len(highwater_offsets))
        return highwater_offsets, cluster_id

    def get_partitions_for_topic(self, topic):
        if partitions := self.topic_partition_cache.get(topic):
            return partitions

        try:
            cluster_metadata = self.kafka_client.list_topics(topic, timeout=self.config._request_timeout)
        except KafkaException as e:
            self.log.error("Received exception when getting partitions for topic %s: %s", topic, e)
            return None
        else:
            topic_metadata = cluster_metadata.topics[topic]
            partitions = list(topic_metadata.partitions.keys())
            self.topic_partition_cache[topic] = partitions
            return partitions

    def request_metadata_update(self):
        # https://github.com/confluentinc/confluent-kafka-python/issues/594
        self.kafka_client.list_topics(None, timeout=self.config._request_timeout)

    def get_consumer_offsets(self):
        # {(consumer_group, topic, partition): offset}
        self.log.debug('Getting consumer offsets')
        consumer_offsets = {}

        consumer_groups = self._get_consumer_groups()
        self.log.debug('Identified %s consumer groups', len(consumer_groups))

        futures = self._get_consumer_offset_futures(consumer_groups)
        self.log.debug('%s futures to be waited on', len(futures))

        for future in as_completed(futures):
            try:
                response_offset_info = future.result()
            except KafkaException as e:
                self.log.debug("Failed to read consumer offsets for future %s: %s", future, e)
            else:
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
                        continue

                    if offset == OFFSET_INVALID:
                        continue

                    if self.config._monitor_unlisted_consumer_groups or not self.config._consumer_groups_compiled_regex:
                        consumer_offsets[(consumer_group, topic, partition)] = offset
                    else:
                        to_match = f"{consumer_group},{topic},{partition}"
                        if self.config._consumer_groups_compiled_regex.match(to_match):
                            consumer_offsets[(consumer_group, topic, partition)] = offset

        self.log.debug('Got %s consumer offsets', len(consumer_offsets))
        return consumer_offsets

    def _get_consumer_groups(self):
        # Get all consumer groups to monitor
        consumer_groups = []
        if self.config._monitor_unlisted_consumer_groups or self.config._consumer_groups_compiled_regex:
            consumer_groups_future = self.kafka_client.list_consumer_groups()
            try:
                list_consumer_groups_result = consumer_groups_future.result()
                for valid_consumer_group in list_consumer_groups_result.valid:
                    self.log.debug("Discovered consumer group: %s", valid_consumer_group.group_id)

                consumer_groups.extend(
                    valid_consumer_group.group_id
                    for valid_consumer_group in list_consumer_groups_result.valid
                    if valid_consumer_group.group_id != ""
                )
            except Exception as e:
                self.log.error("Failed to collect consumer groups: %s", e)
            return consumer_groups
        else:
            return self.config._consumer_groups

    def _list_consumer_group_offsets(self, cg_tp):
        return self.kafka_client.list_consumer_group_offsets([cg_tp])

    def close_admin_client(self):
        self._kafka_client = None

    def _get_consumer_offset_futures(self, consumer_groups):
        futures = []

        # If either monitoring all consumer groups or regex, return all consumer group offsets (can filter later)
        if self.config._monitor_unlisted_consumer_groups or self.config._consumer_groups_compiled_regex:
            for consumer_group in consumer_groups:
                futures.append(
                    self._list_consumer_group_offsets(ConsumerGroupTopicPartitions(consumer_group))[consumer_group]
                )
            return futures

        for consumer_group in consumer_groups:
            # If topics are specified
            topics = consumer_groups.get(consumer_group)
            if not topics:
                futures.append(
                    self._list_consumer_group_offsets(ConsumerGroupTopicPartitions(consumer_group))[consumer_group]
                )
                continue

            for topic in topics:
                # If partitions are defined
                if partitions := topics[topic]:
                    topic_partitions = [TopicPartition(topic, partition) for partition in partitions]
                # If partitions are not defined
                else:
                    # get all the partitions for this topic
                    partitions = self.get_partitions_for_topic(topic)

                    topic_partitions = [TopicPartition(topic, partition) for partition in partitions]

                futures.append(
                    self._list_consumer_group_offsets(ConsumerGroupTopicPartitions(consumer_group, topic_partitions))[
                        consumer_group
                    ]
                )

        return futures
