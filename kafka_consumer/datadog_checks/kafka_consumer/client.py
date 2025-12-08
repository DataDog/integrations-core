# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from concurrent.futures import as_completed

from confluent_kafka import Consumer, ConsumerGroupTopicPartitions, KafkaException, TopicPartition
from confluent_kafka.admin import AdminClient


class KafkaClient:
    def __init__(self, config, log) -> None:
        self.config = config
        self.log = log
        self._kafka_client = None
        self._consumer = None
        self._cluster_metadata = None

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

    def open_consumer(self, consumer_group):
        config = {
            "bootstrap.servers": self.config._kafka_connect_str,
            "group.id": consumer_group,
            "enable.auto.commit": False,  # To avoid offset commit to broker during close
            "queued.max.messages.kbytes": self.config._consumer_queued_max_messages_kbytes,
            "log_level": self.config._librdkafka_log_level,
        }
        config.update(self.__get_authentication_config())

        self._consumer = Consumer(config, logger=self.log)
        self.log.debug("Consumer instance %s created for group %s", self._consumer, consumer_group)

    def close_consumer(self):
        self.log.debug("Closing consumer instance %s", self._consumer)
        self._consumer.close()

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

    def consumer_get_cluster_id_and_list_topics(self, consumer_group):
        cluster_metadata = self._consumer.list_topics(timeout=self.config._request_timeout)
        try:
            # TODO: remove this try-except, the attribute is always present.
            cluster_id = cluster_metadata.cluster_id
        except AttributeError:
            self.log.error("Failed to get cluster metadata for consumer group %s", consumer_group)
            return "", []
        return (cluster_id, [(name, list(metadata.partitions)) for name, metadata in cluster_metadata.topics.items()])

    def consumer_offsets_for_times(self, partitions, offset=-1):
        topicpartitions_for_querying = [
            # -1: latest; 0: earliest (timestamp 0)
            TopicPartition(topic=topic, partition=partition, offset=offset)
            for topic, partition in partitions
        ]
        return [
            (tp.topic, tp.partition, tp.offset)
            for tp in self._consumer.offsets_for_times(
                partitions=topicpartitions_for_querying, timeout=self.config._request_timeout
            )
        ]

    def _list_topics(self):
        if self._cluster_metadata:
            return self._cluster_metadata

        try:
            self.request_metadata_update()

        except KafkaException as e:
            self.log.error("Received exception when listing topics: %s", e)

        return self._cluster_metadata

    def get_topic_partitions(self):
        topic_partitions = {}
        try:
            cluster_metadata = self._list_topics()
            for topic in cluster_metadata.topics:
                topic_metadata = cluster_metadata.topics[topic]
                partitions = list(topic_metadata.partitions)
                topic_partitions[topic] = partitions

        except KafkaException as e:
            self.log.error("Received exception when listing topics: %s", e)

        return topic_partitions

    def get_partitions_for_topic(self, topic):
        partitions = []
        try:
            cluster_metadata = self._list_topics()
        except KafkaException as e:
            self.log.error("Received exception when getting partitions for topic %s: %s", topic, e)
            return []

        if topic in cluster_metadata.topics:
            topic_metadata = cluster_metadata.topics[topic]
            partitions = list(topic_metadata.partitions)
        return partitions

    def request_metadata_update(self):
        # https://github.com/confluentinc/confluent-kafka-python/issues/594
        self._cluster_metadata = self.kafka_client.list_topics(None, timeout=self.config._request_timeout)

    def list_consumer_groups(self):
        groups = []
        try:
            groups_res = self.kafka_client.list_consumer_groups().result()
            for valid_group in groups_res.valid:
                self.log.debug("Discovered consumer group: %s", valid_group.group_id)
                groups.append(valid_group.group_id)
        except Exception as e:
            self.log.error("Failed to collect consumer groups: %s", e)
        return groups

    def list_consumer_group_offsets(self, groups):
        """
        For every group and (optionally) its topics and partitions retrieve consumer offsets.

        As input expects a list of tuples: (consumer_group_id, topic_partitions).
        topic_partitions are either None to indicate we want all topics and partitions OR a list of (topic, partition).

        Returns a list of tuples with members:
        1. group id
        2. list of tuples: (topic, partition, offset)
        """
        futures = []
        for consumer_group, topic_partitions in groups:
            topic_partitions = (
                topic_partitions if topic_partitions is None else [TopicPartition(t, p) for t, p in topic_partitions]
            )
            futures.append(
                self.kafka_client.list_consumer_group_offsets(
                    [ConsumerGroupTopicPartitions(group_id=consumer_group, topic_partitions=topic_partitions)]
                )[consumer_group]
            )
        offsets = []
        for completed in as_completed(futures):
            try:
                response_offset_info = completed.result()
            except KafkaException as e:
                self.log.debug("Failed to read consumer offsets for future %s: %s", completed, e)
                continue
            tpo = []
            for tp in response_offset_info.topic_partitions:
                if tp.error:
                    self.log.debug(
                        "Encountered error: %s. Occurred with topic: %s; partition: [%s]",
                        tp.error.str(),
                        tp.topic,
                        str(tp.partition),
                    )
                    continue
                tpo.append((tp.topic, tp.partition, tp.offset))
            offsets.append((response_offset_info.group_id, tpo))
        return offsets

    def start_collecting_messages(self, start_offsets, consumer_group):
        self.open_consumer(consumer_group)
        self._consumer.assign(start_offsets)

    def get_next_message(self):
        return self._consumer.poll(timeout=1)

    def delete_consumer_group(self, consumer_group):
        """Delete a consumer group using the AdminClient."""
        try:
            future = self.kafka_client.delete_consumer_groups([consumer_group])
            future[consumer_group].result(timeout=self.config._request_timeout)
            self.log.debug("Successfully deleted consumer group: %s", consumer_group)
        except Exception as e:
            self.log.warning("Failed to delete consumer group %s: %s", consumer_group, e)

    def describe_consumer_group(self, consumer_group):
        desc = self.kafka_client.describe_consumer_groups([consumer_group])[consumer_group].result()
        return desc.state.name

    def close_admin_client(self):
        self._kafka_client = None
