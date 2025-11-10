# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from time import time

from datadog_checks.base import AgentCheck

from .kafka_client import KafkaActionsClient
from .message_filter import MessageFilter


class KafkaActionsCheck(AgentCheck):
    """
    Kafka Actions Check - Performs one-time actions on Kafka clusters.

    This check is designed to run once per execution and perform a specific action
    defined in the configuration.
    """

    __NAMESPACE__ = 'kafka_actions'

    def __init__(self, name, init_config, instances):
        super(KafkaActionsCheck, self).__init__(name, init_config, instances)

        # Get action from instance config
        self.action = self.instance.get('action')

        if not self.action:
            raise ValueError("No action specified in configuration. Please set 'action' parameter.")

        # Initialize Kafka client
        self.kafka_client = KafkaActionsClient(self.instance, self.log)

        # Registry of available actions
        self.action_handlers = {
            'retrieve_messages': self._action_retrieve_messages,
            'produce_message': self._action_produce_message,
            'manage_topic': self._action_manage_topic,
            'rebalance_partitions': self._action_rebalance_partitions,
        }

        if self.action not in self.action_handlers:
            raise ValueError(
                f"Unknown action '{self.action}'. Available actions: {', '.join(self.action_handlers.keys())}"
            )

    def check(self, _):
        """Execute the configured action once."""
        self.log.info("Executing Kafka action: %s", self.action)

        try:
            # Execute the action handler
            handler = self.action_handlers[self.action]
            result = handler()

            # Report success metric
            self.gauge(f'action.{self.action}.success', 1, tags=self._get_tags())

            self.log.info("Kafka action '%s' completed successfully", self.action)
            return result

        except Exception as e:
            self.log.exception("Kafka action '%s' failed: %s", self.action, e)
            self.gauge(f'action.{self.action}.failure', 1, tags=self._get_tags())
            raise
        finally:
            # Always close Kafka clients
            self.kafka_client.close()

    def _get_tags(self):
        """Get common tags for metrics."""
        tags = []
        if 'tags' in self.instance:
            tags.extend(self.instance['tags'])
        tags.append(f'action:{self.action}')
        return tags

    # =========================================================================
    # Action Handlers
    # =========================================================================

    def _action_retrieve_messages(self):
        """Retrieve and filter messages from Kafka topics, emit as events."""
        config = self.instance.get('retrieve_messages', {})

        topic = config.get('topic')
        if not topic:
            raise ValueError("retrieve_messages action requires 'topic' parameter")

        partition = config.get('partition', -1)
        start_offset = config.get('start_offset', -2)
        max_scan = config.get('max_messages_scan', 1000)
        max_send = config.get('max_messages_send', 100)
        timeout_ms = config.get('timeout_ms', 30000)
        filters_config = config.get('filters', [])

        self.log.info(
            "Retrieving messages from topic '%s' (partition: %s, max_scan: %d, max_send: %d)",
            topic,
            partition,
            max_scan,
            max_send,
        )

        # Create message filter
        message_filter = MessageFilter(filters_config, self.log)

        # Consume messages
        messages = self.kafka_client.consume_messages(
            topic=topic,
            partition=partition,
            start_offset=start_offset,
            max_messages=max_scan,
            timeout_ms=timeout_ms,
        )

        # Filter and emit messages as events
        sent_count = 0
        scanned_count = 0

        for msg in messages:
            scanned_count += 1

            if not message_filter.matches(msg):
                continue

            if sent_count >= max_send:
                self.log.debug("Reached max_messages_send limit (%d)", max_send)
                break

            # Emit message as event
            self._emit_message_event(msg, topic)
            sent_count += 1

        # Emit summary metrics
        self.gauge('messages.scanned', scanned_count, tags=self._get_tags() + [f'topic:{topic}'])
        self.gauge('messages.sent', sent_count, tags=self._get_tags() + [f'topic:{topic}'])

        self.log.info("Scanned %d messages, sent %d as events", scanned_count, sent_count)

        return {'scanned': scanned_count, 'sent': sent_count}

    def _emit_message_event(self, msg, topic):
        """Emit a Kafka message as a Datadog event.

        Args:
            msg: Kafka message object
            topic: Topic name
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
                'timestamp': int(time()),
                'event_type': 'kafka_message',
                'msg_title': event_title,
                'msg_text': event_text,
                'tags': event_tags,
                'source_type_name': 'kafka',
                'aggregation_key': f'kafka_{topic}_{msg.partition()}_{msg.offset()}',
            }
        )

    def _action_produce_message(self):
        """Produce a message to a Kafka topic."""
        config = self.instance.get('produce_message', {})

        topic = config.get('topic')
        value = config.get('value')

        if not topic or not value:
            raise ValueError("produce_message action requires 'topic' and 'value' parameters")

        key = config.get('key')
        partition = config.get('partition', -1)
        headers = config.get('headers', {})

        self.log.info("Producing message to topic '%s'", topic)

        # Produce message
        result = self.kafka_client.produce_message(
            topic=topic,
            value=value,
            key=key,
            partition=partition,
            headers=headers,
        )

        if result['delivered']:
            self.log.info(
                "Message delivered to %s [%d] at offset %d",
                topic,
                result['partition'],
                result['offset'],
            )
            self.gauge('message.produced', 1, tags=self._get_tags() + [f'topic:{topic}'])
        else:
            self.log.error("Message delivery failed: %s", result['error'])
            raise Exception(f"Message delivery failed: {result['error']}")

        return result

    def _action_manage_topic(self):
        """Create, update, or delete Kafka topics."""
        config = self.instance.get('manage_topic', {})

        operation = config.get('operation')
        topic = config.get('topic')

        if not operation or not topic:
            raise ValueError("manage_topic action requires 'operation' and 'topic' parameters")

        if operation == 'create':
            num_partitions = config.get('num_partitions', 1)
            replication_factor = config.get('replication_factor', 1)
            configs = config.get('configs', {})

            self.log.info("Creating topic '%s' with %d partitions", topic, num_partitions)

            success = self.kafka_client.create_topic(
                topic=topic,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                configs=configs,
            )

            if success:
                self.gauge('topic.created', 1, tags=self._get_tags() + [f'topic:{topic}'])

            return {'operation': 'create', 'topic': topic, 'success': success}

        elif operation == 'update':
            configs = config.get('configs', {})

            if not configs:
                raise ValueError("update operation requires 'configs' parameter")

            self.log.info("Updating configuration for topic '%s'", topic)

            success = self.kafka_client.update_topic_config(
                topic=topic,
                configs=configs,
            )

            if success:
                self.gauge('topic.updated', 1, tags=self._get_tags() + [f'topic:{topic}'])

            return {'operation': 'update', 'topic': topic, 'success': success}

        elif operation == 'delete':
            self.log.warning("Deleting topic '%s'", topic)

            success = self.kafka_client.delete_topic(topic=topic)

            if success:
                self.gauge('topic.deleted', 1, tags=self._get_tags() + [f'topic:{topic}'])

            return {'operation': 'delete', 'topic': topic, 'success': success}

        else:
            raise ValueError(f"Unknown operation '{operation}'. Must be 'create', 'update', or 'delete'")

    def _action_rebalance_partitions(self):
        """Trigger partition rebalancing across brokers."""
        config = self.instance.get('rebalance_partitions', {})

        topics = config.get('topics', [])
        brokers = config.get('brokers', [])
        strategy = config.get('strategy', 'uniform')

        self.log.info("Partition rebalancing requested for topics: %s", topics or 'all')

        # Note: Partition rebalancing is a complex operation that typically requires
        # external tools like kafka-reassign-partitions or cruise-control.
        # This is a placeholder implementation that would need integration with
        # those tools or implement the rebalancing logic directly.

        self.log.warning(
            "Partition rebalancing is not yet fully implemented. "
            "Consider using kafka-reassign-partitions tool or Cruise Control for production use."
        )

        # Emit metric
        self.gauge('rebalance.initiated', 1, tags=self._get_tags() + [f'strategy:{strategy}'])

        return {
            'topics': topics,
            'brokers': brokers,
            'strategy': strategy,
            'status': 'not_implemented',
            'message': 'Use kafka-reassign-partitions or Cruise Control for actual rebalancing',
        }
