# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for Kafka cluster metadata collection."""

import json
import time
from unittest import mock

import pytest
from confluent_kafka.admin import BrokerMetadata, PartitionMetadata, TopicMetadata

from datadog_checks.kafka_consumer.client import KafkaClient

pytestmark = [pytest.mark.unit]


def seed_mock_kafka_client(cluster_id='test-cluster-id'):
    """Set some common defaults for the mock Kafka client with cluster metadata."""
    client = mock.create_autospec(KafkaClient)

    # Mock list_topics response
    metadata = mock.MagicMock()
    metadata.cluster_id = cluster_id

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

    # Mock topics with partition metadata
    partition0 = mock.MagicMock(spec=PartitionMetadata)
    partition0.id = 0
    partition0.leader = 1
    partition0.replicas = [1, 2]
    partition0.isrs = [1, 2]

    partition1 = mock.MagicMock(spec=PartitionMetadata)
    partition1.id = 1
    partition1.leader = 2
    partition1.replicas = [1, 2]
    partition1.isrs = [1, 2]

    topic1 = mock.MagicMock(spec=TopicMetadata)
    topic1.partitions = {0: partition0, 1: partition1}
    topic1.error = None

    metadata.topics = {'test-topic': topic1}

    # Create mock AdminClient and set it as kafka_client
    mock_admin_client = mock.MagicMock()
    mock_admin_client.list_topics.return_value = metadata

    # Mock describe_configs to return realistic Kafka configs
    def mock_describe_configs(resources):
        result = {}
        for resource in resources:
            config_future = mock.MagicMock()

            # Determine if this is a broker or topic config based on resource type
            from confluent_kafka.admin import ResourceType

            if resource.restype == ResourceType.BROKER:
                # Mock realistic broker configurations
                configs = {
                    'log.retention.bytes': mock.MagicMock(name='log.retention.bytes', value='1073741824'),
                    'log.retention.ms': mock.MagicMock(name='log.retention.ms', value='604800000'),
                    'log.segment.bytes': mock.MagicMock(name='log.segment.bytes', value='1073741824'),
                    'num.partitions': mock.MagicMock(name='num.partitions', value='3'),
                    'num.network.threads': mock.MagicMock(name='num.network.threads', value='3'),
                    'num.io.threads': mock.MagicMock(name='num.io.threads', value='8'),
                    'default.replication.factor': mock.MagicMock(name='default.replication.factor', value='2'),
                    'min.insync.replicas': mock.MagicMock(name='min.insync.replicas', value='1'),
                    'compression.type': mock.MagicMock(name='compression.type', value='producer'),
                }
            else:  # TOPIC
                # Mock realistic topic configurations
                configs = {
                    'retention.ms': mock.MagicMock(name='retention.ms', value='604800000'),
                    'retention.bytes': mock.MagicMock(name='retention.bytes', value='-1'),
                    'max.message.bytes': mock.MagicMock(name='max.message.bytes', value='1048588'),
                    'compression.type': mock.MagicMock(name='compression.type', value='producer'),
                    'cleanup.policy': mock.MagicMock(name='cleanup.policy', value='delete'),
                }

            config_future.result.return_value = configs
            result[resource] = config_future
        return result

    mock_admin_client.describe_configs = mock_describe_configs

    cluster_info = mock.MagicMock()
    cluster_info.controller = None
    cluster_future = mock.MagicMock()
    cluster_future.result.return_value = cluster_info
    mock_admin_client.describe_cluster.return_value = cluster_future

    list_result = mock.MagicMock()
    list_result.errors = []
    group_obj = mock.MagicMock()
    group_obj.group_id = 'test-group'
    list_result.valid = [group_obj]
    list_future = mock.MagicMock()
    list_future.result.return_value = list_result
    mock_admin_client.list_consumer_groups.return_value = list_future

    describe_result = mock.MagicMock()

    # Mock state with name attribute
    state_mock = mock.MagicMock()
    state_mock.name = 'STABLE'
    describe_result.state = state_mock

    # Mock member
    member = mock.MagicMock()
    member.member_id = 'm1'
    member.client_id = 'c1'
    member.host = 'h1'

    # Mock assignment with topic_partitions
    assignment = mock.MagicMock()
    tp = mock.MagicMock()
    tp.topic = 'test-topic'
    tp.partition = 0
    assignment.topic_partitions = [tp]
    member.assignment = assignment

    describe_result.members = [member]

    # Mock coordinator with id attribute
    coordinator_mock = mock.MagicMock()
    coordinator_mock.id = 1
    describe_result.coordinator = coordinator_mock

    describe_future = mock.MagicMock()
    describe_future.result.return_value = describe_result
    mock_admin_client.describe_consumer_groups.return_value = {'test-group': describe_future}

    # Set kafka_client as an attribute (not a property mock)
    client.kafka_client = mock_admin_client
    client.get_topic_partitions.return_value = {'test-topic': [0, 1]}

    def mock_offsets_for_times(partitions, offset=-1):
        if offset == -1:
            return [(topic, partition, 100 if partition == 0 else 200) for topic, partition in partitions]
        else:
            return [(topic, partition, 10 if partition == 0 else 20) for topic, partition in partitions]

    client.consumer_offsets_for_times = mock_offsets_for_times
    client.consumer_get_cluster_id_and_list_topics.return_value = (cluster_id, [('test-topic', [0, 1])])
    client.list_consumer_group_offsets.return_value = []
    client.open_consumer.return_value = None
    client.close_consumer.return_value = None

    return client


def mock_schema_registry_methods(metadata_collector):
    """Mock Schema Registry methods on the metadata collector."""
    metadata_collector._get_schema_registry_subjects = mock.Mock(return_value=['test-topic-value'])
    metadata_collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])

    # Mock a realistic minimal Avro schema for a user event
    avro_schema = json.dumps(
        {
            "type": "record",
            "name": "User",
            "namespace": "com.example",
            "fields": [
                {"name": "id", "type": "long"},
                {"name": "username", "type": "string"},
                {"name": "email", "type": ["null", "string"], "default": None},
            ],
        }
    )

    metadata_collector._get_schema_registry_latest_version = mock.Mock(
        return_value={
            'id': 1,
            'version': 2,
            'schema': avro_schema,
            'schemaType': 'AVRO',
        }
    )


@pytest.fixture
def cluster_config():
    """Base configuration for cluster monitoring tests."""
    return {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
    }


def test_collect_cluster_metadata(check, dd_run_check, aggregator):
    """End-to-end collection: emit broker/topic/consumer/schema metrics and events.

    - Verifies exact metric values for brokers, topics, partitions, and consumer groups
    - Verifies broker and topic configuration events are emitted
    - Verifies schema registry event structure and content
    - Tests throughput calculation with persistent cache
    """
    # Create instance config with cluster monitoring enabled
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
        'monitor_unlisted_consumer_groups': True,
        'tags': ['test_tag:test_value'],
    }

    # Create the check
    kafka_consumer_check = check(instance)

    # Mock Kafka client
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    # Also replace the client in the metadata collector since it was initialized with the old client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client

    # Mock schema registry methods on metadata collector
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    # Mock persistent cache for throughput calculation and schema registry events
    # Using per-partition format: partition 0 was at 75, partition 1 was at 175
    # Total was 250, now will be 300 (100 + 200), so rate = (300-250)/10 = 5.0 msg/sec
    prev_snapshot = {
        'ts': time.time() - 10.0,
        'partitions': {
            'test-topic:0': 75,
            'test-topic:1': 175,
        }
    }

    def mocked_read_cache(key):
        if 'kafka_topic_hwm_sum_cache' in key:
            return json.dumps(prev_snapshot)
        # Return None for other caches to allow first-time event emission
        return None

    kafka_consumer_check.read_persistent_cache = mock.Mock(side_effect=mocked_read_cache)
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    # Run the full check
    dd_run_check(kafka_consumer_check)

    # Verify broker metrics with exact values
    aggregator.assert_metric(
        'kafka.broker.count',
        value=2,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'bootstrap_servers:localhost:9092'],
    )

    # Verify broker config metrics are emitted
    broker_tags = [
        'test_tag:test_value',
        'kafka_cluster_id:test-cluster-id',
        'broker_id:1',
        'broker_host:broker1',
        'broker_port:9092',
    ]
    aggregator.assert_metric('kafka.broker.config.log_retention_bytes', value=1073741824, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.log_retention_ms', value=604800000, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.log_segment_bytes', value=1073741824, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.num_partitions', value=3, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.num_network_threads', value=3, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.num_io_threads', value=8, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.default_replication_factor', value=2, tags=broker_tags)
    aggregator.assert_metric('kafka.broker.config.min_insync_replicas', value=1, tags=broker_tags)

    # Verify topic metrics with exact values
    aggregator.assert_metric(
        'kafka.topic.count',
        value=1,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id'],
    )

    # Topic partitions count (2 partitions in test-topic)
    aggregator.assert_metric(
        'kafka.topic.partitions',
        value=2,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic'],
    )

    # Topic size: partition 0 (100-10=90) + partition 1 (200-20=180) = 270
    aggregator.assert_metric(
        'kafka.topic.size',
        value=270,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic'],
    )

    # Topic message rate: (current sum 300 - prev sum 250) / (time diff ~10s) = ~5 msg/s
    aggregator.assert_metric(
        'kafka.topic.message_rate',
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic'],
    )

    # Verify topic config metrics are emitted
    topic_tags = ['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic']
    aggregator.assert_metric('kafka.topic.config.retention_ms', value=604800000, tags=topic_tags)
    aggregator.assert_metric('kafka.topic.config.max_message_bytes', value=1048588, tags=topic_tags)

    # Verify partition metrics with exact values and broker tags
    # Partition 0: beginning=10, end=100, size = 100 - 10 = 90, leader=1, replicas=[1,2]
    aggregator.assert_metric(
        'kafka.partition.beginning_offset',
        value=10,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
        ],
    )

    aggregator.assert_metric(
        'kafka.partition.size',
        value=90,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
            'leader_broker_id:1',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Partition 1: beginning=20, end=200, size = 200 - 20 = 180, leader=2, replicas=[1,2]
    aggregator.assert_metric(
        'kafka.partition.beginning_offset',
        value=20,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:1',
        ],
    )

    aggregator.assert_metric(
        'kafka.partition.size',
        value=180,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:1',
            'leader_broker_id:2',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Partition replicas count (2 replicas per partition)
    aggregator.assert_metric(
        'kafka.partition.replicas',
        value=2,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
            'leader_broker_id:1',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Partition ISR count (2 in-sync replicas per partition)
    aggregator.assert_metric(
        'kafka.partition.isr',
        value=2,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
            'leader_broker_id:1',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Under-replicated partitions (0 for fully replicated)
    aggregator.assert_metric(
        'kafka.partition.under_replicated',
        value=0,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
            'leader_broker_id:1',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Offline partitions (0 for online partitions)
    aggregator.assert_metric(
        'kafka.partition.offline',
        value=0,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'topic:test-topic',
            'partition:0',
            'leader_broker_id:1',
            'replica_broker_id:1',
            'replica_broker_id:2',
        ],
    )

    # Verify consumer group metrics with exact values
    aggregator.assert_metric(
        'kafka.consumer_group.count',
        value=1,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id'],
    )

    aggregator.assert_metric(
        'kafka.consumer_group.members',
        value=1,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
        ],
    )

    aggregator.assert_metric(
        'kafka.consumer_group.member.partitions',
        value=1,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
            'client_id:c1',
            'member_host:h1',
        ],
    )

    # Verify schema registry metrics with exact values
    aggregator.assert_metric(
        'kafka.schema_registry.subjects',
        value=1,
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id'],
    )

    aggregator.assert_metric(
        'kafka.schema_registry.versions',
        value=2,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'subject:test-topic-value',
        ],
    )

    # Verify broker configuration event structure and content
    broker_config_events = [e for e in aggregator.events if 'event_type:broker_config' in e.get('tags', [])]
    assert len(broker_config_events) >= 1, f"Expected at least 1 broker config event, found {len(broker_config_events)}"

    # Check broker event structure and content
    broker_event = broker_config_events[0]
    assert broker_event['event_type'] == 'config_change', "Broker event type should be 'config_change'"
    assert broker_event['source_type_name'] == 'kafka', "Broker event source should be 'kafka'"
    assert broker_event['msg_title'] == 'Broker 1 Configuration', "Broker event title mismatch"
    assert broker_event['alert_type'] == 'info', "Broker event alert type should be 'info'"
    assert broker_event['aggregation_key'] == 'kafka_broker_config_1', "Broker event aggregation key mismatch"

    # Verify broker event tags
    expected_broker_tags = [
        'test_tag:test_value',
        'kafka_cluster_id:test-cluster-id',
        'broker_id:1',
        'broker_host:broker1',
        'broker_port:9092',
        'event_type:broker_config',
    ]
    for tag in expected_broker_tags:
        assert tag in broker_event['tags'], f"Missing broker event tag: {tag}"

    # Verify broker config content (msg_text should be JSON with realistic config data)
    broker_config_json = json.loads(broker_event['msg_text'])
    expected_broker_config = {
        'log.retention.bytes': '1073741824',
        'log.retention.ms': '604800000',
        'log.segment.bytes': '1073741824',
        'num.partitions': '3',
        'num.network.threads': '3',
        'num.io.threads': '8',
        'default.replication.factor': '2',
        'min.insync.replicas': '1',
        'compression.type': 'producer',
    }
    assert broker_config_json == expected_broker_config, (
        f"Broker config mismatch. Expected {expected_broker_config}, got {broker_config_json}"
    )

    # Verify topic configuration event structure and content
    topic_config_events = [e for e in aggregator.events if 'event_type:topic_config' in e.get('tags', [])]
    assert len(topic_config_events) >= 1, f"Expected at least 1 topic config event, found {len(topic_config_events)}"

    # Check topic event structure and content
    topic_event = topic_config_events[0]
    assert topic_event['event_type'] == 'info', "Topic event type should be 'info'"
    assert topic_event['source_type_name'] == 'kafka', "Topic event source should be 'kafka'"
    assert topic_event['msg_title'] == 'Topic: test-topic (custom config)', "Topic event title mismatch"
    assert topic_event['alert_type'] == 'info', "Topic event alert type should be 'info'"
    assert topic_event['aggregation_key'] == 'kafka_topic_config_test-topic', "Topic event aggregation key mismatch"

    # Verify topic event tags
    expected_topic_tags = [
        'test_tag:test_value',
        'kafka_cluster_id:test-cluster-id',
        'topic:test-topic',
        'event_type:topic_config',
    ]
    for tag in expected_topic_tags:
        assert tag in topic_event['tags'], f"Missing topic event tag: {tag}"

    # Verify topic config content (msg_text should be JSON with realistic config data)
    topic_config_json = json.loads(topic_event['msg_text'])
    expected_topic_config = {
        'retention.ms': '604800000',
        'retention.bytes': '-1',
        'max.message.bytes': '1048588',
        'compression.type': 'producer',
        'cleanup.policy': 'delete',
    }
    assert topic_config_json == expected_topic_config, (
        f"Topic config mismatch. Expected {expected_topic_config}, got {topic_config_json}"
    )

    # Verify schema registry event - check complete structure and content
    schema_events = [e for e in aggregator.events if 'event_type:schema_registry' in e.get('tags', [])]
    assert len(schema_events) == 1, f"Expected 1 schema registry event, found {len(schema_events)}"

    schema_event = schema_events[0]

    # Verify event structure
    assert schema_event['event_type'] == 'info', "Schema event type should be 'info'"
    assert schema_event['source_type_name'] == 'kafka', "Schema event source should be 'kafka'"
    assert schema_event['msg_title'] == 'test-topic (value) - Schema v2', "Schema event title mismatch"
    assert schema_event['alert_type'] == 'info', "Schema event alert type should be 'info'"
    assert schema_event['aggregation_key'] == 'kafka_schema_test-topic-value_2', "Schema event aggregation key mismatch"

    # Verify schema content (msg_text should be a valid Avro schema JSON)
    schema_json = json.loads(schema_event['msg_text'])
    expected_schema = {
        "type": "record",
        "name": "User",
        "namespace": "com.example",
        "fields": [
            {"name": "id", "type": "long"},
            {"name": "username", "type": "string"},
            {"name": "email", "type": ["null", "string"], "default": None},
        ],
    }
    assert schema_json == expected_schema, f"Schema mismatch. Expected {expected_schema}, got {schema_json}"

    # Verify the event has a timestamp
    assert 'timestamp' in schema_event, "Schema event should have a timestamp"
    assert isinstance(schema_event['timestamp'], int), "Schema event timestamp should be an integer"

    # Verify all expected tags are present
    expected_schema_tags = [
        'test_tag:test_value',
        'kafka_cluster_id:test-cluster-id',
        'subject:test-topic-value',
        'schema_id:1',
        'schema_version:2',
        'schema_type:AVRO',
        'topic:test-topic',
        'schema_for:value',
        'event_type:schema_registry',
    ]
    for tag in expected_schema_tags:
        assert tag in schema_event['tags'], f"Missing schema event tag: {tag}"


def test_throughput_with_offset_decrease(check, dd_run_check, aggregator):
    """Test that negative throughput is not reported when offsets decrease (data loss scenario)."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'tags': ['test_tag:test_value'],
    }

    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    # Mock current offsets: partition 0 decreased from 100 to 50 (data loss!)
    # partition 1 increased normally from 200 to 250
    def mock_offsets(partitions, offset=-1):
        if offset == -1:
            return [(topic, partition, 50 if partition == 0 else 250) for topic, partition in partitions]
        else:
            return [(topic, partition, 10 if partition == 0 else 20) for topic, partition in partitions]

    mock_kafka_client.consumer_offsets_for_times = mock_offsets

    # Mock cache with previous offsets
    baseline_cache = {
        'ts': time.time() - 10.0,
        'partitions': {
            'test-topic:0': 100,
            'test-topic:1': 200,
        }
    }
    
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=json.dumps(baseline_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)

    # Verify that message_rate was still reported (partition 1 was valid)
    # Only partition 1 contributed: (250 - 200) / elapsed = positive rate
    aggregator.assert_metric(
        'kafka.topic.message_rate',
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic'],
    )

    # The rate should be positive (only from partition 1)
    metrics = aggregator.metrics('kafka.topic.message_rate')
    for metric in metrics:
        if 'topic:test-topic' in metric.tags:
            assert metric.value > 0, f"Message rate should be positive, got {metric.value}"


def test_throughput_with_partition_unavailable(check, dd_run_check, aggregator):
    """Test that throughput calculation skips unavailable partitions (-1 offset)."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'tags': ['test_tag:test_value'],
    }

    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    # First run: establish baseline with previous timestamp
    baseline_cache = {
        'ts': time.time() - 10.0,
        'partitions': {
            'test-topic:0': 100,
            'test-topic:1': 200,
        }
    }
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=json.dumps(baseline_cache))
    kafka_consumer_check.write_persistent_cache = mock.Mock()

    dd_run_check(kafka_consumer_check)
    aggregator.reset()

    # Second run: partition 0 becomes unavailable (-1), partition 1 increases normally
    def mock_offsets_run2(partitions, offset=-1):
        if offset == -1:
            return [(topic, partition, -1 if partition == 0 else 250) for topic, partition in partitions]
        else:
            return [(topic, partition, 10 if partition == 0 else 20) for topic, partition in partitions]

    mock_kafka_client.consumer_offsets_for_times = mock_offsets_run2

    prev_cache = json.dumps(baseline_cache)
    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=prev_cache)

    dd_run_check(kafka_consumer_check)

    # Verify that message_rate was still reported (partition 1 was valid)
    aggregator.assert_metric(
        'kafka.topic.message_rate',
        tags=['test_tag:test_value', 'kafka_cluster_id:test-cluster-id', 'topic:test-topic'],
    )

    # The rate should be positive (only from partition 1: 250 - 200)
    metrics = aggregator.metrics('kafka.topic.message_rate')
    for metric in metrics:
        if 'topic:test-topic' in metric.tags:
            assert metric.value >= 0, f"Message rate should be non-negative, got {metric.value}"
