# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Kafka client wrapper for kafka_actions check."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, ConfigResource, NewTopic, OffsetSpec, ResourceType

try:
    import boto3
    from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

    AWS_MSK_IAM_AVAILABLE = True
except ImportError:
    AWS_MSK_IAM_AVAILABLE = False

if TYPE_CHECKING:
    from datadog_checks.kafka_actions.config import KafkaActionsConfig


class KafkaActionsClient:
    """Kafka client for performing actions on Kafka clusters."""

    def __init__(self, config: KafkaActionsConfig, log):
        self.config = config
        self.log = log
        self.consumer = None
        self.producer = None
        self.admin_client = None

    def _get_authentication_config(self) -> dict[str, Any]:
        """Build authentication configuration for librdkafka."""
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
            method = self.config._sasl_oauth_token_provider.get("method", "oidc")

            if method == "aws_msk_iam":
                if not AWS_MSK_IAM_AVAILABLE:
                    raise Exception(
                        "AWS MSK IAM authentication requires 'aws-msk-iam-sasl-signer-python' library. "
                        "Install it with: pip install aws-msk-iam-sasl-signer-python"
                    )

                def _aws_msk_iam_oauth_cb(oauth_config):
                    try:
                        region = self.config._sasl_oauth_token_provider.get("aws_region")
                        if not region:
                            region = boto3.session.Session().region_name

                        if not region:
                            raise Exception(
                                "AWS region could not be determined. Please specify 'aws_region' in "
                                "sasl_oauth_token_provider configuration."
                            )

                        auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token(region)
                        self.log.debug("Generated AWS MSK IAM token for region %s, expires in %s ms", region, expiry_ms)
                        return auth_token, expiry_ms / 1000
                    except Exception as e:
                        self.log.error("Failed to generate AWS MSK IAM token: %s", e)
                        raise

                extras_parameters['oauth_cb'] = _aws_msk_iam_oauth_cb

            elif method == "oidc":
                extras_parameters['sasl.oauthbearer.method'] = "oidc"
                extras_parameters["sasl.oauthbearer.client.id"] = self.config._sasl_oauth_token_provider.get(
                    "client_id"
                )
                extras_parameters["sasl.oauthbearer.token.endpoint.url"] = self.config._sasl_oauth_token_provider.get(
                    "url"
                )
                extras_parameters["sasl.oauthbearer.client.secret"] = self.config._sasl_oauth_token_provider.get(
                    "client_secret"
                )
                extras_parameters["sasl.oauthbearer.scope"] = self.config._sasl_oauth_token_provider.get("scope")
                extras_parameters["sasl.oauthbearer.extensions"] = self.config._sasl_oauth_token_provider.get(
                    "extensions"
                )
                if self.config._sasl_oauth_tls_ca_cert:
                    extras_parameters["https.ca.location"] = self.config._sasl_oauth_tls_ca_cert

        for key, value in extras_parameters.items():
            if value:
                config[key] = value

        return config

    def _get_kafka_config(self) -> dict[str, Any]:
        """Build full Kafka configuration."""
        kafka_config = {
            'bootstrap.servers': self.config.kafka_connect_str,
        }
        kafka_config.update(self._get_authentication_config())
        return kafka_config

    def get_consumer(self, group_id: str = 'kafka_actions') -> Consumer:
        """Get or create Kafka consumer.

        Args:
            group_id: Consumer group ID

        Returns:
            Kafka Consumer instance
        """
        if self.consumer is None:
            config = self._get_kafka_config()
            config.update(
                {
                    'group.id': group_id,
                    'auto.offset.reset': 'earliest',
                    'enable.auto.commit': False,
                }
            )
            self.consumer = Consumer(config)
            self.log.debug("Created Kafka consumer with group_id: %s", group_id)
        return self.consumer

    def get_producer(self) -> Producer:
        """Get or create Kafka producer.

        Returns:
            Kafka Producer instance
        """
        if self.producer is None:
            config = self._get_kafka_config()
            self.producer = Producer(config)
            self.log.debug("Created Kafka producer")
        return self.producer

    def get_admin_client(self) -> AdminClient:
        """Get or create Kafka admin client.

        Returns:
            Kafka AdminClient instance
        """
        if self.admin_client is None:
            config = self._get_kafka_config()
            self.admin_client = AdminClient(config)
            self.log.debug("Created Kafka admin client")
        return self.admin_client

    def get_cluster_id(self, timeout: int = 10) -> str:
        """Get the Kafka cluster ID.

        Args:
            timeout: Timeout in seconds for metadata request

        Returns:
            Kafka cluster ID string

        Raises:
            Exception: If unable to retrieve cluster ID
        """
        admin_client = self.get_admin_client()
        try:
            metadata = admin_client.list_topics(timeout=timeout)
            cluster_id = metadata.cluster_id
            self.log.debug("Retrieved Kafka cluster ID: %s", cluster_id)
            return cluster_id
        except Exception as e:
            self.log.error("Failed to retrieve Kafka cluster ID: %s", e)
            raise Exception(f"Unable to retrieve Kafka cluster ID: {e}")

    def consume_messages(
        self,
        topic: str,
        partition: int = -1,
        start_offset: int = -2,
        start_timestamp: int | None = None,
        max_messages: int = 1000,
        timeout_ms: int = 30000,
        group_id: str = 'kafka_actions',
    ):
        """Consume messages from a Kafka topic, yielding them as they arrive.

        This is a generator that yields messages in real-time as they're consumed,
        allowing for immediate processing and sending to Datadog.

        Args:
            topic: Topic name
            partition: Partition number (-1 for all partitions)
            start_offset: Starting offset (-1 for latest, -2 for earliest)
            start_timestamp: Starting timestamp in milliseconds since epoch. When set, start_offset is ignored.
            max_messages: Maximum messages to consume
            timeout_ms: Global timeout in milliseconds for the entire consumption
            group_id: Consumer group ID

        Yields:
            Kafka messages as they arrive
        """
        consumer = self.get_consumer(group_id)
        start_time = time.time()
        global_timeout_s = timeout_ms / 1000.0

        try:
            if partition == -1:
                metadata = consumer.list_topics(topic, timeout=10)
                if topic not in metadata.topics:
                    raise ValueError(f"Topic '{topic}' not found")

                partition_ids = list(metadata.topics[topic].partitions.keys())
            else:
                partition_ids = [partition]

            if start_timestamp is not None:
                # Resolve timestamp to per-partition offsets using offsets_for_times.
                timestamp_partitions = [TopicPartition(topic, p, start_timestamp) for p in partition_ids]
                partitions = consumer.offsets_for_times(timestamp_partitions, timeout=10)
                for tp in partitions:
                    if tp.offset != -1:
                        self.log.debug(
                            "Partition %d: timestamp %d resolved to offset %d",
                            tp.partition,
                            start_timestamp,
                            tp.offset,
                        )
            elif start_offset == -1:
                # For "latest" offset, seek back from the high watermark to read the last N existing messages.
                # Use AdminClient.list_offsets to fetch all high watermarks in a single batched call.
                admin = self.get_admin_client()
                offset_request = {TopicPartition(topic, p): OffsetSpec.latest() for p in partition_ids}
                futures = admin.list_offsets(offset_request, request_timeout=10)

                partitions = []
                for tp, future in futures.items():
                    result = future.result()
                    seek_offset = max(0, result.offset - max_messages)
                    partitions.append(TopicPartition(topic, tp.partition, seek_offset))
                    self.log.debug("Partition %d: high=%d, seeking to %d", tp.partition, result.offset, seek_offset)
            else:
                partitions = [TopicPartition(topic, p, start_offset) for p in partition_ids]

            self.log.debug("Assigning partitions: %s", partitions)
            consumer.assign(partitions)

            consumed = 0

            while consumed < max_messages:
                elapsed = time.time() - start_time
                remaining_timeout = global_timeout_s - elapsed

                if remaining_timeout <= 0:
                    self.log.debug("Global timeout reached after %d messages", consumed)
                    break

                poll_timeout = min(1.0, remaining_timeout)
                msg = consumer.poll(timeout=poll_timeout)

                if msg is None:
                    self.log.debug("Poll returned None (no more messages available), stopping consumption")
                    break

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        self.log.debug("Reached end of partition")
                        continue
                    else:
                        raise KafkaException(msg.error())

                yield msg
                consumed += 1

            self.log.debug("Consumed %d messages from topic %s in %.2fs", consumed, topic, time.time() - start_time)

        finally:
            if consumer:
                consumer.close()
                self.consumer = None

    def produce_message(
        self,
        topic: str,
        value: str | bytes,
        key: str | bytes | None = None,
        partition: int = -1,
        headers: dict[str, str | bytes] | None = None,
    ) -> dict[str, Any]:
        """Produce a message to a Kafka topic.

        Args:
            topic: Topic name
            value: Message value (string or bytes)
            key: Message key (optional, string or bytes)
            partition: Target partition (-1 for automatic)
            headers: Message headers (optional, values can be string or bytes)

        Returns:
            Dict with production metadata
        """
        producer = self.get_producer()

        if isinstance(value, str):
            value = value.encode('utf-8')
        if isinstance(key, str):
            key = key.encode('utf-8') if key else None

        kafka_headers = None
        if headers:
            kafka_headers = [(k, v.encode('utf-8') if isinstance(v, str) else v) for k, v in headers.items()]

        result = {'delivered': False, 'error': None, 'partition': None, 'offset': None}

        def delivery_callback(err, msg):
            if err:
                result['error'] = str(err)
                self.log.error("Message delivery failed: %s", err)
            else:
                result['delivered'] = True
                result['partition'] = msg.partition()
                result['offset'] = msg.offset()
                self.log.debug(
                    "Message delivered to %s [%d] at offset %d",
                    msg.topic(),
                    msg.partition(),
                    msg.offset(),
                )

        try:
            partition_arg = None if partition is None or partition == -1 else int(partition)

            self.log.debug(
                "Calling producer.produce with: topic=%s, key=%s, value_len=%d, partition=%s, headers=%s",
                topic,
                key,
                len(value) if value else 0,
                partition_arg,
                kafka_headers,
            )

            produce_kwargs = {
                'topic': topic,
                'value': value,
                'callback': delivery_callback,
            }
            if key is not None:
                produce_kwargs['key'] = key
            if partition_arg is not None:
                produce_kwargs['partition'] = partition_arg
            if kafka_headers is not None:
                produce_kwargs['headers'] = kafka_headers

            producer.produce(**produce_kwargs)
            producer.flush()

            return result

        except Exception as e:
            self.log.error("Failed to produce message: %s", e)
            result['error'] = str(e)
            return result

    def create_topic(
        self,
        topic: str,
        num_partitions: int = 1,
        replication_factor: int = 1,
        configs: dict[str, str] | None = None,
    ) -> bool:
        """Create a new Kafka topic.

        Args:
            topic: Topic name
            num_partitions: Number of partitions
            replication_factor: Replication factor
            configs: Topic configurations

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        new_topic = NewTopic(
            topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            config=configs or {},
        )

        futures = admin.create_topics([new_topic])

        for topic_name, future in futures.items():
            try:
                future.result()
                self.log.debug("Topic '%s' created successfully", topic_name)
                return True
            except Exception as e:
                self.log.error("Failed to create topic '%s': %s", topic_name, e)
                raise

    def delete_topic(self, topic: str) -> bool:
        """Delete a Kafka topic.

        Args:
            topic: Topic name

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        futures = admin.delete_topics([topic])

        for topic_name, future in futures.items():
            try:
                future.result()
                self.log.debug("Topic '%s' deleted successfully", topic_name)
                return True
            except Exception as e:
                self.log.error("Failed to delete topic '%s': %s", topic_name, e)
                raise

    def update_topic_config(self, topic: str, configs: dict[str, str]) -> bool:
        """Update topic configuration.

        Args:
            topic: Topic name
            configs: Configuration key-value pairs to update

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        resource = ConfigResource(ResourceType.TOPIC, topic)
        for key, value in configs.items():
            resource.set_config(key, value)

        futures = admin.alter_configs([resource])

        for _res, future in futures.items():
            try:
                future.result()
                self.log.debug("Topic '%s' configuration updated", topic)
                return True
            except Exception as e:
                self.log.error("Failed to update topic '%s' config: %s", topic, e)
                raise

    def delete_topic_config(self, topic: str, config_keys: list[str]) -> bool:
        """Delete (reset to default) topic configurations.

        Args:
            topic: Topic name
            config_keys: List of configuration keys to reset to defaults

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        resource = ConfigResource(ResourceType.TOPIC, topic)
        for key in config_keys:
            resource.set_config(key, None)

        futures = admin.alter_configs([resource])

        for _res, future in futures.items():
            try:
                future.result()
                self.log.debug("Topic '%s' configuration deleted: %s", topic, config_keys)
                return True
            except Exception as e:
                self.log.error("Failed to delete topic '%s' config: %s", topic, e)
                raise

    def delete_consumer_group(self, consumer_group: str) -> bool:
        """Delete a consumer group.

        Args:
            consumer_group: Consumer group ID

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        futures = admin.delete_consumer_groups([consumer_group])

        for group_id, future in futures.items():
            try:
                future.result()
                self.log.debug("Consumer group '%s' deleted successfully", group_id)
                return True
            except Exception as e:
                self.log.error("Failed to delete consumer group '%s': %s", group_id, e)
                raise

    def update_consumer_group_offsets(self, consumer_group: str, offsets: list[dict[str, Any]]) -> bool:
        """Update consumer group offsets for specific topic-partitions.

        Args:
            consumer_group: Consumer group ID
            offsets: List of offset specifications, each with:
                - topic: Topic name
                - partition: Partition number
                - offset: New offset value

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        topic_partitions = []
        for offset_spec in offsets:
            topic = offset_spec.get('topic')
            partition = offset_spec.get('partition')
            offset = offset_spec.get('offset')

            if topic is None or partition is None or offset is None:
                raise ValueError("Each offset specification must have 'topic', 'partition', and 'offset'")

            tp = TopicPartition(topic, partition, offset)
            topic_partitions.append(tp)

        futures = admin.alter_consumer_group_offsets(consumer_group, topic_partitions)

        for group_id, future in futures.items():
            try:
                future.result()
                self.log.debug("Consumer group '%s' offsets updated for %d partitions", group_id, len(topic_partitions))
                return True
            except Exception as e:
                self.log.error("Failed to update consumer group '%s' offsets: %s", group_id, e)
                raise

    def close(self):
        """Close all Kafka clients."""
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        if self.producer:
            self.producer.flush()
            self.producer = None
        self.admin_client = None
        self.log.debug("Kafka clients closed")

    def close_non_blocking(self):
        """Release all Kafka clients without blocking on pending operations.

        Safe to call from AgentCheck.cancel() which must not block.
        Uses purge/unassign to release resources immediately instead of
        flush/close which can block waiting on broker communication.
        """
        if self.consumer:
            self.consumer.unassign()
            self.consumer = None
        if self.producer:
            self.producer.purge()
            self.producer = None
        self.admin_client = None
        self.log.debug("Kafka clients released (non-blocking)")
