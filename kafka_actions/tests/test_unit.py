# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import json
from unittest.mock import patch

import pytest

from datadog_checks.kafka_actions import KafkaActionsCheck

pytestmark = [pytest.mark.unit]


class MockKafkaMessage:
    """Mock confluent_kafka.Message for testing."""

    def __init__(self, key, value, topic='test-topic', partition=0, offset=100):
        self._key = key
        self._value = value
        self._topic = topic
        self._partition = partition
        self._offset = offset

    def key(self):
        return self._key

    def value(self):
        return self._value

    def topic(self):
        return self._topic

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset

    def timestamp(self):
        return (1, 1732128000000)

    def headers(self):
        return [('source', b'test')]

    def error(self):
        return None


class TestReadMessagesAction:
    """Test read_messages action with filtering."""

    def test_read_messages_with_filter(self, aggregator, dd_run_check):
        """Test reading messages with jq filter applied."""
        messages = [
            MockKafkaMessage(
                key=b'key-1',
                value=b'\x00\x00\x00\x00\x01' + json.dumps({"id": 1, "status": "active", "value": 100}).encode(),
                offset=100,
            ),
            MockKafkaMessage(
                key=b'key-2',
                value=b'\x00\x00\x00\x00\x01' + json.dumps({"id": 2, "status": "inactive", "value": 200}).encode(),
                offset=101,
            ),
            MockKafkaMessage(
                key=b'key-3',
                value=b'\x00\x00\x00\x00\x01' + json.dumps({"id": 3, "status": "active", "value": 300}).encode(),
                offset=102,
            ),
        ]

        instance = {
            'remote_config_id': 'test-read-messages-001',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {
                'cluster': 'test-cluster',
                'topic': 'test-topic',
                'partition': -1,
                'start_offset': -1,
                'n_messages_retrieved': 10,
                'max_scanned_messages': 100,
                'key_format': 'string',
                'key_uses_schema_registry': False,
                'value_format': 'json',
                'value_uses_schema_registry': True,
                'filter': '.value.status == "active"',
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'consume_messages', return_value=messages) as mock_consume,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_consume.assert_called_once()
            call_kwargs = mock_consume.call_args[1]
            assert call_kwargs['topic'] == 'test-topic'
            assert call_kwargs['partition'] == -1
            assert call_kwargs['start_offset'] == -1
            assert call_kwargs['max_messages'] == 100

        all_events = aggregator.get_event_platform_events("data-streams-message")
        # Filter for message events only (those with 'topic' field)
        message_events = [e for e in all_events if 'topic' in e]
        assert len(message_events) == 2, f"Expected 2 message events (filtered), got {len(message_events)}"

        event1 = message_events[0]
        assert event1['topic'] == 'test-topic'
        assert event1['offset'] == 100
        assert event1['value']['id'] == 1
        assert event1['value']['status'] == 'active'
        assert event1['remote_config_id'] == 'test-read-messages-001'

        event2 = message_events[1]
        assert event2['offset'] == 102
        assert event2['value']['id'] == 3


class TestCreateTopicAction:
    """Test create_topic action."""

    def test_create_topic(self, aggregator, dd_run_check):
        """Test creating a Kafka topic."""
        instance = {
            'remote_config_id': 'test-create-topic-001',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {
                'cluster': 'test-cluster',
                'topic': 'new-topic',
                'num_partitions': 6,
                'replication_factor': 3,
                'configs': {
                    'retention.ms': '604800000',
                    'compression.type': 'snappy',
                },
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'create_topic', return_value=True) as mock_create,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs['topic'] == 'new-topic'
            assert call_kwargs['num_partitions'] == 6
            assert call_kwargs['replication_factor'] == 3
            assert call_kwargs['configs']['retention.ms'] == '604800000'
            assert call_kwargs['configs']['compression.type'] == 'snappy'

        aggregator.assert_service_check('kafka_actions.can_connect', count=0)


class TestUpdateTopicConfigAction:
    """Test update_topic_config action."""

    def test_update_topic_config(self, aggregator, dd_run_check):
        """Test updating topic configuration."""
        instance = {
            'remote_config_id': 'test-update-topic-config-001',
            'kafka_connect_str': 'localhost:9092',
            'update_topic_config': {
                'cluster': 'test-cluster',
                'topic': 'existing-topic',
                'configs': {
                    'retention.ms': '1209600000',
                    'max.message.bytes': '2097152',
                },
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'update_topic_config', return_value=True) as mock_update,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_update.assert_called_once()
            call_kwargs = mock_update.call_args[1]
            assert call_kwargs['topic'] == 'existing-topic'
            assert call_kwargs['configs']['retention.ms'] == '1209600000'
            assert call_kwargs['configs']['max.message.bytes'] == '2097152'


class TestDeleteTopicAction:
    """Test delete_topic action."""

    def test_delete_topic(self, aggregator, dd_run_check):
        """Test deleting a Kafka topic."""
        instance = {
            'remote_config_id': 'test-delete-topic-001',
            'kafka_connect_str': 'localhost:9092',
            'delete_topic': {
                'cluster': 'test-cluster',
                'topic': 'old-topic',
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'delete_topic', return_value=True) as mock_delete,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_delete.assert_called_once()
            call_kwargs = mock_delete.call_args[1]
            assert call_kwargs['topic'] == 'old-topic'


class TestDeleteConsumerGroupAction:
    """Test delete_consumer_group action."""

    def test_delete_consumer_group(self, aggregator, dd_run_check):
        """Test deleting a consumer group."""
        instance = {
            'remote_config_id': 'test-delete-consumer-group-001',
            'kafka_connect_str': 'localhost:9092',
            'delete_consumer_group': {
                'cluster': 'test-cluster',
                'consumer_group': 'old-consumer-group',
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'delete_consumer_group', return_value=True) as mock_delete_cg,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_delete_cg.assert_called_once()
            call_kwargs = mock_delete_cg.call_args[1]
            assert call_kwargs['consumer_group'] == 'old-consumer-group'


class TestUpdateConsumerGroupOffsetsAction:
    """Test update_consumer_group_offsets action."""

    def test_update_consumer_group_offsets(self, aggregator, dd_run_check):
        """Test updating consumer group offsets."""
        instance = {
            'remote_config_id': 'test-update-offsets-001',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {
                'cluster': 'test-cluster',
                'consumer_group': 'my-consumer-group',
                'offsets': [
                    {'topic': 'orders', 'partition': 0, 'offset': 1000},
                    {'topic': 'orders', 'partition': 1, 'offset': 1500},
                    {'topic': 'orders', 'partition': 2, 'offset': 2000},
                ],
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'update_consumer_group_offsets', return_value=True) as mock_update_offsets,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_update_offsets.assert_called_once()
            call_kwargs = mock_update_offsets.call_args[1]
            assert call_kwargs['consumer_group'] == 'my-consumer-group'
            assert len(call_kwargs['offsets']) == 3
            assert call_kwargs['offsets'][0] == {'topic': 'orders', 'partition': 0, 'offset': 1000}


class TestProduceMessageAction:
    """Test produce_message action."""

    def test_produce_message(self, aggregator, dd_run_check):
        """Test producing a message to Kafka."""
        key_value = b'test-key-123'
        message_value = b'{"order_id": "12345", "status": "pending"}'
        header_source = b'datadog-agent'
        header_version = b'1.0'

        instance = {
            'remote_config_id': 'test-produce-message-001',
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {
                'cluster': 'test-cluster',
                'topic': 'test-topic',
                'key': base64.b64encode(key_value).decode('utf-8'),
                'value': base64.b64encode(message_value).decode('utf-8'),
                'partition': -1,
                'headers': {
                    'source': base64.b64encode(header_source).decode('utf-8'),
                    'version': base64.b64encode(header_version).decode('utf-8'),
                },
            },
        }

        def mock_produce(*args, **kwargs):
            return {'delivered': True, 'partition': 0, 'offset': 12345}

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'produce_message', side_effect=mock_produce) as mock_prod,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_prod.assert_called_once()
            call_kwargs = mock_prod.call_args[1]
            assert call_kwargs['topic'] == 'test-topic'
            assert call_kwargs['key'] == key_value
            assert call_kwargs['value'] == message_value
            assert call_kwargs['headers']['source'] == header_source
            assert call_kwargs['headers']['version'] == header_version
            assert call_kwargs['partition'] == -1


class TestReadMessagesAdvancedFiltering:
    """Test read_messages with more complex filtering scenarios."""

    def test_read_messages_nested_field_filter(self, aggregator, dd_run_check):
        """Test filtering on nested JSON fields."""
        messages = [
            MockKafkaMessage(
                key=b'order-1',
                value=b'\x00\x00\x00\x00\x01'
                + json.dumps({"order_id": 1, "user": {"country": "US", "tier": "gold"}}).encode(),
                offset=100,
            ),
            MockKafkaMessage(
                key=b'order-2',
                value=b'\x00\x00\x00\x00\x01'
                + json.dumps({"order_id": 2, "user": {"country": "FR", "tier": "silver"}}).encode(),
                offset=101,
            ),
            MockKafkaMessage(
                key=b'order-3',
                value=b'\x00\x00\x00\x00\x01'
                + json.dumps({"order_id": 3, "user": {"country": "US", "tier": "silver"}}).encode(),
                offset=102,
            ),
        ]

        instance = {
            'remote_config_id': 'test-nested-filter-001',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {
                'cluster': 'test-cluster',
                'topic': 'orders',
                'partition': 0,
                'start_offset': 0,
                'n_messages_retrieved': 10,
                'max_scanned_messages': 100,
                'key_format': 'string',
                'value_format': 'json',
                'value_uses_schema_registry': True,
                'filter': '.value.user.country == "US" and .value.user.tier == "gold"',
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'consume_messages', return_value=messages) as mock_consume,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
        ):
            dd_run_check(check)

            mock_consume.assert_called_once()

        all_events = aggregator.get_event_platform_events("data-streams-message")
        # Filter for message events only (those with 'topic' field)
        message_events = [e for e in all_events if 'topic' in e]
        assert len(message_events) == 1, f"Expected 1 message event (filtered), got {len(message_events)}"
        assert message_events[0]['value']['order_id'] == 1
        assert message_events[0]['value']['user']['country'] == 'US'
        assert message_events[0]['value']['user']['tier'] == 'gold'
        assert message_events[0]['remote_config_id'] == 'test-nested-filter-001'


class TestConsumeMessagesOffsetHandling:
    """Test consume_messages offset resolution in KafkaActionsClient."""

    def _make_client(self):
        import logging

        from datadog_checks.kafka_actions.kafka_client import KafkaActionsClient

        return KafkaActionsClient({'kafka_connect_str': 'localhost:9092'}, logging.getLogger('test'))

    def _mock_consumer(self, messages):
        """Create a mock consumer that returns messages from a list then None."""
        from unittest.mock import MagicMock

        consumer = MagicMock()
        message_iter = iter(messages)

        def poll_side_effect(timeout=1.0):
            try:
                return next(message_iter)
            except StopIteration:
                return None

        consumer.poll.side_effect = poll_side_effect
        return consumer

    def _mock_metadata(self, topic, partition_ids):
        from unittest.mock import MagicMock

        metadata = MagicMock()
        partitions = {pid: MagicMock() for pid in partition_ids}
        topic_metadata = MagicMock()
        topic_metadata.partitions = partitions
        metadata.topics = {topic: topic_metadata}
        return metadata

    def test_latest_offset_uses_list_offsets(self):
        """When start_offset=-1, list_offsets is called to resolve high watermarks."""
        from unittest.mock import MagicMock

        messages = [
            MockKafkaMessage(key=b'k1', value=b'v1', partition=0, offset=95),
            MockKafkaMessage(key=b'k2', value=b'v2', partition=0, offset=96),
        ]

        client = self._make_client()
        consumer = self._mock_consumer(messages)
        consumer.list_topics.return_value = self._mock_metadata('test-topic', [0])

        # Mock list_offsets via admin client
        mock_admin = MagicMock()
        mock_future = MagicMock()
        mock_result = MagicMock()
        mock_result.offset = 100
        mock_future.result.return_value = mock_result
        mock_tp = MagicMock()
        mock_tp.partition = 0
        mock_admin.list_offsets.return_value = {mock_tp: mock_future}

        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            result = list(
                client.consume_messages(
                    topic='test-topic', partition=-1, start_offset=-1, max_messages=10, timeout_ms=5000
                )
            )

        mock_admin.list_offsets.assert_called_once()
        assert len(result) == 2

        # Verify assigned partition has offset = max(0, 100 - 10) = 90
        assign_call = consumer.assign.call_args[0][0]
        assert len(assign_call) == 1
        assert assign_call[0].offset == 90
        assert assign_call[0].partition == 0

    def test_latest_offset_multiple_partitions(self):
        """list_offsets is called once with all partitions when start_offset=-1."""
        from unittest.mock import MagicMock

        messages = [
            MockKafkaMessage(key=b'k1', value=b'v1', partition=0, offset=45),
            MockKafkaMessage(key=b'k2', value=b'v2', partition=1, offset=195),
        ]

        client = self._make_client()
        consumer = self._mock_consumer(messages)
        consumer.list_topics.return_value = self._mock_metadata('test-topic', [0, 1])

        mock_admin = MagicMock()
        mock_tp0 = MagicMock()
        mock_tp0.partition = 0
        mock_result0 = MagicMock()
        mock_result0.offset = 50
        mock_future0 = MagicMock()
        mock_future0.result.return_value = mock_result0

        mock_tp1 = MagicMock()
        mock_tp1.partition = 1
        mock_result1 = MagicMock()
        mock_result1.offset = 200
        mock_future1 = MagicMock()
        mock_future1.result.return_value = mock_result1

        mock_admin.list_offsets.return_value = {mock_tp0: mock_future0, mock_tp1: mock_future1}

        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            result = list(
                client.consume_messages(
                    topic='test-topic', partition=-1, start_offset=-1, max_messages=5, timeout_ms=5000
                )
            )

        mock_admin.list_offsets.assert_called_once()
        # Verify the request contained both partitions
        call_args = mock_admin.list_offsets.call_args[0][0]
        assert len(call_args) == 2

        assert len(result) == 2

        # Verify assigned offsets: partition 0 = max(0, 50-5)=45, partition 1 = max(0, 200-5)=195
        assign_call = consumer.assign.call_args[0][0]
        offsets_by_partition = {tp.partition: tp.offset for tp in assign_call}
        assert offsets_by_partition[0] == 45
        assert offsets_by_partition[1] == 195

    def test_latest_offset_clamps_to_zero(self):
        """When high watermark < max_messages, seek offset is clamped to 0."""
        from unittest.mock import MagicMock

        client = self._make_client()
        consumer = self._mock_consumer([])
        consumer.list_topics.return_value = self._mock_metadata('test-topic', [0])

        mock_admin = MagicMock()
        mock_tp = MagicMock()
        mock_tp.partition = 0
        mock_result = MagicMock()
        mock_result.offset = 3  # Less than max_messages
        mock_future = MagicMock()
        mock_future.result.return_value = mock_result
        mock_admin.list_offsets.return_value = {mock_tp: mock_future}

        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            list(
                client.consume_messages(
                    topic='test-topic', partition=-1, start_offset=-1, max_messages=100, timeout_ms=1000
                )
            )

        assign_call = consumer.assign.call_args[0][0]
        assert assign_call[0].offset == 0

    def test_earliest_offset_does_not_call_list_offsets(self):
        """When start_offset=-2 (earliest), list_offsets should not be called."""
        from unittest.mock import MagicMock

        client = self._make_client()
        consumer = self._mock_consumer([])
        consumer.list_topics.return_value = self._mock_metadata('test-topic', [0])

        mock_admin = MagicMock()

        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            list(
                client.consume_messages(
                    topic='test-topic', partition=-1, start_offset=-2, max_messages=10, timeout_ms=1000
                )
            )

        mock_admin.list_offsets.assert_not_called()

        assign_call = consumer.assign.call_args[0][0]
        assert assign_call[0].offset == -2


if __name__ == '__main__':
    pytest.main([__file__, '-vv'])
