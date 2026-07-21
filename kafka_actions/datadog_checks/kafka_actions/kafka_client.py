# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Kafka client wrapper for kafka_actions check."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from confluent_kafka import (
    Consumer,
    ConsumerGroupTopicPartitions,
    KafkaError,
    KafkaException,
    Producer,
    TopicPartition,
)
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
        # True when consume_messages stopped on the timeout rather than draining all partitions.
        self.hit_timeout = False

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
                    # Signal end-of-partition via a _PARTITION_EOF event so we stop once drained.
                    'enable.partition.eof': True,
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
        timeout_ms: int = 5000,
        group_id: str = 'kafka_actions',
    ):
        """Consume the messages already present in a topic, yielding them as they are read.

        The per-partition high watermark is captured before consumption begins and no message
        at or beyond it is yielded, so messages produced after the check starts are never
        returned and the generator can't tail a live topic. A partition stops on EOF or when its
        captured watermark is reached; the generator returns once all are drained. ``timeout_ms``
        is only a safety net.

        Args:
            topic: Topic name
            partition: Partition number (-1 for all partitions)
            start_offset: Starting offset (-1 for latest, -2 for earliest)
            start_timestamp: Starting timestamp in milliseconds since epoch. When set, start_offset is ignored.
            max_messages: Maximum messages to consume
            timeout_ms: Safety-net timeout in milliseconds for the entire consumption
            group_id: Consumer group ID

        Yields:
            Kafka messages that existed in the log when consumption began
        """
        consumer = self.get_consumer(group_id)
        admin = self.get_admin_client()
        start_time = time.time()
        global_timeout_s = timeout_ms / 1000.0
        self.hit_timeout = False

        try:
            if partition == -1:
                partition_ids = self._discover_partition_ids(consumer, topic)
            else:
                partition_ids = [partition]

            # Snapshot each partition's high watermark; we never read at or beyond it.
            end_request = {TopicPartition(topic, p): OffsetSpec.latest() for p in partition_ids}
            end_futures = admin.list_offsets(end_request, request_timeout=10)
            end_offsets = {tp.partition: future.result().offset for tp, future in end_futures.items()}

            start_offsets = self._resolve_start_offsets(
                consumer, admin, topic, partition_ids, start_offset, start_timestamp, max_messages, end_offsets
            )

            # Assign only partitions that have messages in [start, high_watermark).
            partitions = []
            active = set()
            for p in partition_ids:
                start = start_offsets.get(p, 0)
                end = end_offsets.get(p, 0)
                if start < end:
                    partitions.append(TopicPartition(topic, p, start))
                    active.add(p)
                else:
                    self.log.debug("Partition %d: nothing to read (start=%d, high=%d)", p, start, end)

            if not partitions:
                self.log.debug("No messages to read for topic %s in [start, high-watermark)", topic)
                return

            self.log.debug("Assigning partitions: %s (high watermarks: %s)", partitions, end_offsets)
            consumer.assign(partitions)

            consumed = 0

            while consumed < max_messages and active:
                elapsed = time.time() - start_time
                remaining_timeout = global_timeout_s - elapsed

                if remaining_timeout <= 0:
                    self.hit_timeout = True
                    self.log.debug("Global timeout reached after %d messages", consumed)
                    break

                poll_timeout = min(1.0, remaining_timeout)
                msg = consumer.poll(timeout=poll_timeout)

                if msg is None:
                    # End-of-data arrives as an EOF event, not None; keep polling until drained.
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        active.discard(msg.partition())
                        continue
                    else:
                        raise KafkaException(msg.error())

                p = msg.partition()
                # Never surface a message at or beyond the captured high watermark.
                if p not in active or msg.offset() >= end_offsets.get(p, 0):
                    active.discard(p)
                    continue

                yield msg
                consumed += 1

                if msg.offset() >= end_offsets[p] - 1:
                    active.discard(p)

            self.log.debug("Consumed %d messages from topic %s in %.2fs", consumed, topic, time.time() - start_time)

        finally:
            if consumer:
                consumer.close()
                self.consumer = None

    def _discover_partition_ids(self, client, topic: str) -> list[int]:
        """Look up all partition IDs for a topic via the given client's list_topics."""
        metadata = client.list_topics(topic, timeout=10)
        if topic not in metadata.topics:
            raise ValueError(f"Topic '{topic}' not found")
        return list(metadata.topics[topic].partitions.keys())

    def _resolve_start_offsets(
        self,
        consumer,
        admin,
        topic: str,
        partition_ids: list[int],
        start_offset: int,
        start_timestamp: int | None,
        max_messages: int,
        end_offsets: dict[int, int],
    ) -> dict[int, int]:
        """Return a {partition: start_offset} map. A start at or beyond the high watermark
        means there is nothing to read for that partition."""
        if start_timestamp is not None:
            # An offset < 0 means the timestamp is past the end of the log: nothing to read.
            timestamp_partitions = [TopicPartition(topic, p, start_timestamp) for p in partition_ids]
            resolved = consumer.offsets_for_times(timestamp_partitions, timeout=10)
            start_offsets = {}
            for tp in resolved:
                end = end_offsets.get(tp.partition, 0)
                start_offsets[tp.partition] = tp.offset if tp.offset is not None and tp.offset >= 0 else end
            return start_offsets

        if start_offset == -1:
            # "latest": seek back from the high watermark to read the last N existing messages.
            return {p: max(0, end_offsets.get(p, 0) - max_messages) for p in partition_ids}

        if start_offset == -2:
            # "earliest": use the low watermark as the numeric start.
            low_request = {TopicPartition(topic, p): OffsetSpec.earliest() for p in partition_ids}
            low_futures = admin.list_offsets(low_request, request_timeout=10)
            return {tp.partition: future.result().offset for tp, future in low_futures.items()}

        return dict.fromkeys(partition_ids, start_offset)

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

    def check_consumer_group_inactive(self, consumer_group: str) -> None:
        """Raise if the consumer group has active members.

        alter_consumer_group_offsets requires a dead or empty group; active members
        cause Kafka to return NON_EMPTY_GROUP errors per partition.
        """
        admin = self.get_admin_client()
        futures = admin.describe_consumer_groups([consumer_group], request_timeout=10)
        future = futures[consumer_group]
        try:
            description = future.result()
        except Exception as e:
            self.log.error("Failed to describe consumer group '%s': %s", consumer_group, e)
            raise
        if description.members:
            raise Exception(
                f"Consumer group '{consumer_group}' has {len(description.members)} active member(s). "
                "Stop all consumers in the group before resetting offsets."
            )

    def _resolve_sentinel_offsets(
        self, admin: AdminClient, requests: list[tuple[str, int, int]]
    ) -> dict[tuple[str, int], int]:
        """Resolve a batch of sentinel offset values (-1 latest, -2 earliest) to concrete offsets.

        requests is a list of (topic, partition, offset) tuples; returns a dict keyed by
        (topic, partition) mapping to the resolved concrete offset.
        """
        tp_by_key = {}
        offset_request = {}
        for topic, partition, offset in requests:
            if offset not in (-1, -2):
                raise ValueError(f"Sentinel offset must be -1 (latest) or -2 (earliest), got {offset}")
            tp = TopicPartition(topic, partition)
            tp_by_key[(topic, partition)] = tp
            offset_request[tp] = OffsetSpec.earliest() if offset == -2 else OffsetSpec.latest()

        futures = admin.list_offsets(offset_request, request_timeout=10)
        resolved = {}
        for (topic, partition), tp in tp_by_key.items():
            try:
                resolved[(topic, partition)] = futures[tp].result().offset
            except Exception as e:
                self.log.error("Failed to resolve sentinel offset for %s[%d]: %s", topic, partition, e)
                raise
        return resolved

    def _resolve_sentinel_offset(self, admin: AdminClient, topic: str, partition: int, offset: int) -> int:
        """Resolve a single sentinel offset value (-1 latest, -2 earliest) to a concrete offset."""
        return self._resolve_sentinel_offsets(admin, [(topic, partition, offset)])[(topic, partition)]

    def _resolve_timestamp_targets(
        self, admin: AdminClient, topic: str, partition: int | None, timestamp: int
    ) -> list[TopicPartition]:
        """Resolve a timestamp offset spec to concrete TopicPartitions for one or all partitions of a topic."""
        partition_ids = [partition] if partition is not None else self._discover_partition_ids(admin, topic)

        offset_request = {TopicPartition(topic, p): OffsetSpec.for_timestamp(timestamp) for p in partition_ids}
        futures = admin.list_offsets(offset_request, request_timeout=10)

        resolved_by_partition = {}
        for tp, future in futures.items():
            try:
                resolved_by_partition[tp.partition] = future.result().offset
            except Exception as e:
                self.log.error("Failed to resolve timestamp offset for %s[%d]: %s", topic, tp.partition, e)
                raise

        no_message_partitions = [p for p, offset in resolved_by_partition.items() if offset == -1]
        if no_message_partitions:
            fallback = self._resolve_sentinel_offsets(admin, [(topic, p, -1) for p in no_message_partitions])
            for p in no_message_partitions:
                resolved_by_partition[p] = fallback[(topic, p)]
                self.log.debug(
                    "Partition %d: no message at timestamp %d, using latest offset %d",
                    p,
                    timestamp,
                    resolved_by_partition[p],
                )

        resolved_partitions = []
        for partition_id, resolved in resolved_by_partition.items():
            if partition_id not in no_message_partitions:
                self.log.debug("Partition %d: timestamp %d resolved to offset %d", partition_id, timestamp, resolved)
            resolved_partitions.append(TopicPartition(topic, partition_id, resolved))
        return resolved_partitions

    def _resolve_explicit_target(self, admin: AdminClient, topic: str, partition: int, offset: int) -> TopicPartition:
        """Resolve an explicit or sentinel offset spec to a concrete TopicPartition."""
        if offset in (-1, -2):
            resolved = self._resolve_sentinel_offset(admin, topic, partition, offset)
            label = 'earliest' if offset == -2 else 'latest'
            self.log.debug("Resolved '%s' for %s[%d] to offset %d", label, topic, partition, resolved)
        else:
            resolved = offset
        return TopicPartition(topic, partition, resolved)

    def update_consumer_group_offsets(self, consumer_group: str, offsets: list[dict[str, Any]]) -> bool:
        """Update consumer group offsets for specific topic-partitions.

        Args:
            consumer_group: Consumer group ID
            offsets: List of offset specifications, each with:
                - topic: Topic name (required)
                - partition: Partition number. Required when 'offset' is specified;
                  optional when 'timestamp' is specified (auto-discovers all partitions).
                - offset: Offset to commit. Use -2 for earliest, -1 for latest, or a
                  non-negative integer for an explicit offset. Mutually exclusive with timestamp.
                - timestamp: Milliseconds since epoch. Resets to the first offset at or after
                  this timestamp in each matching partition. When no message exists at or after
                  the timestamp the partition is reset to latest. Mutually exclusive with offset.

        Returns:
            True if successful
        """
        admin = self.get_admin_client()

        topic_partitions = []
        seen_targets = set()
        for offset_spec in offsets:
            topic = offset_spec.get('topic')
            partition = offset_spec.get('partition')
            offset = offset_spec.get('offset')
            timestamp = offset_spec.get('timestamp')

            if topic is None:
                raise ValueError("Each offset specification must have 'topic'")
            if offset is not None and timestamp is not None:
                raise ValueError(f"offsets entry for topic '{topic}' cannot specify both 'offset' and 'timestamp'")

            if timestamp is not None:
                targets = self._resolve_timestamp_targets(admin, topic, partition, timestamp)
            else:
                if partition is None:
                    raise ValueError("Each offset specification must have 'partition' when 'offset' is specified")
                targets = [self._resolve_explicit_target(admin, topic, partition, offset)]

            for tp in targets:
                key = (tp.topic, tp.partition)
                if key in seen_targets:
                    raise ValueError(
                        f"Multiple offset specifications target the same partition: {tp.topic}[{tp.partition}]"
                    )
                seen_targets.add(key)
                topic_partitions.append(tp)

        futures = admin.alter_consumer_group_offsets([ConsumerGroupTopicPartitions(consumer_group, topic_partitions)])

        for group_id, future in futures.items():
            try:
                result = future.result()
            except Exception as e:
                self.log.error("Failed to update consumer group '%s' offsets: %s", group_id, e)
                raise

            partition_errors = [
                f"{tp.topic}[{tp.partition}]: {tp.error}" for tp in result.topic_partitions if tp.error is not None
            ]
            if partition_errors:
                error_msg = f"Per-partition errors for group '{group_id}': {'; '.join(partition_errors)}"
                self.log.error(error_msg)
                raise Exception(error_msg)

            self.log.debug("Consumer group '%s' offsets updated for %d partitions", group_id, len(topic_partitions))
            return True

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
