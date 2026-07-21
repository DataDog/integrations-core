# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from confluent_kafka import KafkaError, KafkaException, TopicPartition
from confluent_kafka.admin import OffsetSpec

from datadog_checks.kafka_actions import KafkaActionsCheck
from datadog_checks.kafka_actions.kafka_client import KafkaActionsClient

pytestmark = [pytest.mark.unit]


def _futures(offsets):
    """Build a {topic-partition: future} map mimicking AdminClient.list_offsets results."""
    out = {}
    for p, off in offsets.items():
        fut = MagicMock()
        fut.result.return_value = MagicMock(offset=off)
        out[MagicMock(partition=p)] = fut
    return out


def _offset_future(offset):
    fut = MagicMock()
    fut.result.return_value = MagicMock(offset=offset)
    return fut


def _offset_future_with_topic_partitions(topic_partitions):
    """Build a future mimicking AdminClient.alter_consumer_group_offsets results."""
    future = MagicMock()
    future.result.return_value = MagicMock(topic_partitions=topic_partitions)
    return future


def _list_offsets_stub(offsets_by_partition):
    """A `list_offsets`-compatible side_effect resolving any requested TopicPartition by partition number."""

    def _stub(request, **kwargs):
        return {tp: _offset_future(offsets_by_partition[tp.partition]) for tp in request}

    return _stub


def _eof(partition):
    """A mock poll() result representing a _PARTITION_EOF event."""
    msg = MagicMock()
    msg.error.return_value = MagicMock(code=MagicMock(return_value=KafkaError._PARTITION_EOF))
    msg.partition.return_value = partition
    return msg


def _client():
    return KafkaActionsClient({'kafka_connect_str': 'localhost:9092'}, logging.getLogger('test'))


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
        assert event1['message_timestamp'] == 1732128000000
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
        """Test updating consumer group offsets with explicit values."""
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
            patch.object(check.kafka_client, 'check_consumer_group_inactive'),
        ):
            dd_run_check(check)

            mock_update_offsets.assert_called_once()
            call_kwargs = mock_update_offsets.call_args[1]
            assert call_kwargs['consumer_group'] == 'my-consumer-group'
            assert len(call_kwargs['offsets']) == 3
            assert call_kwargs['offsets'][0] == {'topic': 'orders', 'partition': 0, 'offset': 1000}

    def test_update_consumer_group_offsets_with_sentinels(self, aggregator, dd_run_check):
        """Test updating consumer group offsets with sentinel values -2 (earliest) and -1 (latest)."""
        instance = {
            'remote_config_id': 'test-update-offsets-002',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {
                'cluster': 'test-cluster',
                'consumer_group': 'my-consumer-group',
                'offsets': [
                    {'topic': 'orders', 'partition': 0, 'offset': -2},
                    {'topic': 'orders', 'partition': 1, 'offset': -1},
                ],
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'update_consumer_group_offsets', return_value=True) as mock_update_offsets,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
            patch.object(check.kafka_client, 'check_consumer_group_inactive'),
        ):
            dd_run_check(check)

            mock_update_offsets.assert_called_once()
            call_kwargs = mock_update_offsets.call_args[1]
            assert call_kwargs['offsets'][0] == {'topic': 'orders', 'partition': 0, 'offset': -2}
            assert call_kwargs['offsets'][1] == {'topic': 'orders', 'partition': 1, 'offset': -1}

    def test_update_consumer_group_offsets_with_timestamp(self, aggregator, dd_run_check):
        """Test updating consumer group offsets with a timestamp (all partitions)."""
        instance = {
            'remote_config_id': 'test-update-offsets-004',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {
                'cluster': 'test-cluster',
                'consumer_group': 'my-consumer-group',
                'offsets': [
                    {'topic': 'payments', 'timestamp': 1735689600000},
                ],
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'update_consumer_group_offsets', return_value=True) as mock_update_offsets,
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
            patch.object(check.kafka_client, 'check_consumer_group_inactive'),
        ):
            dd_run_check(check)

            mock_update_offsets.assert_called_once()
            call_kwargs = mock_update_offsets.call_args[1]
            assert call_kwargs['offsets'][0] == {'topic': 'payments', 'timestamp': 1735689600000}

    def test_update_consumer_group_offsets_blocks_on_active_group(self, aggregator, dd_run_check):
        """Test that the check aborts when the consumer group has active members."""
        instance = {
            'remote_config_id': 'test-update-offsets-003',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {
                'cluster': 'test-cluster',
                'consumer_group': 'my-consumer-group',
                'offsets': [{'topic': 'orders', 'partition': 0, 'offset': 0}],
            },
        }

        check = KafkaActionsCheck('kafka_actions', {}, [instance])
        with (
            patch.object(check.kafka_client, 'get_cluster_id', return_value='test-cluster'),
            patch.object(
                check.kafka_client,
                'check_consumer_group_inactive',
                side_effect=Exception("Consumer group 'my-consumer-group' has 2 active member(s)."),
            ),
        ):
            with pytest.raises(Exception, match="active member"):
                dd_run_check(check)


class TestCheckConsumerGroupInactive:
    """Test the check_consumer_group_inactive guard."""

    def test_raises_when_group_has_active_members(self):
        mock_admin = MagicMock()
        description = MagicMock(members=[MagicMock(), MagicMock()])
        future = MagicMock()
        future.result.return_value = description
        mock_admin.describe_consumer_groups.return_value = {'my-group': future}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            with pytest.raises(Exception, match="2 active member"):
                client.check_consumer_group_inactive('my-group')

        mock_admin.describe_consumer_groups.assert_called_once_with(['my-group'], request_timeout=10)

    def test_passes_when_group_has_no_members(self):
        mock_admin = MagicMock()
        description = MagicMock(members=[])
        future = MagicMock()
        future.result.return_value = description
        mock_admin.describe_consumer_groups.return_value = {'my-group': future}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            client.check_consumer_group_inactive('my-group')


class TestResolveSentinelOffset:
    """Test _resolve_sentinel_offset."""

    def test_resolves_earliest(self):
        mock_admin = MagicMock()
        mock_admin.list_offsets.side_effect = _list_offsets_stub({0: 42})

        client = _client()
        assert client._resolve_sentinel_offset(mock_admin, 't', 0, -2) == 42

    def test_resolves_latest(self):
        mock_admin = MagicMock()
        mock_admin.list_offsets.side_effect = _list_offsets_stub({0: 99})

        client = _client()
        assert client._resolve_sentinel_offset(mock_admin, 't', 0, -1) == 99

    def test_rejects_non_sentinel_offset_without_calling_admin(self):
        mock_admin = MagicMock()
        client = _client()
        with pytest.raises(ValueError, match="Sentinel offset"):
            client._resolve_sentinel_offset(mock_admin, 't', 0, 5)

        mock_admin.list_offsets.assert_not_called()

    def test_propagates_result_error(self):
        tp = TopicPartition('t', 0)
        future = MagicMock()
        future.result.side_effect = KafkaException(MagicMock())
        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = {tp: future}

        client = _client()
        with pytest.raises(KafkaException):
            client._resolve_sentinel_offset(mock_admin, 't', 0, -1)


class TestUpdateConsumerGroupOffsetsClient:
    """Test update_consumer_group_offsets client-internal offset resolution logic."""

    def test_resolves_sentinel_and_explicit_offsets(self):
        mock_admin = MagicMock()
        mock_admin.list_offsets.side_effect = _list_offsets_stub({0: 500})
        mock_admin.alter_consumer_group_offsets.return_value = {'g': _offset_future_with_topic_partitions([])}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            assert client.update_consumer_group_offsets(
                'g',
                [
                    {'topic': 't', 'partition': 0, 'offset': -2},
                    {'topic': 't', 'partition': 1, 'offset': 1000},
                ],
            )

        committed = mock_admin.alter_consumer_group_offsets.call_args[0][0][0].topic_partitions
        by_partition = {tp.partition: tp.offset for tp in committed}
        assert by_partition == {0: 500, 1: 1000}

    def test_resolves_timestamp_across_all_partitions(self):
        admin_metadata = MagicMock()
        admin_metadata.topics = {'t': MagicMock(partitions={0: MagicMock(), 1: MagicMock()})}

        mock_admin = MagicMock()
        mock_admin.list_topics.return_value = admin_metadata
        mock_admin.list_offsets.side_effect = _list_offsets_stub({0: 10, 1: 20})
        mock_admin.alter_consumer_group_offsets.return_value = {'g': _offset_future_with_topic_partitions([])}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            assert client.update_consumer_group_offsets('g', [{'topic': 't', 'timestamp': 1700000000000}])

        committed = mock_admin.alter_consumer_group_offsets.call_args[0][0][0].topic_partitions
        by_partition = {tp.partition: tp.offset for tp in committed}
        assert by_partition == {0: 10, 1: 20}

    def test_resolves_timestamp_falls_back_to_latest_when_no_message_after(self):
        admin_metadata = MagicMock()
        admin_metadata.topics = {'t': MagicMock(partitions={0: MagicMock(), 1: MagicMock()})}

        # Partition 0 has a message at/after the timestamp; partition 1 doesn't (-1) and
        # must fall back to a separate batched `latest` lookup.
        timestamp_offsets = {0: 10, 1: -1}
        latest_offsets = {1: 30}

        def list_offsets_side_effect(request, **kwargs):
            is_latest_batch = all(spec == OffsetSpec.latest() for spec in request.values())
            offsets = latest_offsets if is_latest_batch else timestamp_offsets
            return {tp: _offset_future(offsets[tp.partition]) for tp in request}

        mock_admin = MagicMock()
        mock_admin.list_topics.return_value = admin_metadata
        mock_admin.list_offsets.side_effect = list_offsets_side_effect
        mock_admin.alter_consumer_group_offsets.return_value = {'g': _offset_future_with_topic_partitions([])}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            assert client.update_consumer_group_offsets('g', [{'topic': 't', 'timestamp': 1700000000000}])

        committed = mock_admin.alter_consumer_group_offsets.call_args[0][0][0].topic_partitions
        by_partition = {tp.partition: tp.offset for tp in committed}
        assert by_partition == {0: 10, 1: 30}
        assert mock_admin.list_offsets.call_count == 2

    def test_rejects_both_offset_and_timestamp(self):
        client = _client()
        with patch.object(client, 'get_admin_client', return_value=MagicMock()):
            with pytest.raises(ValueError, match="cannot specify both"):
                client.update_consumer_group_offsets('g', [{'topic': 't', 'partition': 0, 'offset': 1, 'timestamp': 1}])

    def test_rejects_overlapping_targets(self):
        mock_admin = MagicMock()
        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            with pytest.raises(ValueError, match="Multiple offset specifications target the same partition"):
                client.update_consumer_group_offsets(
                    'g',
                    [
                        {'topic': 't', 'partition': 0, 'offset': 1},
                        {'topic': 't', 'partition': 0, 'offset': 2},
                    ],
                )

    def test_raises_on_per_partition_error(self):
        mock_admin = MagicMock()
        mock_admin.list_offsets.side_effect = _list_offsets_stub({0: 1})
        failed_tp = MagicMock(topic='t', partition=0, error='UNKNOWN_MEMBER_ID')
        mock_admin.alter_consumer_group_offsets.return_value = {'g': _offset_future_with_topic_partitions([failed_tp])}

        client = _client()
        with patch.object(client, 'get_admin_client', return_value=mock_admin):
            with pytest.raises(Exception, match="Per-partition errors"):
                client.update_consumer_group_offsets('g', [{'topic': 't', 'partition': 0, 'offset': 1}])


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


class TestConsumeMessagesLatestOffset:
    """Test that start_offset=-1 seeks back from the captured high watermark."""

    def test_latest_offset_seeks_back_from_high_watermark(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock(), 1: MagicMock()})}
        consumer.list_topics.return_value = metadata
        consumer.poll.side_effect = [_eof(0), _eof(1)]

        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = _futures({0: 100, 1: 200})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            list(client.consume_messages(topic='t', start_offset=-1, max_messages=10, timeout_ms=500))

        assigned = {tp.partition: tp.offset for tp in consumer.assign.call_args[0][0]}
        assert assigned[0] == 90  # max(0, 100 - 10)
        assert assigned[1] == 190  # max(0, 200 - 10)


class TestConsumeMessagesSnapshotBound:
    """Test that consumption never crosses the high watermark captured at the start."""

    def test_does_not_yield_messages_at_or_beyond_high_watermark(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock()})}
        consumer.list_topics.return_value = metadata
        # High watermark is 5; a message at offset 5 arrives after the snapshot and must be dropped.
        consumer.poll.side_effect = [
            MockKafkaMessage(key=b'k', value=b'v', partition=0, offset=0),
            MockKafkaMessage(key=b'k', value=b'v', partition=0, offset=1),
            MockKafkaMessage(key=b'k', value=b'v', partition=0, offset=5),
        ]

        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = _futures({0: 5})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            result = list(client.consume_messages(topic='t', start_offset=0, max_messages=1000, timeout_ms=500))

        assert [m.offset() for m in result] == [0, 1]


class TestConsumeMessagesStartTimestamp:
    """Test that start_timestamp resolves to per-partition offsets via offsets_for_times."""

    def test_start_timestamp_resolves_offsets(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock(), 1: MagicMock()})}
        consumer.list_topics.return_value = metadata
        consumer.offsets_for_times.return_value = [
            MagicMock(partition=0, offset=50),
            MagicMock(partition=1, offset=120),
        ]
        consumer.poll.side_effect = [_eof(0), _eof(1)]

        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = _futures({0: 100, 1: 200})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            list(client.consume_messages(topic='t', start_timestamp=1700000000000, max_messages=10, timeout_ms=500))

        consumer.offsets_for_times.assert_called_once()
        for tp in consumer.offsets_for_times.call_args[0][0]:
            assert tp.offset == 1700000000000
        assigned = {tp.partition: tp.offset for tp in consumer.assign.call_args[0][0]}
        assert assigned == {0: 50, 1: 120}

    def test_start_timestamp_skips_partitions_past_end(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock(), 1: MagicMock()})}
        consumer.list_topics.return_value = metadata
        # Partition 0 has no message at/after the timestamp (offset=-1); it must not be assigned.
        consumer.offsets_for_times.return_value = [
            MagicMock(partition=0, offset=-1),
            MagicMock(partition=1, offset=120),
        ]
        consumer.poll.side_effect = [_eof(1)]

        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = _futures({0: 100, 1: 200})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            list(client.consume_messages(topic='t', start_timestamp=1700000000000, max_messages=10, timeout_ms=500))

        assigned = consumer.assign.call_args[0][0]
        assert len(assigned) == 1
        assert assigned[0].partition == 1

    def test_start_timestamp_overrides_start_offset(self, dd_run_check, aggregator):
        """Test that start_timestamp is passed through from check config."""
        messages = [
            MockKafkaMessage(
                key=b'key1',
                value=json.dumps({"id": 1}).encode(),
                offset=100,
            ),
        ]

        instance = {
            'remote_config_id': 'test-timestamp-001',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {
                'cluster': 'test-cluster',
                'topic': 'test-topic',
                'start_offset': -1,
                'start_timestamp': 1700000000000,
                'n_messages_retrieved': 10,
                'max_scanned_messages': 100,
                'key_format': 'string',
                'value_format': 'json',
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
            assert call_kwargs['start_timestamp'] == 1700000000000


class TestConsumeMessagesEarlyReturn:
    """Test that consume_messages stops when all partitions are drained (EOF), not on None."""

    def test_eof_drains_and_stops(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock()})}
        consumer.list_topics.return_value = metadata
        # A None poll must NOT end consumption; only EOF (or the watermark) does.
        consumer.poll.side_effect = [
            MockKafkaMessage(key=b'k', value=b'v', partition=0, offset=0),
            None,
            _eof(0),
        ]

        mock_admin = MagicMock()
        mock_admin.list_offsets.return_value = _futures({0: 100})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            result = list(client.consume_messages(topic='t', start_offset=0, max_messages=1000, timeout_ms=500))

        assert len(result) == 1
        assert consumer.poll.call_count == 3

    def test_empty_range_returns_without_polling(self):
        consumer = MagicMock()
        metadata = MagicMock()
        metadata.topics = {'t': MagicMock(partitions={0: MagicMock()})}
        consumer.list_topics.return_value = metadata

        mock_admin = MagicMock()
        # start (10) is already at the high watermark (10): nothing to read.
        mock_admin.list_offsets.return_value = _futures({0: 10})

        client = _client()
        with (
            patch.object(client, 'get_consumer', return_value=consumer),
            patch.object(client, 'get_admin_client', return_value=mock_admin),
        ):
            result = list(client.consume_messages(topic='t', start_offset=10, max_messages=1000, timeout_ms=500))

        assert result == []
        consumer.assign.assert_not_called()
        consumer.poll.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-vv'])
