# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import time

from datadog_checks.base import AgentCheck

from .kafka_client import KafkaActionsClient
from .message_deserializer import DeserializedMessage, MessageDeserializer
from .schema_registry_client import SchemaRegistryClient


class KafkaActionsCheck(AgentCheck):
    """
    Kafka Actions Check - Performs one-time actions on Kafka clusters.

    This check is designed to run once per execution and perform a specific action
    defined in the configuration.
    """

    __NAMESPACE__ = 'kafka_actions'

    def __init__(self, name, init_config, instances):
        super(KafkaActionsCheck, self).__init__(name, init_config, instances)

        # Get remote config ID from instance (required for tracking)
        self.remote_config_id = self.instance.get('remote_config_id')
        if not self.remote_config_id:
            raise ValueError(
                "remote_config_id is required. This integration must be configured via Remote Configuration."
            )

        # Initialize Kafka client
        self.kafka_client = KafkaActionsClient(self.instance, self.log)

        # Initialize Schema Registry client (if configured)
        self.schema_registry_client = None
        if self.instance.get('schema_registry_url'):
            self.schema_registry_client = SchemaRegistryClient(self.instance, self.log, self.http)

        # Initialize message deserializer
        self.deserializer = MessageDeserializer(self.log, self.schema_registry_client)

        # Registry of available actions (RFC-compliant)
        self.action_handlers = {
            'read_messages': self._action_read_messages,
            'create_topic': self._action_create_topic,
            'update_topic_config': self._action_update_topic_config,
            'delete_topic': self._action_delete_topic,
            'delete_consumer_group': self._action_delete_consumer_group,
            'update_consumer_group_offsets': self._action_update_consumer_group_offsets,
            'produce_message': self._action_produce_message,
        }

        # Auto-detect action from config structure (no 'action' parameter needed)
        self.action = self._detect_action()

        if not self.action:
            raise ValueError(
                f"No action detected in configuration. Please include one of: {', '.join(self.action_handlers.keys())}"
            )

        self.log.info(
            "Kafka Actions check initialized - Action: %s, Remote Config ID: %s", self.action, self.remote_config_id
        )

    def _detect_action(self) -> str | None:
        """Auto-detect which action to execute based on config structure.

        Returns:
            Action name, or None if no action detected
        """
        # Check which action-specific config is present
        for action_name in self.action_handlers.keys():
            if action_name in self.instance:
                return action_name

        return None

    def check(self, _):
        """Execute the configured action once."""
        self.log.info("Executing Kafka action: %s (Remote Config ID: %s)", self.action, self.remote_config_id)

        try:
            # Execute the action handler
            handler = self.action_handlers[self.action]
            result = handler()

            # Report success event
            self._emit_action_event(
                success=True, action=self.action, message=f"Kafka action '{self.action}' completed successfully"
            )

            self.log.info("Kafka action '%s' completed successfully", self.action)
            return result

        except Exception as e:
            error_msg = str(e)
            self.log.exception("Kafka action '%s' failed: %s", self.action, error_msg)

            # Report failure event
            self._emit_action_event(
                success=False, action=self.action, message=f"Kafka action '{self.action}' failed: {error_msg}"
            )
            raise
        finally:
            # Always close Kafka clients
            self.kafka_client.close()

    def _get_tags(self):
        """Get common tags for metrics and events."""
        tags = []

        # Add action tag
        tags.append(f'action:{self.action}')

        # Add remote config ID tag (always present, required)
        tags.append(f'remote_config_id:{self.remote_config_id}')

        # Add user-defined tags
        if 'tags' in self.instance:
            tags.extend(self.instance['tags'])

        return tags

    def _emit_action_event(self, success: bool, action: str, message: str, **kwargs):
        """Emit an event for action success or failure.

        Args:
            success: Whether the action succeeded
            action: Action name
            message: Event message
            **kwargs: Additional event fields
        """
        event_type = 'success' if success else 'error'
        alert_type = 'success' if success else 'error'

        # Build event text with details
        event_text = f"**Action:** {action}\n"
        event_text += f"**Remote Config ID:** {self.remote_config_id}\n"
        event_text += f"**Status:** {'Success' if success else 'Failure'}\n\n"
        event_text += f"{message}\n"

        # Add extra details if provided
        for key, value in kwargs.items():
            event_text += f"**{key.replace('_', ' ').title()}:** {value}\n"

        self.event(
            {
                'timestamp': int(time.time()),
                'event_type': f'kafka_action_{event_type}',
                'msg_title': f'Kafka Action {action.replace("_", " ").title()}: {event_type.title()}',
                'msg_text': event_text,
                'alert_type': alert_type,
                'source_type_name': 'kafka_actions',
                'aggregation_key': f'kafka_action_{action}_{self.remote_config_id}',
                'tags': self._get_tags(),
            }
        )

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
                n_messages: 10  # Max messages to fetch
                filter: ""  # jq expression (optional)
        """
        config = self.instance.get('read_messages', {})

        # Required parameters
        cluster = config.get('cluster')
        topic = config.get('topic')

        if not cluster:
            raise ValueError("read_messages action requires 'cluster' parameter")
        if not topic:
            raise ValueError("read_messages action requires 'topic' parameter")

        # Optional parameters (RFC-compliant)
        partition = config.get('partition', -1)
        start_offset = config.get('start_offset', -1)  # -1 for latest (RFC default)
        n_messages = config.get('n_messages', 10)  # RFC default: 10, max: 100
        timeout_ms = config.get('timeout_ms', 30000)
        filter_expression = config.get('filter', '')  # jq expression

        # Validate n_messages limit (RFC specifies max 100)
        if n_messages > 100:
            self.log.warning("n_messages=%d exceeds RFC limit of 100, capping at 100", n_messages)
            n_messages = 100

        # Deserialization configuration
        deser_config = {
            'value_format': config.get('value_format', 'json'),
            'value_schema': config.get('value_schema'),
            'value_uses_schema_registry': config.get('value_uses_schema_registry', False),
            'key_format': config.get('key_format', 'json'),
            'key_schema': config.get('key_schema'),
            'key_uses_schema_registry': config.get('key_uses_schema_registry', False),
        }

        self.log.info(
            "Reading messages from cluster '%s', topic '%s' (partition: %s, n_messages: %d, value_format: %s)",
            cluster,
            topic,
            partition,
            n_messages,
            deser_config['value_format'],
        )

        # Consume messages
        raw_messages = self.kafka_client.consume_messages(
            topic=topic,
            partition=partition,
            start_offset=start_offset,
            max_messages=n_messages,
            timeout_ms=timeout_ms,
        )

        # Process messages with deserialization and filtering
        sent_count = 0
        tags = [f'kafka_cluster_id:{cluster}', f'topic:{topic}']

        for raw_msg in raw_messages:
            # Wrap in DeserializedMessage for lazy deserialization
            deserialized_msg = DeserializedMessage(raw_msg, self.deserializer, deser_config)

            # Apply filter if provided (filtering happens AFTER deserialization)
            if filter_expression:
                if not self._evaluate_filter(filter_expression, deserialized_msg):
                    continue

            # Emit message as event
            self._emit_message_event_deserialized(deserialized_msg, cluster)
            sent_count += 1

        # Emit summary metrics
        self.gauge('messages.read', sent_count, tags=self._get_tags() + tags)

        self.log.info("Read %d messages from cluster '%s', topic '%s'", sent_count, cluster, topic)

        return {'cluster': cluster, 'topic': topic, 'messages_read': sent_count}

    def _evaluate_filter(self, filter_expression: str, deserialized_msg: DeserializedMessage) -> bool:
        """Evaluate jq-style filter expression on deserialized message.

        Args:
            filter_expression: jq expression (e.g., '.value.status == "failed"')
            deserialized_msg: DeserializedMessage with lazy deserialization

        Returns:
            True if message matches filter, False otherwise
        """
        try:
            # Parse and evaluate the jq-style filter
            # Convert message to dict for field access
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
        # Handle 'and' / 'or' operators
        if ' and ' in expression:
            parts = expression.split(' and ')
            return all(self._evaluate_jq_expression(part.strip(), context) for part in parts)
        if ' or ' in expression:
            parts = expression.split(' or ')
            return any(self._evaluate_jq_expression(part.strip(), context) for part in parts)

        # Parse comparison: .field.path <operator> value
        # Supported operators: ==, !=, >, <, >=, <=, contains
        operators = ['==', '!=', '>=', '<=', '>', '<', ' contains ']
        for op in operators:
            if op in expression:
                left, right = expression.split(op, 1)
                left = left.strip()
                right = right.strip()

                # Evaluate left side (field access)
                left_value = self._get_field_from_path(left, context)

                # Evaluate right side (literal value)
                right_value = self._parse_literal(right)

                # Apply operator
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

        # Remove leading '.' and split by '.'
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

        # String literals (with quotes)
        if (value_str.startswith('"') and value_str.endswith('"')) or (
            value_str.startswith("'") and value_str.endswith("'")
        ):
            return value_str[1:-1]

        # Numbers
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            pass

        # Booleans
        if value_str.lower() == 'true':
            return True
        if value_str.lower() == 'false':
            return False
        if value_str.lower() == 'null':
            return None

        # Default: return as string
        return value_str

    def _emit_message_event_deserialized(self, deserialized_msg: DeserializedMessage, cluster: str):
        """Emit a deserialized Kafka message as a Datadog event.

        Args:
            deserialized_msg: DeserializedMessage object
            cluster: Kafka cluster identifier
        """
        # Get message data (lazy deserialization happens here)
        msg_dict = deserialized_msg.to_dict()

        # Format key and value for display
        key_display = self._format_for_display(msg_dict.get('key'))
        value_display = self._format_for_display(msg_dict.get('value'))

        # Build event tags
        event_tags = self._get_tags() + [
            f'cluster:{cluster}',
            f'topic:{deserialized_msg.topic}',
            f'partition:{deserialized_msg.partition}',
            f'offset:{deserialized_msg.offset}',
        ]

        if key_display and len(str(key_display)) < 200:
            event_tags.append(f'key:{key_display}')

        event_title = (
            f'Kafka Message: {deserialized_msg.topic} [P{deserialized_msg.partition}@{deserialized_msg.offset}]'
        )

        event_text = f"""**Topic:** {deserialized_msg.topic}
**Partition:** {deserialized_msg.partition}
**Offset:** {deserialized_msg.offset}
**Timestamp:** {deserialized_msg.timestamp}
**Key:** {key_display or '<none>'}

**Value:**
```json
{value_display or '<none>'}
```
"""

        # Add headers if present
        if msg_dict.get('headers'):
            headers_str = ', '.join(f"{k}={v}" for k, v in msg_dict['headers'].items())
            event_text += f"\n**Headers:** {headers_str}\n"

        agg_key = f'kafka_{deserialized_msg.topic}_{deserialized_msg.partition}_{deserialized_msg.offset}'

        self.event(
            {
                'timestamp': int(time.time()),
                'event_type': 'kafka_message',
                'msg_title': event_title,
                'msg_text': event_text,
                'tags': event_tags,
                'source_type_name': 'kafka',
                'aggregation_key': agg_key,
            }
        )

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

    def _emit_message_event(self, msg, topic, cluster='unknown'):
        """Emit a Kafka message as a Datadog event.

        Args:
            msg: Kafka message object
            topic: Topic name
            cluster: Kafka cluster identifier
        """
        # Parse message value
        try:
            value_str = msg.value().decode('utf-8') if msg.value() else ''
            try:
                value_obj = json.loads(value_str)
                value_display = json.dumps(value_obj, indent=2)
            except json.JSONDecodeError:
                value_display = value_str
        except UnicodeDecodeError:
            value_display = f"<binary data, {len(msg.value())} bytes>"

        # Parse message key
        key_str = ''
        if msg.key():
            try:
                key_str = msg.key().decode('utf-8')
            except UnicodeDecodeError:
                key_str = f"<binary, {len(msg.key())} bytes>"

        # Get timestamp
        ts_type, ts_value = msg.timestamp()
        timestamp = ts_value if ts_value else int(time() * 1000)

        # Build event
        event_tags = self._get_tags() + [
            f'cluster:{cluster}',
            f'topic:{topic}',
            f'partition:{msg.partition()}',
            f'offset:{msg.offset()}',
        ]

        if key_str:
            event_tags.append(f'key:{key_str[:200]}')  # Limit key length in tags

        event_title = f'Kafka Message: {topic} [P{msg.partition()}@{msg.offset()}]'

        event_text = f"""**Topic:** {topic}
**Partition:** {msg.partition()}
**Offset:** {msg.offset()}
**Timestamp:** {timestamp}
**Key:** {key_str or '<none>'}

**Value:**
```
{value_display}
```
"""

        self.event(
            {
                'timestamp': int(time.time()),
                'event_type': 'kafka_message',
                'msg_title': event_title,
                'msg_text': event_text,
                'tags': event_tags,
                'source_type_name': 'kafka',
                'aggregation_key': f'kafka_{topic}_{msg.partition()}_{msg.offset()}',
            }
        )

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
        config = self.instance.get('create_topic', {})

        # Required parameters
        cluster = config.get('cluster')
        topic = config.get('topic')
        num_partitions = config.get('num_partitions')
        replication_factor = config.get('replication_factor')

        if not cluster:
            raise ValueError("create_topic action requires 'cluster' parameter")
        if not topic:
            raise ValueError("create_topic action requires 'topic' parameter")
        if not num_partitions:
            raise ValueError("create_topic action requires 'num_partitions' parameter")
        if not replication_factor:
            raise ValueError("create_topic action requires 'replication_factor' parameter")

        # Optional configurations
        topic_configs = config.get('configs', {})

        self.log.info(
            "Creating topic '%s' on cluster '%s' with %d partitions, RF=%d",
            topic,
            cluster,
            num_partitions,
            replication_factor,
        )

        success = self.kafka_client.create_topic(
            topic=topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            configs=topic_configs,
        )

        if success:
            tags = [f'kafka_cluster_id:{cluster}', f'topic:{topic}']
            self.gauge('topic.created', 1, tags=self._get_tags() + tags)
            self.log.info("Successfully created topic '%s' on cluster '%s'", topic, cluster)
        else:
            raise Exception(f"Failed to create topic '{topic}' on cluster '{cluster}'")

        return {'cluster': cluster, 'topic': topic, 'success': success}

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
        config = self.instance.get('update_topic_config', {})

        # Required parameters
        cluster = config.get('cluster')
        topic = config.get('topic')

        if not cluster:
            raise ValueError("update_topic_config action requires 'cluster' parameter")
        if not topic:
            raise ValueError("update_topic_config action requires 'topic' parameter")

        # Optional parameters
        num_partitions = config.get('num_partitions')
        topic_configs = config.get('configs', {})
        delete_configs = config.get('delete_configs', [])

        self.log.info("Updating configuration for topic '%s' on cluster '%s'", topic, cluster)

        # Update partition count if specified
        if num_partitions:
            self.log.info("Increasing partition count to %d (cannot decrease)", num_partitions)
            # TODO: Implement partition count increase using AdminClient.create_partitions()

        # Update topic configurations
        if topic_configs:
            success = self.kafka_client.update_topic_config(topic=topic, configs=topic_configs)
            if not success:
                raise Exception(f"Failed to update configs for topic '{topic}'")

        # Delete configurations (reset to defaults)
        if delete_configs:
            success = self.kafka_client.delete_topic_config(topic=topic, config_keys=delete_configs)
            if not success:
                raise Exception(f"Failed to delete configs for topic '{topic}'")

        tags = [f'kafka_cluster_id:{cluster}', f'topic:{topic}']
        self.gauge('topic.updated', 1, tags=self._get_tags() + tags)
        self.log.info("Successfully updated topic '%s' on cluster '%s'", topic, cluster)

        return {'cluster': cluster, 'topic': topic, 'success': True}

    def _action_delete_topic(self):
        """Delete a Kafka topic (RFC Action #4).

        Config format:
            delete_topic:
                cluster: prod-kafka-1
                topic: old-orders
        """
        config = self.instance.get('delete_topic', {})

        # Required parameters
        cluster = config.get('cluster')
        topic = config.get('topic')

        if not cluster:
            raise ValueError("delete_topic action requires 'cluster' parameter")
        if not topic:
            raise ValueError("delete_topic action requires 'topic' parameter")

        self.log.warning("DELETING topic '%s' on cluster '%s' - THIS IS IRREVERSIBLE", topic, cluster)

        success = self.kafka_client.delete_topic(topic=topic)

        if success:
            tags = [f'kafka_cluster_id:{cluster}', f'topic:{topic}']
            self.gauge('topic.deleted', 1, tags=self._get_tags() + tags)
            self.log.warning("Successfully deleted topic '%s' on cluster '%s'", topic, cluster)
        else:
            raise Exception(f"Failed to delete topic '{topic}' on cluster '{cluster}'")

        return {'cluster': cluster, 'topic': topic, 'success': success}

    def _action_delete_consumer_group(self):
        """Delete a Kafka consumer group (RFC Action #5).

        Config format:
            delete_consumer_group:
                cluster: prod-kafka-1
                consumer_group: old-service-v1
        """
        config = self.instance.get('delete_consumer_group', {})

        # Required parameters
        cluster = config.get('cluster')
        consumer_group = config.get('consumer_group')

        if not cluster:
            raise ValueError("delete_consumer_group action requires 'cluster' parameter")
        if not consumer_group:
            raise ValueError("delete_consumer_group action requires 'consumer_group' parameter")

        self.log.warning("Deleting consumer group '%s' on cluster '%s'", consumer_group, cluster)

        success = self.kafka_client.delete_consumer_group(consumer_group=consumer_group)

        if success:
            tags = [f'kafka_cluster_id:{cluster}', f'consumer_group:{consumer_group}']
            self.gauge('consumer_group.deleted', 1, tags=self._get_tags() + tags)
            self.log.info("Successfully deleted consumer group '%s' on cluster '%s'", consumer_group, cluster)
        else:
            raise Exception(f"Failed to delete consumer group '{consumer_group}' on cluster '{cluster}'")

        return {'cluster': cluster, 'consumer_group': consumer_group, 'success': success}

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
        config = self.instance.get('update_consumer_group_offsets', {})

        # Required parameters
        cluster = config.get('cluster')
        consumer_group = config.get('consumer_group')
        offsets = config.get('offsets', [])

        if not cluster:
            raise ValueError("update_consumer_group_offsets action requires 'cluster' parameter")
        if not consumer_group:
            raise ValueError("update_consumer_group_offsets action requires 'consumer_group' parameter")
        if not offsets:
            raise ValueError("update_consumer_group_offsets action requires 'offsets' list")

        self.log.warning(
            "Updating offsets for consumer group '%s' on cluster '%s' - may cause duplicate processing or data loss",
            consumer_group,
            cluster,
        )

        success = self.kafka_client.update_consumer_group_offsets(consumer_group=consumer_group, offsets=offsets)

        if success:
            tags = [f'kafka_cluster_id:{cluster}', f'consumer_group:{consumer_group}']
            self.gauge('consumer_group.offsets_updated', len(offsets), tags=self._get_tags() + tags)
            self.log.info(
                "Successfully updated %d offsets for consumer group '%s' on cluster '%s'",
                len(offsets),
                consumer_group,
                cluster,
            )
        else:
            raise Exception(f"Failed to update offsets for consumer group '{consumer_group}' on cluster '{cluster}'")

        return {
            'cluster': cluster,
            'consumer_group': consumer_group,
            'offsets_updated': len(offsets),
            'success': success,
        }

    def _action_produce_message(self):
        """Produce a message to a Kafka topic (RFC Action #7).

        Config format:
            produce_message:
                cluster: prod-kafka-1
                topic: test-topic
                key: "12345"
                value: '{"order_id": "12345", "status": "pending"}'
                partition: -1  # -1 for automatic partitioning
                headers:
                    source: datadog-agent
        """
        config = self.instance.get('produce_message', {})

        # Required parameters
        cluster = config.get('cluster')
        topic = config.get('topic')
        value = config.get('value')

        if not cluster:
            raise ValueError("produce_message action requires 'cluster' parameter")
        if not topic:
            raise ValueError("produce_message action requires 'topic' parameter")
        if not value:
            raise ValueError("produce_message action requires 'value' parameter")

        # Optional parameters
        key = config.get('key')
        partition = config.get('partition', -1)
        headers = config.get('headers', {})

        self.log.info("Producing message to topic '%s' on cluster '%s'", topic, cluster)

        # Produce message
        result = self.kafka_client.produce_message(
            topic=topic,
            value=value,
            key=key,
            partition=partition,
            headers=headers,
        )

        if result['delivered']:
            tags = [f'kafka_cluster_id:{cluster}', f'topic:{topic}', f'partition:{result["partition"]}']
            self.log.info(
                "Message delivered to %s [%d] at offset %d on cluster '%s'",
                topic,
                result['partition'],
                result['offset'],
                cluster,
            )
            self.gauge('message.produced', 1, tags=self._get_tags() + tags)
        else:
            self.log.error("Message delivery failed: %s", result['error'])
            raise Exception(f"Message delivery failed: {result['error']}")

        return {'cluster': cluster, 'topic': topic, 'partition': result['partition'], 'offset': result['offset']}
