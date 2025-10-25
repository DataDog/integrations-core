# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for Kafka cluster metadata collection."""

import hashlib
import json
import time
from unittest import mock

import pytest
from confluent_kafka.admin import BrokerMetadata, PartitionMetadata, TopicMetadata

from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.cluster_metadata import ClusterMetadataCollector

pytestmark = [pytest.mark.unit]


@pytest.fixture
def cluster_config():
    """Base configuration for cluster monitoring tests."""
    return {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
    }


@pytest.fixture
def mock_kafka_client():
    """Mock Kafka client with cluster metadata."""
    client = mock.MagicMock()

    # Mock list_topics response
    metadata = mock.MagicMock()
    metadata.cluster_id = 'test-cluster-id'

    # Mock brokers
    broker1 = mock.MagicMock(spec=BrokerMetadata)
    broker1.id = 1
    broker1.host = 'broker1'
    broker1.port = 9092

    broker2 = mock.MagicMock(spec=BrokerMetadata)
    broker2.id = 2
    broker2.host = 'broker2'
    broker2.port = 9092

    metadata.brokers = {1: broker1, 2: broker2}

    # Mock topics
    partition1 = mock.MagicMock(spec=PartitionMetadata)
    partition1.id = 0
    partition1.leader = 1
    partition1.replicas = [1, 2]
    partition1.isrs = [1, 2]

    topic1 = mock.MagicMock(spec=TopicMetadata)
    topic1.partitions = {0: partition1}
    topic1.error = None

    metadata.topics = {'test-topic': topic1}

    client.kafka_client.list_topics.return_value = metadata

    return client


@pytest.fixture
def collector(cluster_config, mock_kafka_client):
    """Create a ClusterMetadataCollector instance for testing."""
    check = mock.MagicMock(spec=KafkaCheck)
    config = mock.MagicMock()
    config._custom_tags = ['env:test']
    config._request_timeout = 10
    config._monitor_unlisted_consumer_groups = False
    config._collect_broker_metadata = True
    config._collect_topic_metadata = True
    config._collect_consumer_group_metadata = True
    config._collect_schema_registry = False
    config._schema_registry_url = None

    log = mock.MagicMock()

    return ClusterMetadataCollector(check, mock_kafka_client, config, log)


def test_event_cache_initialization(collector):
    """Test that event cache keys are initialized correctly."""
    assert hasattr(collector, 'BROKER_CONFIG_CACHE_KEY')
    assert hasattr(collector, 'TOPIC_CONFIG_CACHE_KEY')
    assert hasattr(collector, 'SCHEMA_CACHE_KEY')
    assert collector.EVENT_CACHE_TTL == 600
    assert collector.BROKER_CONFIG_CACHE_KEY == 'kafka_broker_config_cache'
    assert collector.TOPIC_CONFIG_CACHE_KEY == 'kafka_topic_config_cache'
    assert collector.SCHEMA_CACHE_KEY == 'kafka_schema_cache'


def test_should_emit_cached_event_first_time(collector):
    """Test that event is emitted on first occurrence."""
    # Mock empty cache (first time)
    collector.check.read_persistent_cache = mock.MagicMock(return_value=None)
    collector.check.write_persistent_cache = mock.MagicMock()

    content = "test content"
    key = "test_key"
    cache_key = "test_cache_key"

    result = collector._should_emit_cached_event(cache_key, key, content)

    assert result is True
    # Verify cache was written
    assert collector.check.write_persistent_cache.called


def test_should_emit_cached_event_content_changed(collector):
    """Test that event is emitted when content changes."""
    key = "test_key"
    cache_key = "test_cache_key"
    old_content = "old content"
    new_content = "new content"
    old_hash = hashlib.sha256(old_content.encode('utf-8')).hexdigest()

    # Mock existing cache with old content
    old_cache = {key: {'hash': old_hash, 'last_emit': time.time()}}
    collector.check.read_persistent_cache = mock.MagicMock(return_value=json.dumps(old_cache))
    collector.check.write_persistent_cache = mock.MagicMock()

    # Content changed
    result = collector._should_emit_cached_event(cache_key, key, new_content)

    assert result is True
    # Verify cache was updated
    assert collector.check.write_persistent_cache.called


def test_should_emit_cached_event_within_ttl(collector):
    """Test that event is not emitted within TTL if content unchanged."""
    key = "test_key"
    cache_key = "test_cache_key"
    content = "test content"
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Mock existing cache with same content, recent timestamp
    existing_cache = {key: {'hash': content_hash, 'last_emit': time.time()}}
    collector.check.read_persistent_cache = mock.MagicMock(return_value=json.dumps(existing_cache))
    collector.check.write_persistent_cache = mock.MagicMock()

    # Same content, within TTL
    result = collector._should_emit_cached_event(cache_key, key, content)

    assert result is False
    # Cache should not be written
    assert not collector.check.write_persistent_cache.called


def test_should_emit_cached_event_after_ttl(collector):
    """Test that event is emitted after TTL expires."""
    key = "test_key"
    cache_key = "test_cache_key"
    content = "test content"
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Mock existing cache with same content but expired TTL
    expired_cache = {key: {'hash': content_hash, 'last_emit': time.time() - 601}}  # 601 seconds ago
    collector.check.read_persistent_cache = mock.MagicMock(return_value=json.dumps(expired_cache))
    collector.check.write_persistent_cache = mock.MagicMock()

    # Should emit after TTL
    result = collector._should_emit_cached_event(cache_key, key, content)

    assert result is True
    # Cache should be updated with new timestamp
    assert collector.check.write_persistent_cache.called


def test_get_tags_with_cluster_id(collector):
    """Test that tags include kafka_cluster_id."""
    tags = collector._get_tags('test-cluster-123')

    assert 'env:test' in tags
    assert 'kafka_cluster_id:test-cluster-123' in tags


def test_get_tags_without_cluster_id(collector):
    """Test that tags work without cluster_id."""
    tags = collector._get_tags()

    assert 'env:test' in tags
    assert not any('kafka_cluster_id' in tag for tag in tags)


def test_collect_broker_metadata(collector, mock_kafka_client):
    """Test broker metadata collection."""
    # Mock describe_configs
    config_resource = mock.MagicMock()
    config_result = mock.MagicMock()

    config_entry = mock.MagicMock()
    config_entry.name = 'advertised.listeners'
    config_entry.value = 'PLAINTEXT://localhost:9092'
    config_entry.is_default = False

    config_result.result.return_value = {config_entry.name: config_entry}
    mock_kafka_client.kafka_client.describe_configs.return_value = {config_resource: config_result}

    collector._collect_broker_metadata()

    # Verify broker count metric was called
    collector.check.gauge.assert_any_call('broker.count', 2, tags=mock.ANY)


def test_collect_topic_metadata(collector, mock_kafka_client):
    """Test topic metadata collection."""
    # Mock get_topic_partitions
    mock_kafka_client.get_topic_partitions.return_value = {'test-topic': [0]}

    # Mock consumer
    mock_consumer = mock.MagicMock()
    mock_consumer.get_watermark_offsets.return_value = (0, 100)
    mock_kafka_client._consumer = mock_consumer
    mock_kafka_client.open_consumer = mock.MagicMock()
    mock_kafka_client.close_consumer = mock.MagicMock()

    # Mock describe_configs
    mock_kafka_client.kafka_client.describe_configs.return_value = {}

    collector._collect_topic_metadata()

    # Verify topic count metric was called
    collector.check.gauge.assert_any_call('topic.count', 1, tags=mock.ANY)

    # Verify partition metrics were called
    assert any(call[0][0] == 'partition.beginning_offset' for call in collector.check.gauge.call_args_list)
    assert any(call[0][0] == 'partition.end_offset' for call in collector.check.gauge.call_args_list)


def test_collect_consumer_group_metadata(collector, mock_kafka_client):
    """Test consumer group metadata collection."""
    # Mock list_consumer_groups
    list_result = mock.MagicMock()
    list_result.errors = []

    group1 = mock.MagicMock()
    group1.group_id = 'test-group'
    list_result.valid = [group1]

    list_future = mock.MagicMock()
    list_future.result.return_value = list_result
    mock_kafka_client.kafka_client.list_consumer_groups.return_value = list_future

    # Mock describe_consumer_groups
    describe_result = mock.MagicMock()
    describe_result.state = mock.MagicMock()
    describe_result.state.name = 'STABLE'
    describe_result.members = []
    describe_result.coordinator = mock.MagicMock()
    describe_result.coordinator.id = 1

    describe_future = mock.MagicMock()
    describe_future.result.return_value = describe_result

    mock_kafka_client.kafka_client.describe_consumer_groups.return_value = {'test-group': describe_future}

    collector._collect_consumer_group_metadata()

    # Verify consumer group count metric was called
    collector.check.gauge.assert_any_call('consumer_group.count', 1, tags=mock.ANY)

    # Verify consumer group state metric was called
    assert any(
        call[0][0] == 'consumer_group.state' and 'state:STABLE' in call[1]['tags']
        for call in collector.check.gauge.call_args_list
    )


def test_collect_schema_registry_info(collector, mock_kafka_client):
    """Test schema registry information collection."""
    collector.config._collect_schema_registry = True
    collector.config._schema_registry_url = 'http://localhost:8081'

    # Mock subjects list
    subjects_response = mock.MagicMock()
    subjects_response.json.return_value = ['test-topic-value', 'test-topic-key']

    # Mock versions
    versions_response = mock.MagicMock()
    versions_response.json.return_value = [1, 2]

    # Mock latest schema
    latest_response = mock.MagicMock()
    latest_response.json.return_value = {
        'id': 1,
        'version': 2,
        'schema': '{"type": "record", "name": "Test"}',
        'schemaType': 'AVRO',
    }

    collector.check.http.get = mock.MagicMock(
        side_effect=[
            subjects_response,
            versions_response,
            latest_response,
            versions_response,
            latest_response,
        ]
    )

    collector._collect_schema_registry_info()

    # Verify schema count metric was called
    collector.check.gauge.assert_any_call('schema_registry.subjects', 2, tags=mock.ANY)

    # Verify HTTP requests were made
    assert collector.check.http.get.call_count >= 3


def test_config_enables_all_collection(cluster_config):
    """Test that enable_cluster_monitoring flag enables all collection."""
    from datadog_checks.kafka_consumer.config import KafkaConfig

    config = KafkaConfig({}, cluster_config, mock.MagicMock())

    assert config._collect_broker_metadata is True
    assert config._collect_topic_metadata is True
    assert config._collect_consumer_group_metadata is True


def test_config_schema_registry_auto_enabled(cluster_config):
    """Test that schema registry is auto-enabled when URL is provided."""
    from datadog_checks.kafka_consumer.config import KafkaConfig

    cluster_config['schema_registry_url'] = 'http://localhost:8081'
    config = KafkaConfig({}, cluster_config, mock.MagicMock())

    assert config._collect_schema_registry is True
    assert config._schema_registry_url == 'http://localhost:8081'


def test_config_schema_registry_not_enabled_without_url(cluster_config):
    """Test that schema registry is not enabled without URL."""
    from datadog_checks.kafka_consumer.config import KafkaConfig

    config = KafkaConfig({}, cluster_config, mock.MagicMock())

    assert config._collect_schema_registry is False
    assert config._schema_registry_url is None


def test_broker_config_event_caching(collector, mock_kafka_client):
    """Test that broker config events are cached and not re-emitted unnecessarily."""
    # Mock persistent cache (empty first, then populated)
    cache_data = {}

    def read_cache_side_effect(key):
        return json.dumps(cache_data) if cache_data else None

    def write_cache_side_effect(key, value):
        nonlocal cache_data
        cache_data = json.loads(value)

    collector.check.read_persistent_cache = mock.MagicMock(side_effect=read_cache_side_effect)
    collector.check.write_persistent_cache = mock.MagicMock(side_effect=write_cache_side_effect)

    # Mock describe_configs
    config_resource = mock.MagicMock()
    config_result = mock.MagicMock()

    config_entry = mock.MagicMock()
    config_entry.name = 'advertised.listeners'
    config_entry.value = 'PLAINTEXT://localhost:9092'
    config_entry.is_default = False

    config_result.result.return_value = {config_entry.name: config_entry}
    mock_kafka_client.kafka_client.describe_configs.return_value = {config_resource: config_result}

    # First collection - should emit event
    collector._collect_broker_metadata()
    first_event_count = len([call for call in collector.check.event.call_args_list if 'broker' in str(call)])

    # Second collection - should not emit event (within TTL, same content)
    collector._collect_broker_metadata()
    second_event_count = len([call for call in collector.check.event.call_args_list if 'broker' in str(call)])

    # Event count should be the same (no new events emitted)
    assert second_event_count == first_event_count


def test_topic_config_event_json_format(collector, mock_kafka_client):
    """Test that topic config events are in JSON format."""
    # Mock get_topic_partitions
    mock_kafka_client.get_topic_partitions.return_value = {'test-topic': [0]}

    # Mock consumer
    mock_consumer = mock.MagicMock()
    mock_consumer.get_watermark_offsets.return_value = (0, 100)
    mock_kafka_client._consumer = mock_consumer
    mock_kafka_client.open_consumer = mock.MagicMock()
    mock_kafka_client.close_consumer = mock.MagicMock()

    # Mock describe_configs with a custom config
    config_entry = mock.MagicMock()
    config_entry.name = 'retention.ms'
    config_entry.value = '86400000'
    config_entry.is_default = False

    future = mock.MagicMock()
    future.result.return_value = {config_entry.name: config_entry}

    mock_kafka_client.kafka_client.describe_configs.return_value = {mock.MagicMock(): future}

    collector._collect_topic_metadata()

    # Find topic config events
    topic_config_events = [call for call in collector.check.event.call_args_list if 'topic_config' in str(call)]

    if topic_config_events:
        # Verify event has JSON formatted msg_text
        event_call = topic_config_events[0]
        event_data = event_call[0][0] if event_call[0] else event_call[1]
        msg_text = event_data.get('msg_text', '')

        # Should be valid JSON
        try:
            parsed = json.loads(msg_text)
            assert isinstance(parsed, dict)
        except json.JSONDecodeError:
            pytest.fail("Topic config event msg_text is not valid JSON")
