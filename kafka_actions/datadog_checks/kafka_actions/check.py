# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import base64
import json
import time

from datadog_checks.base import AgentCheck

from .config import KafkaActionsConfig
from .kafka_client import KafkaActionsClient
from .message_deserializer import DeserializedMessage, MessageDeserializer


class KafkaActionsCheck(AgentCheck):
    """
    Kafka Actions Check - Performs one-time actions on Kafka clusters.

    This check is designed to run once per execution and perform a specific action
    defined in the configuration.
    """

    __NAMESPACE__ = 'kafka_actions'

    def __init__(self, name, init_config, instances):
        super(KafkaActionsCheck, self).__init__(name, init_config, instances)

        self.config = KafkaActionsConfig(self.instance, self.log)
        self.config.validate_config()

        self.remote_config_id = self.config.remote_config_id
        self.action = self.config.action

        self.kafka_client = KafkaActionsClient(self.instance, self.log)
        self.deserializer = MessageDeserializer(self.log)

        self.action_handlers = {
            'read_messages': self._action_read_messages,
            'create_topic': self._action_create_topic,
            'update_topic_config': self._action_update_topic_config,
            'delete_topic': self._action_delete_topic,
            'delete_consumer_group': self._action_delete_consumer_group,
            'update_consumer_group_offsets': self._action_update_consumer_group_offsets,
            'produce_message': self._action_produce_message,
        }

        self.log.debug(
            "Kafka Actions check initialized - Action: %s, Remote Config ID: %s", self.action, self.remote_config_id
        )

    def check(self, _):
        """Execute the configured action once."""
        self.log.debug("Executing Kafka action: %s (Remote Config ID: %s)", self.action, self.remote_config_id)

        try:
            handler = self.action_handlers[self.action]
            result = handler()

            self._emit_action_event(
                success=True,
                action=self.action,
                message=f"Kafka action '{self.action}' completed successfully",
                cluster=self.cluster,
                event_data=result if isinstance(result, dict) else None,
            )

            self.log.debug("Kafka action '%s' completed successfully", self.action)

        except Exception as e:
            error_msg = str(e)
            self.log.exception("Kafka action '%s' failed: %s", self.action, error_msg)

            self._emit_action_event(
                success=False,
                action=self.action,
                message=f"Kafka action '{self.action}' failed: {error_msg}",
                cluster=getattr(self, 'cluster', 'unknown'),
            )
            raise
        finally:
            self.kafka_client.close()

    def _verify_cluster_id(self):
        """Verify that the configured cluster matches the actual Kafka cluster ID.

        Raises:
            Exception: If cluster verification fails
        """
        if not self.cluster:
            self.log.debug("No cluster parameter in action config, skipping cluster verification")
            return

        try:
            actual_cluster_id = self.kafka_client.get_cluster_id()
        except Exception as e:
            raise Exception(
                f"Failed to retrieve Kafka cluster ID for verification. "
                f"Unable to verify that the configured cluster '{self.cluster}' "
                f"matches the actual Kafka cluster: {e}"
            )

        if not self._normalize_cluster_id(self.cluster) or not self._normalize_cluster_id(actual_cluster_id):
            raise Exception(f"Invalid cluster ID format. Configured: '{self.cluster}', Actual: '{actual_cluster_id}'")

        if self._normalize_cluster_id(self.cluster) != self._normalize_cluster_id(actual_cluster_id):
            raise Exception(
                f"Cluster ID mismatch! Configured cluster '{self.cluster}' does not match "
                f"actual Kafka cluster ID '{actual_cluster_id}'. "
                f"This action is configured to run on '{self.cluster}' "
                f"but you are connected to '{actual_cluster_id}'."
            )

        self.log.debug("Cluster ID verification successful: '%s' matches '%s'", self.cluster, actual_cluster_id)

    @staticmethod
    def _normalize_cluster_id(cluster_id: str) -> str:
        """Normalize cluster ID for comparison.

        Args:
            cluster_id: Cluster ID string

        Returns:
            Normalized cluster ID (lowercase, stripped)
        """
        if not cluster_id:
            return ""
        return str(cluster_id).lower().strip()

    def _get_tags(self):
        """Get common tags for metrics and events."""
        tags = []

        tags.append(f'action:{self.action}')
        tags.append(f'remote_config_id:{self.remote_config_id}')

        if 'tags' in self.instance:
            tags.extend(self.instance['tags'])

        return tags

    def _emit_action_event(
        self, success: bool, action: str, message: str, cluster: str, event_data: dict | None = None
    ):
        """Emit an event for action success or failure.

        Args:
            success: Whether the action succeeded
            action: Action name
            message: Event message
            cluster: Kafka cluster ID
            event_data: Optional dict with additional event data (stats, metadata, etc.)
        """
        event_type = 'success' if success else 'error'
        alert_type = 'success' if success else 'error'

        payload = {
            'action': action,
            'remote_config_id': self.remote_config_id,
            'status': 'success' if success else 'failure',
            'message': message,
        }

        if event_data:
            if 'messages_scanned' in event_data:
                payload['stats'] = event_data
            else:
                payload.update(event_data)

        event_text = json.dumps(payload, indent=2)

        tags = self._get_tags() + [f'kafka_cluster_id:{cluster}']

        event_payload = {
            'timestamp': int(time.time()),
            'event_type': f'kafka_action_{event_type}',
            'msg_title': f'Kafka Action {action.replace("_", " ").title()}: {event_type.title()}',
            'msg_text': event_text,
            'alert_type': alert_type,
            'source_type_name': 'kafka',
            'aggregation_key': f'kafka_action_{action}_{self.remote_config_id}',
            'tags': tags,
        }

        self.log.info(
            "Sending Kafka action event to Datadog: action=%s, status=%s, event_type=%s",
            action,
            'success' if success else 'failure',
            f'kafka_action_{event_type}',
        )
        self.log.info("Event payload: %s", json.dumps(event_payload, indent=2))

        self.event(event_payload)

    # =========================================================================
    # Action Handlers (RFC-Compliant)
    # =========================================================================

    def _action_read_messages(self):
        """Read messages from Kafka with filtering (RFC Action #1).

        Config format:
            read_messages:
                cluster: prod-kafka-1
                topic: orders
                partition: -1  # -1 for all partitions
                start_offset: -1  # -1 for latest, -2 for earliest, or specific offset
                n_messages_retrieved: 10  # Max matching messages to retrieve
                max_scanned_messages: 1000  # Max messages to scan through
                filter: ""  # jq expression (optional)
                consumer_group_id: ""  # Optional, defaults to: datadog-agent-<remote_config_id>

        Returns:
            Dict with stats about the operation
        """
        config = self.config.read_messages
        start_time = time.time()

        self.log.info("Read messages config: %s", json.dumps(dict(config), indent=2))

        self.cluster = config['cluster']
        self._verify_cluster_id()
        topic = config['topic']
        partition = config.get('partition', -1)
        start_offset = config.get('start_offset', -1)
        n_messages_retrieved = config.get('n_messages_retrieved', 10)
        max_scanned_messages = config.get('max_scanned_messages', 1000)
        timeout_ms = config.get('timeout_ms', 20000)
        filter_expression = config.get('filter', '')
        consumer_group_id = config.get('consumer_group_id') or f"datadog-agent-{self.remote_config_id}"

        deser_config = {
            'value_format': config.get('value_format', 'json'),
            'value_schema': config.get('value_schema'),
            'value_uses_schema_registry': config.get('value_uses_schema_registry', False),
            'key_format': config.get('key_format', 'json'),
            'key_schema': config.get('key_schema'),
            'key_uses_schema_registry': config.get('key_uses_schema_registry', False),
        }

        self.log.debug(
            "Reading messages from cluster '%s', topic '%s' (partition: %s, max_retrieved: %d, max_scanned: %d)",
            self.cluster,
            topic,
            partition,
            n_messages_retrieved,
            max_scanned_messages,
        )
        self.log.debug("Using consumer group: %s", consumer_group_id)

        scanned_count = 0
        sent_count = 0
        filtered_out_count = 0
        hit_scan_limit = False
        hit_retrieved_limit = False

        for raw_msg in self.kafka_client.consume_messages(
            topic=topic,
            partition=partition,
            start_offset=start_offset,
            max_messages=max_scanned_messages,
            timeout_ms=timeout_ms,
            group_id=consumer_group_id,
        ):
            scanned_count += 1

            deserialized_msg = DeserializedMessage(raw_msg, self.deserializer, deser_config)

            if filter_expression:
                if not self._evaluate_filter(filter_expression, deserialized_msg):
                    filtered_out_count += 1
                    continue

            self._emit_message_event_deserialized(deserialized_msg, self.cluster)
            sent_count += 1

            if sent_count >= n_messages_retrieved:
                hit_retrieved_limit = True
                break

        if scanned_count >= max_scanned_messages and sent_count < n_messages_retrieved:
            hit_scan_limit = True

        elapsed_time = time.time() - start_time

        stats = {
            'cluster': self.cluster,
            'topic': topic,
            'partition': partition,
            'messages_scanned': scanned_count,
            'messages_sent': sent_count,
            'messages_filtered_out': filtered_out_count,
            'hit_scan_limit': hit_scan_limit,
            'hit_retrieved_limit': hit_retrieved_limit,
            'elapsed_time_seconds': round(elapsed_time, 3),
            'n_messages_retrieved': n_messages_retrieved,
            'max_scanned_messages': max_scanned_messages,
        }

        self.log.debug(
            "Read messages stats: scanned=%d, sent=%d, filtered=%d, time=%.3fs",
            scanned_count,
            sent_count,
            filtered_out_count,
            elapsed_time,
        )

        if hit_scan_limit:
            self.log.warning(
                "Hit max_scanned_messages limit (%d) before retrieving %d messages. Only found %d matching messages.",
                max_scanned_messages,
                n_messages_retrieved,
                sent_count,
            )

        return stats

    def _evaluate_filter(self, filter_expression: str, deserialized_msg: DeserializedMessage) -> bool:
        """Evaluate jq-style filter expression on deserialized message.

        Args:
            filter_expression: jq expression (e.g., '.value.status == "failed"')
            deserialized_msg: DeserializedMessage with lazy deserialization

        Returns:
            True if message matches filter, False otherwise
        """
        try:
            msg_dict = {
                'key': deserialized_msg.key,
                'value': deserialized_msg.value,
                'topic': deserialized_msg.topic,
                'partition': deserialized_msg.partition,
                'offset': deserialized_msg.offset,
            }

            # Simple jq expression parser
            # Supports: .field.subfield == "value", .field > 100, .field contains "text"
            # Supports: and, or operators
            result = self._evaluate_jq_expression(filter_expression, msg_dict)
            self.log.debug("Filter '%s' evaluated to: %s", filter_expression, result)
            return result

        except Exception as e:
            self.log.warning("Filter evaluation failed for '%s': %s", filter_expression, e)
            return False

    def _evaluate_jq_expression(self, expression: str, context: dict) -> bool:
        """Evaluate a jq-style expression.

        Args:
            expression: Filter expression (e.g., '.value.status == "active"')
            context: Dictionary with message data

        Returns:
            Boolean result of the expression
        """
        if ' and ' in expression:
            parts = expression.split(' and ')
            return all(self._evaluate_jq_expression(part.strip(), context) for part in parts)
        if ' or ' in expression:
            parts = expression.split(' or ')
            return any(self._evaluate_jq_expression(part.strip(), context) for part in parts)

        operators = ['==', '!=', '>=', '<=', '>', '<', ' contains ']
        for op in operators:
            if op in expression:
                left, right = expression.split(op, 1)
                left = left.strip()
                right = right.strip()

                left_value = self._get_field_from_path(left, context)
                right_value = self._parse_literal(right)

                if op == '==':
                    return left_value == right_value
                elif op == '!=':
                    return left_value != right_value
                elif op == '>':
                    return left_value > right_value
                elif op == '<':
                    return left_value < right_value
                elif op == '>=':
                    return left_value >= right_value
                elif op == '<=':
                    return left_value <= right_value
                elif op == ' contains ':
                    if isinstance(left_value, (list, str)):
                        return right_value in left_value
                    return False

        # No operator found - treat as existence check
        value = self._get_field_from_path(expression, context)
        return value is not None

    def _get_field_from_path(self, path: str, context: dict):
        """Get field value from dotted path (e.g., '.value.user.country').

        Args:
            path: Field path starting with '.'
            context: Dictionary to navigate

        Returns:
            Field value or None if not found
        """
        if not path.startswith('.'):
            return None

        parts = path[1:].split('.')
        current = context

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current

    def _parse_literal(self, value_str: str):
        """Parse a literal value from string.

        Args:
            value_str: String representation of value

        Returns:
            Parsed value (string, number, boolean, None)
        """
        value_str = value_str.strip()

        if (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]

        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        if value_str.lower() == 'null':
            return None

        return value_str

    def _emit_message_event_deserialized(self, deserialized_msg: DeserializedMessage, cluster: str):
        """Emit a deserialized Kafka message as a Datadog event.

        Args:
            deserialized_msg: DeserializedMessage object
            cluster: Kafka cluster identifier
        """
        msg_dict = deserialized_msg.to_dict()

        event_data = {
            'topic': deserialized_msg.topic,
            'partition': deserialized_msg.partition,
            'offset': deserialized_msg.offset,
            'timestamp': deserialized_msg.timestamp,
            'key': msg_dict.get('key'),
            'value': msg_dict.get('value'),
        }

        if msg_dict.get('headers'):
            event_data['headers'] = msg_dict['headers']

        if deserialized_msg.value_schema_id:
            event_data['value_schema_id'] = deserialized_msg.value_schema_id
        if deserialized_msg.key_schema_id:
            event_data['key_schema_id'] = deserialized_msg.key_schema_id

        event_text = json.dumps(event_data, indent=2)

        event_tags = self._get_tags() + [
            f'kafka_cluster_id:{cluster}',
            f'topic:{deserialized_msg.topic}',
            f'partition:{deserialized_msg.partition}',
            f'offset:{deserialized_msg.offset}',
        ]

        event_title = f'Kafka Message: {deserialized_msg.topic}'

        agg_key = (
            f'kafka_{deserialized_msg.topic}_{deserialized_msg.partition}_'
            f'{deserialized_msg.offset}_{self.remote_config_id}'
        )

        event_payload = {
            'timestamp': int(time.time()),
            'event_type': 'kafka_message',
            'msg_title': event_title,
            'msg_text': event_text,
            'tags': event_tags,
            'source_type_name': 'kafka',
            'aggregation_key': agg_key,
        }

        self.log.info(
            "Sending Kafka message event to Datadog: topic=%s, partition=%d, offset=%d, event_type=%s",
            deserialized_msg.topic,
            deserialized_msg.partition,
            deserialized_msg.offset,
            'kafka_message',
        )
        self.log.info("Event payload: %s", json.dumps(event_payload, indent=2))

        self.event(event_payload)

    def _format_for_display(self, data) -> str:
        """Format data for display in event.

        Args:
            data: Data to format (dict, str, etc.)

        Returns:
            Formatted string
        """
        if data is None:
            return ""
        if isinstance(data, dict):
            return json.dumps(data, indent=2)
        if isinstance(data, str):
            return data
        return str(data)

    def _action_create_topic(self):
        """Create a new Kafka topic (RFC Action #2).

        Config format:
            create_topic:
                cluster: prod-kafka-1
                topic: orders-v2
                num_partitions: 6
                replication_factor: 3
                configs:
                    retention.ms: "604800000"
                    compression.type: "snappy"
        """
        config = self.config.create_topic

        self.cluster = config['cluster']
        self._verify_cluster_id()
        topic = config['topic']
        num_partitions = config['num_partitions']
        replication_factor = config['replication_factor']
        topic_configs = config.get('configs', {})

        self.log.debug(
            "Creating topic '%s' on cluster '%s' with %d partitions, RF=%d",
            topic,
            self.cluster,
            num_partitions,
            replication_factor,
        )

        success = self.kafka_client.create_topic(
            topic=topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            configs=topic_configs,
        )

        if not success:
            raise Exception(f"Failed to create topic '{topic}' on cluster '{self.cluster}'")

    def _action_update_topic_config(self):
        """Update Kafka topic configuration (RFC Action #3).

        Config format:
            update_topic_config:
                cluster: prod-kafka-1
                topic: orders
                num_partitions: 12  # Optional: increase partition count
                configs:  # Optional: configs to update
                    retention.ms: "1209600000"
                delete_configs:  # Optional: configs to reset to defaults
                    - retention.bytes
        """
        config = self.config.update_topic_config

        self.cluster = config['cluster']
        self._verify_cluster_id()
        topic = config['topic']
        num_partitions = config.get('num_partitions')
        topic_configs = config.get('configs', {})
        delete_configs = config.get('delete_configs', [])

        self.log.debug("Updating configuration for topic '%s' on cluster '%s'", topic, self.cluster)

        if num_partitions:
            self.log.debug("Increasing partition count to %d (cannot decrease)", num_partitions)
            # TODO: Implement partition count increase using AdminClient.create_partitions()

        if topic_configs:
            success = self.kafka_client.update_topic_config(topic=topic, configs=topic_configs)
            if not success:
                raise Exception(f"Failed to update configs for topic '{topic}'")

        if delete_configs:
            success = self.kafka_client.delete_topic_config(topic=topic, config_keys=delete_configs)
            if not success:
                raise Exception(f"Failed to delete configs for topic '{topic}'")

    def _action_delete_topic(self):
        """Delete a Kafka topic (RFC Action #4).

        Config format:
            delete_topic:
                cluster: prod-kafka-1
                topic: old-orders
        """
        config = self.config.delete_topic

        self.cluster = config['cluster']
        self._verify_cluster_id()

        topic = config['topic']

        self.log.warning("DELETING topic '%s' on cluster '%s' - THIS IS IRREVERSIBLE", topic, self.cluster)

        success = self.kafka_client.delete_topic(topic=topic)

        if not success:
            raise Exception(f"Failed to delete topic '{topic}' on cluster '{self.cluster}'")

    def _action_delete_consumer_group(self):
        """Delete a Kafka consumer group (RFC Action #5).

        Config format:
            delete_consumer_group:
                cluster: prod-kafka-1
                consumer_group: old-service-v1
        """
        config = self.config.delete_consumer_group

        self.cluster = config['cluster']
        self._verify_cluster_id()

        consumer_group = config['consumer_group']

        self.log.warning("Deleting consumer group '%s' on cluster '%s'", consumer_group, self.cluster)

        success = self.kafka_client.delete_consumer_group(consumer_group=consumer_group)

        if not success:
            raise Exception(f"Failed to delete consumer group '{consumer_group}' on cluster '{self.cluster}'")

    def _action_update_consumer_group_offsets(self):
        """Update consumer group offsets (RFC Action #6).

        Config format:
            update_consumer_group_offsets:
                cluster: prod-kafka-1
                consumer_group: order-processor
                offsets:
                    - topic: orders
                      partition: 0
                      offset: 1000
                    - topic: orders
                      partition: 1
                      offset: 1500
        """
        config = self.config.update_consumer_group_offsets

        self.cluster = config['cluster']
        self._verify_cluster_id()
        consumer_group = config['consumer_group']
        offsets = config['offsets']

        self.log.warning(
            "Updating offsets for consumer group '%s' on cluster '%s' - may cause duplicate processing or data loss",
            consumer_group,
            self.cluster,
        )

        success = self.kafka_client.update_consumer_group_offsets(consumer_group=consumer_group, offsets=offsets)

        if not success:
            raise Exception(
                f"Failed to update offsets for consumer group '{consumer_group}' on cluster '{self.cluster}'"
            )

    def _action_produce_message(self):
        """Produce a message to a Kafka topic (RFC Action #7).

        All values (key, value, headers) must be base64-encoded strings.
        This ensures they can be safely transmitted via YAML configuration
        and supports binary data.

        Config format:
            produce_message:
                cluster: prod-kafka-1
                topic: test-topic
                key: "MTIzNDU="  # base64-encoded
                value: "eyJvcmRlcl9pZCI6ICIxMjM0NSIsICJzdGF0dXMiOiAicGVuZGluZyJ9"  # base64-encoded JSON
                partition: -1  # -1 for automatic partitioning
                headers:
                    source: "ZGF0YWRvZy1hZ2VudA=="  # base64-encoded
        """
        config = self.config.produce_message

        self.cluster = config['cluster']
        self._verify_cluster_id()
        topic = config['topic']
        value_b64 = config['value']
        key_b64 = config.get('key')
        partition = config.get('partition', -1)
        headers_b64 = config.get('headers', {})

        self.log.debug("Producing message to topic '%s' on cluster '%s'", topic, self.cluster)

        try:
            value_bytes = base64.b64decode(value_b64)
        except Exception as e:
            raise Exception(f"Failed to decode base64 value: {e}")

        key_bytes = None
        if key_b64:
            try:
                key_bytes = base64.b64decode(key_b64)
            except Exception as e:
                raise Exception(f"Failed to decode base64 key: {e}")

        headers_decoded = {}
        for header_key, header_value_b64 in headers_b64.items():
            try:
                headers_decoded[header_key] = base64.b64decode(header_value_b64)
            except Exception as e:
                raise Exception(f"Failed to decode base64 header '{header_key}': {e}")

        result = self.kafka_client.produce_message(
            topic=topic,
            value=value_bytes,
            key=key_bytes,
            partition=partition,
            headers=headers_decoded,
        )

        if not result['delivered']:
            raise Exception(f"Message delivery failed: {result['error']}")

        return {'topic': topic, 'partition': result['partition'], 'offset': result['offset']}
