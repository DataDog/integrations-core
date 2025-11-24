# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import json
from unittest.mock import patch

import pytest

from datadog_checks.kafka_actions import KafkaActionsCheck


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

        events = [e for e in aggregator.events if e.get('event_type') == 'kafka_message']
        assert len(events) == 2, f"Expected 2 message events (filtered), got {len(events)}"

        event1 = events[0]
        assert 'test-topic' in event1['msg_title']
        assert '"offset": 100' in event1['msg_text']
        assert '"id": 1' in event1['msg_text']
        assert '"status": "active"' in event1['msg_text']

        event2 = events[1]
        assert '"offset": 102' in event2['msg_text']
        assert '"id": 3' in event2['msg_text']


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

        events = [e for e in aggregator.events if e.get('event_type') == 'kafka_message']
        assert len(events) == 1, f"Expected 1 message event (filtered), got {len(events)}"
        assert '"order_id": 1' in events[0]['msg_text']
        assert '"country": "US"' in events[0]['msg_text']
        assert '"tier": "gold"' in events[0]['msg_text']


if __name__ == '__main__':
    pytest.main([__file__, '-vv'])
