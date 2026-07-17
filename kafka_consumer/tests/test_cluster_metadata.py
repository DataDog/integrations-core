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

from datadog_checks.kafka_consumer.cache import EVENT_CACHE_TTL
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

    # Group-level metadata used for dimensional tags
    describe_result.partition_assignor = 'range'
    describe_result.is_simple_consumer_group = False
    type_mock = mock.MagicMock()
    type_mock.name = 'CLASSIC'
    describe_result.type = type_mock

    # Mock member
    member = mock.MagicMock()
    member.member_id = 'm1'
    member.client_id = 'c1'
    member.host = 'h1'
    member.group_instance_id = None
    member.target_assignment = None

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
    client._cluster_metadata = metadata
    client.get_topic_partitions.return_value = {'test-topic': [0, 1]}

    def mock_offsets_for_times(partitions, offset=-1):
        if offset == -1:
            return [(topic, partition, 100 if partition == 0 else 200) for topic, partition in partitions]
        else:
            return [(topic, partition, 10 if partition == 0 else 20) for topic, partition in partitions]

    client.get_partition_offsets = mock_offsets_for_times

    def mock_list_offsets(requests, **_kwargs):
        result = {}
        for tp in requests:
            info = mock.MagicMock()
            info.offset = 10 if tp.partition == 0 else 20
            future = mock.MagicMock()
            future.result.return_value = info
            result[tp] = future
        return result

    mock_admin_client.list_offsets.side_effect = mock_list_offsets
    client.consumer_get_cluster_id_and_list_topics.return_value = (cluster_id, [('test-topic', [0, 1])])
    client.list_consumer_group_offsets.return_value = []
    client.open_consumer.return_value = None
    client.close_consumer.return_value = None

    return client


def mock_schema_registry_methods(metadata_collector, global_compat='BACKWARD', subject_compat='BACKWARD'):
    """Mock Schema Registry methods on the metadata collector."""
    metadata_collector._get_schema_registry_subjects = mock.Mock(return_value=['test-topic-value'])

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

    # Tier 1: lightweight version list (returns just version numbers)
    metadata_collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])

    # Tier 2: full schema fetch (only called when version changes)
    metadata_collector._get_schema_registry_latest_version = mock.Mock(
        return_value={
            'id': 1,
            'version': 2,
            'schema': avro_schema,
            'schemaType': 'AVRO',
        }
    )

    mock_compatibility_methods(metadata_collector, global_compat=global_compat, subject_compat=subject_compat)


def mock_compatibility_methods(collector, global_compat='BACKWARD', subject_compat='BACKWARD'):
    """Mock the global and per-subject compatibility fetches on the collector."""
    collector._get_schema_registry_global_compatibility = mock.Mock(return_value=global_compat)
    collector._get_schema_registry_subject_compatibility = mock.Mock(return_value=subject_compat)


def schema_ds_events(check):
    """Return the parsed data-streams-message payloads with config_type 'schema' emitted by the check."""
    events = []
    for call in check.event_platform_event.call_args_list:
        args = call[0]
        if len(args) > 1 and args[1] == 'data-streams-message':
            payload = json.loads(args[0])
            if payload.get('config_type') == 'schema':
                events.append(payload)
    return events


def _make_schema_registry_check(check, instance_overrides=None):
    """Return a check instance wired with a mock Kafka client and persistent cache mocks."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
        'monitor_unlisted_consumer_groups': True,
    }
    if instance_overrides:
        instance.update(instance_overrides)
    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    return kafka_consumer_check


def _wire_cache(kafka_consumer_check, seed=None):
    """Wire persistent-cache and event mocks on the check, returning the backing cache_storage dict.

    Each test only declares its seed cache entries; reads and writes go through this in-memory dict.
    """
    cache_storage = dict(seed or {})
    kafka_consumer_check.read_persistent_cache = mock.Mock(side_effect=cache_storage.get)
    kafka_consumer_check.write_persistent_cache = mock.Mock(
        side_effect=lambda key, value: cache_storage.__setitem__(key, value)
    )
    kafka_consumer_check.event_platform_event = mock.Mock()
    return cache_storage


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
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector, subject_compat='FULL')

    # Mock persistent cache for throughput calculation and schema registry events
    # Using per-partition format: partition 0 was at 75, partition 1 was at 175
    # Total was 250, now will be 300 (100 + 200), so rate = (300-250)/10 = 5.0 msg/sec
    prev_snapshot = {
        'ts': time.time() - 10.0,
        'partitions': {
            'test-topic:0': 75,
            'test-topic:1': 175,
        },
    }

    def mocked_read_cache(key):
        if 'kafka_topic_hwm_sum_cache' in key:
            return json.dumps(prev_snapshot)
        # Return None for other caches to allow first-time event emission
        return None

    kafka_consumer_check.read_persistent_cache = mock.Mock(side_effect=mocked_read_cache)
    kafka_consumer_check.write_persistent_cache = mock.Mock()
    kafka_consumer_check.event_platform_event = mock.Mock()

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
            'partition_assignor:range',
            'consumer_group_type:CLASSIC',
            'is_simple_consumer_group:false',
        ],
    )

    aggregator.assert_metric(
        'kafka.consumer_group.rebalancing',
        value=0,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
            'partition_assignor:range',
            'consumer_group_type:CLASSIC',
            'is_simple_consumer_group:false',
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

    # Broker, topic, and schema configs are emitted only to the Data Streams intake.
    assert not [e for e in aggregator.events if 'event_type:broker_config' in e.get('tags', [])]
    assert not [e for e in aggregator.events if 'event_type:topic_config' in e.get('tags', [])]
    assert not [e for e in aggregator.events if 'event_type:schema_registry' in e.get('tags', [])]

    # Verify events are sent to Data Streams intake
    ds_calls = kafka_consumer_check.event_platform_event.call_args_list
    ds_events = [
        json.loads(call[0][0]) for call in ds_calls if len(call[0]) > 1 and call[0][1] == "data-streams-message"
    ]
    assert len(ds_events) >= 3, (
        f"Expected at least 3 Data Streams events (broker, topic, schema), found {len(ds_events)}"
    )

    broker_ds_events = [e for e in ds_events if e.get('config_type') == 'broker']
    assert len(broker_ds_events) >= 1, "Expected at least 1 broker Data Streams event"
    broker_ds = broker_ds_events[0]
    assert broker_ds['kafka_cluster_id'] == 'test-cluster-id'
    assert broker_ds['broker_id'] == '1'
    assert broker_ds['broker_host'] == 'broker1'
    assert broker_ds['broker_port'] == 9092
    assert 'collection_timestamp' in broker_ds
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
    assert broker_ds['config'] == expected_broker_config

    topic_ds_events = [e for e in ds_events if e.get('config_type') == 'topic']
    assert len(topic_ds_events) >= 1, "Expected at least 1 topic Data Streams event"
    topic_ds = topic_ds_events[0]
    assert topic_ds['kafka_cluster_id'] == 'test-cluster-id'
    assert topic_ds['topic'] == 'test-topic'
    assert 'collection_timestamp' in topic_ds
    expected_topic_config = {
        'retention.ms': '604800000',
        'retention.bytes': '-1',
        'max.message.bytes': '1048588',
        'compression.type': 'producer',
        'cleanup.policy': 'delete',
    }
    assert topic_ds['config'] == expected_topic_config

    schema_events = [e for e in ds_events if e.get('config_type') == 'schema']
    assert len(schema_events) >= 1, "Expected at least 1 schema Data Streams event"
    schema_ds = schema_events[0]
    assert schema_ds['kafka_cluster_id'] == 'test-cluster-id'
    assert schema_ds['subject'] == 'test-topic-value'
    assert schema_ds['schema_id'] == 1
    assert schema_ds['schema_version'] == 2
    assert schema_ds['schema_type'] == 'AVRO'
    assert 'collection_timestamp' in schema_ds
    assert 'schema' in schema_ds
    assert schema_ds['compatibility'] == 'FULL'
    assert schema_ds['global_compatibility'] == 'BACKWARD'
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
    assert json.loads(schema_ds['schema']) == expected_schema


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

    mock_kafka_client.get_partition_offsets = mock_offsets

    # Mock cache with previous offsets
    baseline_cache = {
        'ts': time.time() - 10.0,
        'partitions': {
            'test-topic:0': 100,
            'test-topic:1': 200,
        },
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
        },
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

    mock_kafka_client.get_partition_offsets = mock_offsets_run2

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


def test_event_cache_ttl_not_reset_on_subsequent_calls(check):
    """Test that cache TTL is only updated when events are sent, not on every call.

    This validates the fix for the bug where cache TTL was being reset on every check run,
    preventing events from ever being sent again unless content changed.
    """
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)
    collector = kafka_consumer_check.metadata_collector

    cache_key = 'test_event_cache'
    items = {'item1': 'content1'}

    # Mock the check's cache methods
    cache_storage = {}

    def mock_read(key):
        return cache_storage.get(key)

    def mock_write(key, value):
        cache_storage[key] = value

    collector.check.read_persistent_cache = mock.Mock(side_effect=mock_read)
    collector.check.write_persistent_cache = mock.Mock(side_effect=mock_write)

    # First call at t=1000: no cache, event should be sent
    with mock.patch('time.time', return_value=1000.0):
        events_to_send = collector.cache.get_events_to_send(cache_key, items)
        assert 'item1' in events_to_send, "First call should send event (no cache)"

    # Get the expire_at from first call (should be 1000 + 3600 = 4600)
    cache_dict = json.loads(cache_storage[cache_key])
    first_expire_at = cache_dict['item1']['expire_at']
    assert first_expire_at == 4600.0, f"Expected expire_at=4600.0, got {first_expire_at}"

    # Second call at t=1100: cache exists and valid (1100 < 4600), event should NOT be sent
    with mock.patch('time.time', return_value=1100.0):
        events_to_send = collector.cache.get_events_to_send(cache_key, items)
        assert 'item1' not in events_to_send, "Second call should NOT send event (cache valid)"

    # Verify expire_at was NOT updated (this is the bug fix!)
    cache_dict = json.loads(cache_storage[cache_key])
    second_expire_at = cache_dict['item1']['expire_at']
    assert second_expire_at == 4600.0, f"Cache TTL should NOT be reset when no event is sent, got {second_expire_at}"

    # Third call at t=4601: cache expired (4601 >= 4600), event should be sent
    with mock.patch('time.time', return_value=4601.0):
        events_to_send = collector.cache.get_events_to_send(cache_key, items)
        assert 'item1' in events_to_send, "Third call should send event (cache expired)"

    # Verify expire_at WAS updated after sending event (should be 4601 + 3600 = 8201)
    cache_dict = json.loads(cache_storage[cache_key])
    third_expire_at = cache_dict['item1']['expire_at']
    assert third_expire_at == 8201.0, f"Cache TTL should be updated when event is sent, got {third_expire_at}"


def test_schema_registry_batching(check, dd_run_check, aggregator):
    """Test that schema registry version checking is batched to SCHEMA_VERSION_CHECK_BATCH_SIZE per run.

    With thousands of subjects, only a limited batch should be checked per check run
    to avoid overwhelming the registry.
    """
    kafka_consumer_check = _make_schema_registry_check(check)

    collector = kafka_consumer_check.metadata_collector
    # Set a small batch size for testing
    collector.SCHEMA_VERSION_CHECK_BATCH_SIZE = 2

    # Create 5 subjects
    all_subjects = [f'topic-{i}-value' for i in range(5)]
    collector._get_schema_registry_subjects = mock.Mock(return_value=all_subjects)

    # Tier 1: lightweight version list — all subjects return version [1]
    collector._get_schema_registry_versions = mock.Mock(return_value=[1])

    avro_schema = json.dumps({"type": "string"})
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': 1, 'version': 1, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )

    _wire_cache(kafka_consumer_check)

    mock_compatibility_methods(collector)

    # Run 1: first batch of 2 subjects
    dd_run_check(kafka_consumer_check)

    # Only SCHEMA_VERSION_CHECK_BATCH_SIZE subjects should have version lists fetched
    assert collector._get_schema_registry_versions.call_count == 2

    # All 2 checked subjects have new versions (no prior cache), so full fetch for all 2
    assert collector._get_schema_registry_latest_version.call_count == 2

    # Total subjects metric should still report all 5
    aggregator.assert_metric('kafka.schema_registry.subjects', value=5)

    # Record which subjects were checked in run 1
    run1_subjects = {call.args[0] for call in collector._get_schema_registry_versions.call_args_list}

    # Run 2: the next batch should pick different subjects (the ones not yet fetched)
    dd_run_check(kafka_consumer_check)

    assert collector._get_schema_registry_versions.call_count == 4  # 2 more calls

    run2_subjects = {call.args[0] for call in collector._get_schema_registry_versions.call_args_list[2:]}
    assert run1_subjects.isdisjoint(run2_subjects), (
        f"Run 2 should check different subjects than run 1, but got overlap: run1={run1_subjects}, run2={run2_subjects}"
    )

    # Run 3: picks the remaining 1 subject not yet checked
    dd_run_check(kafka_consumer_check)

    assert collector._get_schema_registry_versions.call_count == 5  # 1 more call

    run3_subjects = {call.args[0] for call in collector._get_schema_registry_versions.call_args_list[4:]}
    assert run3_subjects.isdisjoint(run1_subjects | run2_subjects), (
        f"Run 3 should check the remaining subject, but got overlap: "
        f"run3={run3_subjects}, previous={run1_subjects | run2_subjects}"
    )

    # All 5 subjects should have been checked across the 3 runs
    all_checked = run1_subjects | run2_subjects | run3_subjects
    assert all_checked == set(all_subjects)


def test_schema_registry_schema_id_cache(check, dd_run_check, aggregator):
    """Test that schema content is cached by schema ID and reused across runs.

    Schema IDs in the registry are immutable, so once we fetch the content for a
    given ID we should never need to fetch it again.
    """
    kafka_consumer_check = _make_schema_registry_check(check)

    collector = kafka_consumer_check.metadata_collector

    collector._get_schema_registry_subjects = mock.Mock(return_value=['my-topic-value'])

    # Tier 1: version list
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2, 3])

    avro_schema = json.dumps({"type": "string"})
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': 42, 'version': 3, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )

    cache_storage = _wire_cache(kafka_consumer_check)

    mock_compatibility_methods(collector)

    dd_run_check(kafka_consumer_check)

    # Verify schema ID cache was written
    schema_id_cache_str = cache_storage.get('kafka_schema_id_cache')
    assert schema_id_cache_str is not None
    schema_id_cache = json.loads(schema_id_cache_str)
    assert '42' in schema_id_cache
    assert schema_id_cache['42']['schema'] == avro_schema
    assert schema_id_cache['42']['schema_type'] == 'AVRO'

    # Verify that a second run with the same schema ID skips the full fetch
    assert collector._get_schema_registry_latest_version.call_count == 1
    dd_run_check(kafka_consumer_check)
    assert collector._get_schema_registry_latest_version.call_count == 1


def test_schema_registry_two_tier_ttl(check):
    """Test that schema version checks reuse CONFIGS_REFRESH_INTERVAL and event re-emission uses EVENT_CACHE_TTL."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
    }

    kafka_consumer_check = check(instance)
    collector = kafka_consumer_check.metadata_collector

    # Schema version checks reuse the same refresh interval as broker/topic configs
    assert collector.cache.refresh_interval == 180  # default 3 min

    # All events (broker, topic, schema) share the same re-emission TTL
    assert EVENT_CACHE_TTL == 3600  # 1 hour


def test_schema_registry_two_tier_no_fetch_when_unchanged(check, dd_run_check, aggregator):
    """Test that no full schema fetch happens when version numbers haven't changed.

    The two-tier approach checks version numbers first (lightweight). If the max version
    matches what's cached, no full fetch (/versions/latest) should be made.
    """
    kafka_consumer_check = _make_schema_registry_check(check)

    collector = kafka_consumer_check.metadata_collector

    collector._get_schema_registry_subjects = mock.Mock(return_value=['my-topic-value', 'other-topic-key'])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])

    avro_schema = json.dumps({"type": "string"})
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': 10, 'version': 2, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )

    # Pre-populate the latest version cache so both subjects show max version = 2
    # This simulates a previous run that already fetched these versions.
    latest_version_cache = {
        'my-topic-value': {'version': 2, 'schema_id': 10},
        'other-topic-key': {'version': 2, 'schema_id': 11},
    }

    _wire_cache(kafka_consumer_check, {'kafka_schema_latest_version_cache': json.dumps(latest_version_cache)})

    mock_compatibility_methods(collector)

    dd_run_check(kafka_consumer_check)

    # Version lists should have been fetched (lightweight tier 1)
    assert collector._get_schema_registry_versions.call_count == 2

    # Full schema fetch should NOT have been called (versions unchanged)
    assert collector._get_schema_registry_latest_version.call_count == 0

    # Subjects metric should still be emitted
    aggregator.assert_metric('kafka.schema_registry.subjects', value=2)


def test_schema_registry_two_tier_fetch_on_new_version(check, dd_run_check, aggregator):
    """Test that a full schema fetch happens only for subjects with new versions.

    When a subject has a new version (e.g., max goes from 2 to 3), only that subject
    should trigger a full /versions/latest fetch.
    """
    kafka_consumer_check = _make_schema_registry_check(check)

    collector = kafka_consumer_check.metadata_collector

    collector._get_schema_registry_subjects = mock.Mock(return_value=['unchanged-topic-value', 'changed-topic-value'])

    # Subject "unchanged" returns [1, 2], "changed" returns [1, 2, 3]
    def mock_versions(subject):
        if subject == 'changed-topic-value':
            return [1, 2, 3]
        return [1, 2]

    collector._get_schema_registry_versions = mock.Mock(side_effect=mock_versions)

    avro_schema = json.dumps({"type": "string"})
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': 99, 'version': 3, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )

    mock_compatibility_methods(collector)

    # Pre-populate: both subjects were last seen at version 2
    latest_version_cache = {
        'unchanged-topic-value': {'version': 2, 'schema_id': 50},
        'changed-topic-value': {'version': 2, 'schema_id': 50},
    }

    cache_storage = _wire_cache(
        kafka_consumer_check, {'kafka_schema_latest_version_cache': json.dumps(latest_version_cache)}
    )

    dd_run_check(kafka_consumer_check)

    # Both subjects should have version lists checked
    assert collector._get_schema_registry_versions.call_count == 2

    # Only the changed subject should trigger a full fetch
    assert collector._get_schema_registry_latest_version.call_count == 1
    collector._get_schema_registry_latest_version.assert_called_with('changed-topic-value')

    # Latest version cache should be updated for the changed subject
    updated_cache = json.loads(cache_storage['kafka_schema_latest_version_cache'])
    assert updated_cache['changed-topic-value'] == {'version': 3, 'schema_id': 99, 'compatibility': 'BACKWARD'}
    # Compatibility is refreshed on its own cadence, so the unchanged subject also picks it up.
    assert updated_cache['unchanged-topic-value'] == {'version': 2, 'schema_id': 50, 'compatibility': 'BACKWARD'}


def test_schema_registry_compat_not_refetched_when_cache_fresh(check, dd_run_check, aggregator):
    """A subject with a fresh compat-fetch cache and no version bump must not refetch compatibility.

    This guards the cadence-skip path: SCHEMA_COMPATIBILITY_FETCH_CACHE_KEY + remaining_slots logic
    should keep _get_schema_registry_subject_compatibility from being called every run.
    """
    kafka_consumer_check = _make_schema_registry_check(check)
    collector = kafka_consumer_check.metadata_collector

    subject = 'my-topic-value'
    collector._get_schema_registry_subjects = mock.Mock(return_value=[subject])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])
    collector._get_schema_registry_latest_version = mock.Mock()
    mock_compatibility_methods(collector)

    # Subject is already at version 2 (no bump) and its compat fetch cache is unexpired.
    latest_version_cache = {subject: {'version': 2, 'schema_id': 50, 'compatibility': 'BACKWARD'}}
    compat_fetch_cache = {subject: time.time() + 3600}
    _wire_cache(
        kafka_consumer_check,
        {
            'kafka_schema_latest_version_cache': json.dumps(latest_version_cache),
            'kafka_schema_compatibility_fetch_cache': json.dumps(compat_fetch_cache),
        },
    )

    dd_run_check(kafka_consumer_check)

    # No version bump → no full fetch, and a fresh compat cache → no compat fetch.
    collector._get_schema_registry_latest_version.assert_not_called()
    collector._get_schema_registry_subject_compatibility.assert_not_called()


@pytest.mark.parametrize(
    "global_compat, subject_compat, expected_compat, expected_global",
    [
        pytest.param('BACKWARD', 'FULL', 'FULL', 'BACKWARD', id='subject_flip'),
        pytest.param('FULL', 'BACKWARD', 'BACKWARD', 'FULL', id='global_flip'),
    ],
)
def test_schema_registry_compatibility_flip_triggers_reemission(
    check, dd_run_check, aggregator, global_compat, subject_compat, expected_compat, expected_global
):
    """A compatibility change without a version bump (subject or global) triggers schema re-emission.

    The cache_content key includes both compatibility fields, so flipping either one causes
    re-emission even when the schema version and content are identical and the subject is served
    entirely from cache.
    """
    kafka_consumer_check = _make_schema_registry_check(check)
    collector = kafka_consumer_check.metadata_collector

    subject = 'my-topic-value'
    avro_schema = json.dumps({"type": "string"})
    schema_id = 50

    collector._get_schema_registry_subjects = mock.Mock(return_value=[subject])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': schema_id, 'version': 2, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )
    mock_compatibility_methods(collector, global_compat=global_compat, subject_compat=subject_compat)

    # Pre-populate caches as if a previous run emitted this subject under BACKWARD/BACKWARD.
    old_cache_content = f"{schema_id}:2:BACKWARD:BACKWARD:{avro_schema}"
    old_hash = hashlib.sha256(old_cache_content.encode()).hexdigest()

    latest_version_cache = {subject: {'version': 2, 'schema_id': schema_id, 'compatibility': 'BACKWARD'}}
    schema_id_cache = {str(schema_id): {'schema': avro_schema, 'schema_type': 'AVRO'}}
    schema_emit_cache = {subject: {'hash': old_hash, 'expire_at': time.time() + 3600}}

    _wire_cache(
        kafka_consumer_check,
        {
            'kafka_schema_latest_version_cache': json.dumps(latest_version_cache),
            'kafka_schema_id_cache': json.dumps(schema_id_cache),
            'kafka_schema_cache': json.dumps(schema_emit_cache),
        },
    )

    dd_run_check(kafka_consumer_check)

    # No version bump — full schema fetch should be skipped (subject served from cache).
    collector._get_schema_registry_latest_version.assert_not_called()

    # Flipping either compatibility field should have triggered exactly one re-emission.
    schema_events = schema_ds_events(kafka_consumer_check)
    assert len(schema_events) == 1, f"Expected exactly 1 schema re-emission, got {len(schema_events)}"
    assert schema_events[0]['subject'] == subject
    assert schema_events[0]['compatibility'] == expected_compat
    assert schema_events[0]['global_compatibility'] == expected_global


@pytest.mark.parametrize(
    "interval,expected_interval,expected_jitter",
    [
        (None, 180, 18),  # default: 10% of 180
        (600, 600, 60),  # custom: 10% of 600
        (60, 60, 15),  # jitter floor: 60 // 10 = 6 < 15, so clamped to 15
    ],
)
def test_kafka_configs_refresh_interval(check, interval, expected_interval, expected_jitter):
    """Test that kafka_configs_refresh_interval drives broker/topic TTLs and jitter."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
    }
    if interval is not None:
        instance['kafka_configs_refresh_interval'] = interval

    kafka_consumer_check = check(instance)
    collector = kafka_consumer_check.metadata_collector

    assert collector.cache.refresh_interval == expected_interval
    assert collector.cache.refresh_jitter == expected_jitter


def test_fetch_earliest_offsets_cached_across_calls(check):
    """fetch_earliest_offsets should hit the broker once, then serve later calls from cache."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
    }
    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client

    _wire_cache(kafka_consumer_check)

    collector = kafka_consumer_check.metadata_collector
    topic_partitions = {'test-topic': [0, 1]}

    first = collector.fetch_earliest_offsets(topic_partitions)
    second = collector.fetch_earliest_offsets(topic_partitions)

    expected = {('test-topic', 0): 10, ('test-topic', 1): 20}
    assert first == expected
    assert second == expected
    assert mock_kafka_client.kafka_client.list_offsets.call_count == 1


def test_fetch_earliest_offsets_refetches_when_cache_missing_partitions(check):
    """A fresh cache that doesn't cover every requested partition triggers a full refetch, keeping the same TTL."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
    }
    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client

    collector = kafka_consumer_check.metadata_collector
    expire_at = time.time() + 300
    seed_payload = json.dumps({'expire_at': expire_at, 'offsets': [['test-topic', 0, 10]]})
    _wire_cache(kafka_consumer_check, seed={collector.EARLIEST_OFFSETS_CACHE_KEY: seed_payload})

    topic_partitions = {'test-topic': [0, 1]}
    result = collector.fetch_earliest_offsets(topic_partitions)

    assert result == {('test-topic', 0): 10, ('test-topic', 1): 20}
    assert mock_kafka_client.kafka_client.list_offsets.call_count == 1

    saved = json.loads(kafka_consumer_check.write_persistent_cache.call_args[0][1])
    assert saved['expire_at'] == expire_at


def test_schema_registry_oauth_oidc_token(check, dd_run_check, aggregator):
    """Test that OIDC OAuth token is fetched and passed as Bearer header for Schema Registry."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
        'schema_registry_oauth_token_provider': {
            'url': 'https://idp.example.com/oauth/token',
            'client_id': 'my-client-id',
            'client_secret': 'my-client-secret',
            'scope': 'schema-registry',
        },
        'monitor_unlisted_consumer_groups': True,
    }

    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=None)
    kafka_consumer_check.write_persistent_cache = mock.Mock()
    kafka_consumer_check.event_platform_event = mock.Mock()

    # Mock the OIDC token request
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        'access_token': 'oidc-test-token-123',
        'token_type': 'Bearer',
        'expires_in': 3600,
    }
    mock_response.raise_for_status = mock.Mock()

    collector = kafka_consumer_check.metadata_collector
    original_get = collector.http.get
    mock_http = mock.MagicMock(wraps=collector.http)
    mock_http.post.return_value = mock_response
    mock_http.get.side_effect = original_get
    mock_http.options = collector.http.options
    collector.http = mock_http

    dd_run_check(kafka_consumer_check)

    # Verify token was requested with correct params
    mock_http.post.assert_called_once()
    call_args = mock_http.post.call_args
    assert call_args[0][0] == 'https://idp.example.com/oauth/token'
    assert call_args[1]['data'] == {'grant_type': 'client_credentials', 'scope': 'schema-registry'}
    assert call_args[1]['auth'] == ('my-client-id', 'my-client-secret')

    # Verify Bearer token is stored and included in per-request kwargs
    assert kafka_consumer_check.metadata_collector._schema_registry_oauth_token == 'oidc-test-token-123'
    request_kwargs = kafka_consumer_check.metadata_collector._get_schema_registry_request_kwargs()
    assert request_kwargs.get('extra_headers', {}).get('Authorization') == 'Bearer oidc-test-token-123'

    # Verify schema registry still works (subjects metric emitted)
    aggregator.assert_metric('kafka.schema_registry.subjects', value=1)


def test_schema_registry_oauth_token_refresh_on_expiry(check, dd_run_check, aggregator):
    """Test that expired OIDC token is refreshed on next check run."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
        'schema_registry_oauth_token_provider': {
            'url': 'https://idp.example.com/oauth/token',
            'client_id': 'my-client-id',
            'client_secret': 'my-client-secret',
        },
        'monitor_unlisted_consumer_groups': True,
    }

    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=None)
    kafka_consumer_check.write_persistent_cache = mock.Mock()
    kafka_consumer_check.event_platform_event = mock.Mock()

    collector = kafka_consumer_check.metadata_collector

    # Simulate an already-cached but expired token
    collector._schema_registry_oauth_token = 'old-expired-token'
    collector._schema_registry_oauth_token_expiry = time.time() - 100  # expired

    mock_response = mock.Mock()
    mock_response.json.return_value = {
        'access_token': 'new-refreshed-token',
        'token_type': 'Bearer',
        'expires_in': 3600,
    }
    mock_response.raise_for_status = mock.Mock()

    original_get = collector.http.get
    mock_http = mock.MagicMock(wraps=collector.http)
    mock_http.post.return_value = mock_response
    mock_http.get.side_effect = original_get
    mock_http.options = collector.http.options
    collector.http = mock_http

    dd_run_check(kafka_consumer_check)
    mock_http.post.assert_called_once()

    assert collector._schema_registry_oauth_token == 'new-refreshed-token'
    request_kwargs = collector._get_schema_registry_request_kwargs()
    assert request_kwargs.get('extra_headers', {}).get('Authorization') == 'Bearer new-refreshed-token'


def test_schema_registry_oauth_token_not_refreshed_when_valid(check):
    """Test that a valid (non-expired) token is not re-fetched."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'schema_registry_url': 'http://localhost:8081',
        'schema_registry_oauth_token_provider': {
            'url': 'https://idp.example.com/oauth/token',
            'client_id': 'my-client-id',
            'client_secret': 'my-client-secret',
        },
        'monitor_unlisted_consumer_groups': True,
    }

    kafka_consumer_check = check(instance)
    collector = kafka_consumer_check.metadata_collector

    # Simulate a valid cached token (expires far in the future)
    collector._schema_registry_oauth_token = 'still-valid-token'
    collector._schema_registry_oauth_token_expiry = time.time() + 3600

    mock_http = mock.MagicMock(wraps=collector.http)
    mock_http.options = collector.http.options
    collector.http = mock_http

    collector._refresh_schema_registry_oauth_token()
    mock_http.post.assert_not_called()

    assert collector._schema_registry_oauth_token == 'still-valid-token'


@pytest.mark.parametrize(
    'oauth_config, error_match',
    [
        pytest.param(
            {'client_id': 'id', 'client_secret': 'secret'},
            'url',
            id='missing_url',
        ),
        pytest.param(
            {'url': 'https://idp/token', 'client_secret': 'secret'},
            'client_id',
            id='missing_client_id',
        ),
        pytest.param(
            {'url': 'https://idp/token', 'client_id': 'id'},
            'client_secret',
            id='missing_client_secret',
        ),
    ],
)
def test_schema_registry_oauth_validation_errors(check, dd_run_check, oauth_config, error_match):
    """Test validation errors for schema_registry_oauth_token_provider."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'monitor_unlisted_consumer_groups': True,
        'schema_registry_oauth_token_provider': oauth_config,
    }

    with pytest.raises(Exception, match=error_match):
        dd_run_check(check(instance))


def test_cluster_metadata_with_cluster_id_override(check, dd_run_check, aggregator):
    """When kafka_cluster_id_override is set, metadata metrics and events use the override."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'monitor_unlisted_consumer_groups': True,
        'kafka_cluster_id_override': 'my-override-id',
        'tags': ['test_tag:test_value'],
    }

    kafka_consumer_check = check(instance)

    mock_kafka_client = seed_mock_kafka_client(cluster_id='auto-detected-id')
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client

    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=None)
    kafka_consumer_check.write_persistent_cache = mock.Mock()
    kafka_consumer_check.event_platform_event = mock.Mock()

    dd_run_check(kafka_consumer_check)

    # Verify metrics use override cluster id and include original tag
    aggregator.assert_metric(
        'kafka.broker.count',
        value=2,
        tags=[
            'test_tag:test_value',
            'kafka_cluster_id:my-override-id',
            'original_kafka_cluster_id:auto-detected-id',
            'bootstrap_servers:localhost:9092',
        ],
    )

    # Verify event_platform_event payloads use override and include original
    for call in kafka_consumer_check.event_platform_event.call_args_list:
        payload = json.loads(call[0][0])
        if 'kafka_cluster_id' in payload:
            assert payload['kafka_cluster_id'] == 'my-override-id'
            assert payload['original_kafka_cluster_id'] == 'auto-detected-id'


def test_schema_registry_url_encodes_subject_names(check):
    """Subjects with slashes (e.g. Protobuf references) must be URL-encoded in API calls."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'schema_registry_url': 'http://localhost:8081',
    }
    kafka_check = check(instance)
    collector = kafka_check.metadata_collector

    mock_response = mock.MagicMock()
    mock_response.json.return_value = [1]
    mock_response.raise_for_status.return_value = None
    collector.http = mock.MagicMock()
    collector.http.get.return_value = mock_response

    subject = 'google/protobuf/timestamp.proto'

    collector._get_schema_registry_versions(subject)
    collector.http.get.assert_called_with(
        'http://localhost:8081/subjects/google%2Fprotobuf%2Ftimestamp.proto/versions', verify=True
    )

    collector.http.get.reset_mock()
    collector._get_schema_registry_latest_version(subject)
    collector.http.get.assert_called_with(
        'http://localhost:8081/subjects/google%2Fprotobuf%2Ftimestamp.proto/versions/latest', verify=True
    )

    collector.http.get.reset_mock()
    mock_response.json.return_value = {'compatibilityLevel': 'BACKWARD'}
    collector._get_schema_registry_subject_compatibility(subject)
    collector.http.get.assert_called_with(
        'http://localhost:8081/config/google%2Fprotobuf%2Ftimestamp.proto',
        params={'defaultToGlobal': 'true'},
        verify=True,
    )


@pytest.mark.parametrize(
    "replicas, isrs, expected_oos, expected_under",
    [
        pytest.param([1, 2], [1, 2], [], 0, id="fully_in_sync"),
        pytest.param([1, 2], [1], [2], 1, id="single_oos"),
        pytest.param([1, 2, 3], [1], [2, 3], 1, id="multiple_oos"),
        pytest.param([1, 2], [], [1, 2], 1, id="empty_isr"),
        pytest.param([1], [1], [], 0, id="single_replica"),
    ],
)
def test_partition_out_of_sync_broker_id_tag(
    check, dd_run_check, aggregator, replicas, isrs, expected_oos, expected_under
):
    """Under-replicated partitions expose an ``out_of_sync_broker_id`` tag per replica missing from the ISR."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'tags': ['test_tag:test_value'],
    }

    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()

    topic_metadata = mock_kafka_client.kafka_client.list_topics.return_value.topics['test-topic']
    topic_metadata.partitions[0].replicas = replicas
    topic_metadata.partitions[0].isrs = isrs

    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.metadata_collector.client = mock_kafka_client
    mock_schema_registry_methods(kafka_consumer_check.metadata_collector)

    kafka_consumer_check.read_persistent_cache = mock.Mock(return_value=None)
    kafka_consumer_check.write_persistent_cache = mock.Mock()
    kafka_consumer_check.event_platform_event = mock.Mock()

    dd_run_check(kafka_consumer_check)

    expected_tags = [
        'test_tag:test_value',
        'kafka_cluster_id:test-cluster-id',
        'topic:test-topic',
        'partition:0',
        'leader_broker_id:1',
        *(f'replica_broker_id:{r}' for r in replicas),
        *(f'out_of_sync_broker_id:{b}' for b in expected_oos),
    ]
    aggregator.assert_metric('kafka.partition.under_replicated', value=expected_under, tags=expected_tags)
    for metric in (
        'kafka.partition.replicas',
        'kafka.partition.isr',
        'kafka.partition.size',
        'kafka.partition.offline',
    ):
        aggregator.assert_metric(metric, tags=expected_tags)


def test_heartbeat_brokers_populated(check):
    """Heartbeat payload includes the broker list when metadata is available."""
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.event_platform_event = mock.Mock()

    kafka_consumer_check._send_cluster_monitoring_heartbeat(total_contexts=5, cluster_id='test-cluster-id')

    calls = kafka_consumer_check.event_platform_event.call_args_list
    hb_events = [json.loads(c[0][0]) for c in calls if c[0][1] == 'data-streams-message']
    hb_events = [e for e in hb_events if e.get('config_type') == 'heartbeat']
    assert len(hb_events) == 1
    assert hb_events[0]['brokers'] == [
        {'id': '1', 'host': 'broker1', 'port': 9092},
        {'id': '2', 'host': 'broker2', 'port': 9092},
    ]


def test_heartbeat_brokers_empty_when_no_metadata(check):
    """Heartbeat payload has an empty broker list when _cluster_metadata is None."""
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)
    mock_kafka_client = seed_mock_kafka_client()
    mock_kafka_client._cluster_metadata = None
    kafka_consumer_check.client = mock_kafka_client
    kafka_consumer_check.event_platform_event = mock.Mock()

    kafka_consumer_check._send_cluster_monitoring_heartbeat(total_contexts=0, cluster_id='test-cluster-id')

    calls = kafka_consumer_check.event_platform_event.call_args_list
    hb_events = [json.loads(c[0][0]) for c in calls if c[0][1] == 'data-streams-message']
    hb_events = [e for e in hb_events if e.get('config_type') == 'heartbeat']
    assert len(hb_events) == 1
    assert hb_events[0]['brokers'] == []


def test_schema_registry_subject_compat_failure_on_version_bump_preserves_cached_compat(
    check, dd_run_check, aggregator
):
    """When compat fetch raises for a version-bumped subject, the previous cached value is preserved."""
    kafka_consumer_check = _make_schema_registry_check(check)

    subject = 'my-topic-value'
    avro_schema = json.dumps({"type": "string"})
    schema_id = 42

    collector = kafka_consumer_check.metadata_collector
    collector._get_schema_registry_subjects = mock.Mock(return_value=[subject])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2, 3])
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': schema_id, 'version': 3, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )
    collector._get_schema_registry_global_compatibility = mock.Mock(return_value='BACKWARD')
    collector._get_schema_registry_subject_compatibility = mock.Mock(side_effect=Exception("registry down"))

    # Previous run had version 2 with FULL compatibility cached.
    latest_version_cache = {subject: {'version': 2, 'schema_id': 10, 'compatibility': 'FULL'}}
    cache_storage = _wire_cache(
        kafka_consumer_check,
        {
            'kafka_schema_latest_version_cache': json.dumps(latest_version_cache),
            'kafka_schema_id_cache': json.dumps({}),
        },
    )

    dd_run_check(kafka_consumer_check)

    # The new cache entry must preserve the previously known compatibility, not write None.
    saved_cache = json.loads(cache_storage.get('kafka_schema_latest_version_cache', '{}'))
    assert saved_cache[subject]['compatibility'] == 'FULL'

    # The emitted payload must also carry the preserved compatibility.
    schema_events = schema_ds_events(kafka_consumer_check)
    assert len(schema_events) == 1
    assert schema_events[0]['compatibility'] == 'FULL'


def test_schema_registry_global_compat_failure_uses_last_known_value(check, dd_run_check, aggregator):
    """When the global compatibility fetch fails, the last successfully fetched value is used."""
    kafka_consumer_check = _make_schema_registry_check(check)

    subject = 'my-topic-value'
    avro_schema = json.dumps({"type": "string"})
    schema_id = 77

    collector = kafka_consumer_check.metadata_collector
    collector._get_schema_registry_subjects = mock.Mock(return_value=[subject])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1])
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': schema_id, 'version': 1, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )
    collector._get_schema_registry_global_compatibility = mock.Mock(side_effect=Exception("registry down"))
    collector._get_schema_registry_subject_compatibility = mock.Mock(return_value='BACKWARD')

    # Simulate a previously cached global compatibility of 'FULL'.
    _wire_cache(kafka_consumer_check, {'kafka_schema_global_compatibility_cache': 'FULL'})

    dd_run_check(kafka_consumer_check)

    schema_events = schema_ds_events(kafka_consumer_check)
    assert len(schema_events) == 1
    assert schema_events[0]['global_compatibility'] == 'FULL'


def test_schema_registry_none_compat_in_cache_omits_field(check, dd_run_check, aggregator):
    """A cached entry with compatibility=None must not include the field in the DS payload."""
    kafka_consumer_check = _make_schema_registry_check(check)

    subject = 'my-topic-value'
    avro_schema = json.dumps({"type": "string"})
    schema_id = 99

    collector = kafka_consumer_check.metadata_collector
    collector._get_schema_registry_subjects = mock.Mock(return_value=[subject])
    collector._get_schema_registry_versions = mock.Mock(return_value=[1, 2])
    collector._get_schema_registry_latest_version = mock.Mock(
        return_value={'id': schema_id, 'version': 2, 'schema': avro_schema, 'schemaType': 'AVRO'}
    )
    collector._get_schema_registry_global_compatibility = mock.Mock(return_value=None)
    collector._get_schema_registry_subject_compatibility = mock.Mock(return_value=None)

    _wire_cache(kafka_consumer_check)

    dd_run_check(kafka_consumer_check)

    schema_events = schema_ds_events(kafka_consumer_check)
    assert len(schema_events) == 1
    assert 'compatibility' not in schema_events[0]
    assert 'global_compatibility' not in schema_events[0]


def _tp(topic, partition):
    tp = mock.MagicMock()
    tp.topic = topic
    tp.partition = partition
    return tp


def _make_assignment(tps):
    if tps is None:
        return None
    assignment = mock.MagicMock()
    assignment.topic_partitions = [_tp(t, p) for t, p in tps]
    return assignment


def _make_member(
    client_id='c1', host='h1', assignment_tps=(('test-topic', 0),), target_tps=None, group_instance_id=None
):
    member = mock.MagicMock()
    member.member_id = f'm-{client_id}'
    member.client_id = client_id
    member.host = host
    member.group_instance_id = group_instance_id
    member.assignment = _make_assignment(assignment_tps)
    member.target_assignment = _make_assignment(target_tps)
    return member


def _make_group_describe(
    state_name='STABLE', assignor='range', is_simple=False, group_type='CONSUMER', members=(), coordinator_id=1
):
    describe_result = mock.MagicMock()
    state_mock = mock.MagicMock()
    state_mock.name = state_name
    describe_result.state = state_mock
    describe_result.partition_assignor = assignor
    describe_result.is_simple_consumer_group = is_simple
    if group_type is None:
        describe_result.type = None
    else:
        type_mock = mock.MagicMock()
        type_mock.name = group_type
        describe_result.type = type_mock
    coordinator_mock = mock.MagicMock()
    coordinator_mock.id = coordinator_id
    describe_result.coordinator = coordinator_mock
    describe_result.members = list(members)
    return describe_result


def _stub_consumer_groups(admin, describe_by_group):
    """Wire list_consumer_groups + describe_consumer_groups futures on a mock admin client."""
    list_result = mock.MagicMock()
    list_result.errors = []
    list_result.valid = [mock.MagicMock(group_id=gid) for gid in describe_by_group]
    list_future = mock.MagicMock()
    list_future.result.return_value = list_result
    admin.list_consumer_groups.return_value = list_future

    futures = {}
    for gid, describe_result in describe_by_group.items():
        future = mock.MagicMock()
        future.result.return_value = describe_result
        futures[gid] = future
    admin.describe_consumer_groups.return_value = futures


def _collect_groups(check, describe_result, group_id='test-group'):
    """Run _collect_consumer_group_metadata against a single mocked consumer group.

    Reuses the shared seed_mock_kafka_client wiring and only swaps in the
    consumer-group futures, so the admin-client mock setup is not duplicated.
    """
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)

    mock_client = seed_mock_kafka_client()
    _stub_consumer_groups(mock_client.kafka_client, {group_id: describe_result})
    kafka_consumer_check.metadata_collector.client = mock_client

    metadata = mock.MagicMock()
    metadata.cluster_id = 'test-cluster-id'
    kafka_consumer_check.metadata_collector._collect_consumer_group_metadata(metadata)
    return kafka_consumer_check


def _collect_groups_with_cache(check, describe_result, seed=None, group_id='test-group'):
    """Like _collect_groups but wires the persistent cache so membership-change logic is exercised."""
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)

    mock_client = seed_mock_kafka_client()
    _stub_consumer_groups(mock_client.kafka_client, {group_id: describe_result})
    kafka_consumer_check.metadata_collector.client = mock_client
    _wire_cache(kafka_consumer_check, seed)

    metadata = mock.MagicMock()
    metadata.cluster_id = 'test-cluster-id'
    kafka_consumer_check.metadata_collector._collect_consumer_group_metadata(metadata)
    return kafka_consumer_check


def test_consumer_group_rebalancing_state_based(check, aggregator):
    """A group in a rebalancing state reports rebalancing=1 (classic protocol)."""
    describe_result = _make_group_describe(state_name='PREPARING_REBALANCING', members=[_make_member()])
    _collect_groups(check, describe_result)
    aggregator.assert_metric(
        'kafka.consumer_group.rebalancing',
        value=1,
        tags=[
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:PREPARING_REBALANCING',
            'coordinator:1',
            'partition_assignor:range',
            'consumer_group_type:CONSUMER',
            'is_simple_consumer_group:false',
        ],
    )


def test_consumer_group_rebalancing_target_assignment(check, aggregator):
    """A stable group whose assignment != target_assignment reports rebalancing=1 (KIP-848)."""
    member = _make_member(assignment_tps=[('test-topic', 0)], target_tps=[('test-topic', 0), ('test-topic', 1)])
    describe_result = _make_group_describe(state_name='STABLE', members=[member])
    _collect_groups(check, describe_result)
    aggregator.assert_metric('kafka.consumer_group.rebalancing', value=1)


def test_consumer_group_not_rebalancing_when_assignment_matches_target(check, aggregator):
    """A stable group whose assignment == target_assignment reports rebalancing=0."""
    member = _make_member(assignment_tps=[('test-topic', 0)], target_tps=[('test-topic', 0)])
    describe_result = _make_group_describe(state_name='STABLE', members=[member])
    _collect_groups(check, describe_result)
    aggregator.assert_metric('kafka.consumer_group.rebalancing', value=0)


def test_consumer_group_not_rebalancing_when_no_target_assignment(check, aggregator):
    """A stable classic-protocol member (no target_assignment) is skipped, reporting rebalancing=0."""
    member = _make_member(assignment_tps=[('test-topic', 0)], target_tps=None)
    describe_result = _make_group_describe(state_name='STABLE', members=[member])
    _collect_groups(check, describe_result)
    aggregator.assert_metric('kafka.consumer_group.rebalancing', value=0)


def test_consumer_group_dimensional_tags(check, aggregator):
    """Group-level metadata is attached as tags on consumer_group.members."""
    describe_result = _make_group_describe(
        state_name='STABLE',
        assignor='cooperative-sticky',
        is_simple=True,
        group_type='CONSUMER',
        members=[_make_member()],
    )
    _collect_groups(check, describe_result)
    aggregator.assert_metric(
        'kafka.consumer_group.members',
        value=1,
        tags=[
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
            'partition_assignor:cooperative-sticky',
            'consumer_group_type:CONSUMER',
            'is_simple_consumer_group:true',
        ],
    )


@pytest.mark.parametrize('assignor', [None, ''], ids=['none', 'empty_string'])
def test_consumer_group_dimensional_tags_absent_when_unset(check, aggregator, assignor):
    """When the broker reports no assignor (None or empty for KIP-848 groups), no dimensional tags are attached."""
    describe_result = _make_group_describe(
        state_name='STABLE', assignor=assignor, is_simple=None, group_type=None, members=[_make_member()]
    )
    _collect_groups(check, describe_result)
    aggregator.assert_metric(
        'kafka.consumer_group.members',
        value=1,
        tags=[
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
        ],
    )


def test_consumer_group_member_static_membership_tag(check, aggregator):
    """A member with a group_instance_id is tagged as a static member."""
    member = _make_member(group_instance_id='static-1')
    describe_result = _make_group_describe(state_name='STABLE', members=[member])
    _collect_groups(check, describe_result)
    aggregator.assert_metric(
        'kafka.consumer_group.member.partitions',
        value=1,
        tags=[
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
            'client_id:c1',
            'member_host:h1',
            'group_instance_id:static-1',
        ],
    )


def test_membership_changes_not_emitted_on_first_run(check, aggregator):
    """No membership_changes on first run — no prior cache to compare against."""
    describe_result = _make_group_describe(members=[_make_member()])
    _collect_groups_with_cache(check, describe_result)
    aggregator.assert_metric('kafka.consumer_group.membership_changes', count=0)


def test_membership_changes_not_emitted_when_members_unchanged(check, aggregator):
    """No membership_changes when the member set is identical to the previous run."""
    member = _make_member(client_id='c1')
    prev_hash = hashlib.sha256(b'["m-c1"]').hexdigest()
    cache_key = 'kafka_consumer_group_members_cache'
    describe_result = _make_group_describe(members=[member])
    _collect_groups_with_cache(
        check,
        describe_result,
        seed={cache_key: json.dumps({'test-group': prev_hash})},
    )
    aggregator.assert_metric('kafka.consumer_group.membership_changes', count=0)


def test_membership_changes_emitted_when_members_differ(check, aggregator):
    """membership_changes fires exactly once when the member set differs from the prior run."""
    cache_key = 'kafka_consumer_group_members_cache'
    old_hash = hashlib.sha256(b'["m-old"]').hexdigest()
    describe_result = _make_group_describe(members=[_make_member(client_id='new')])
    _collect_groups_with_cache(
        check,
        describe_result,
        seed={cache_key: json.dumps({'test-group': old_hash})},
    )
    aggregator.assert_metric(
        'kafka.consumer_group.membership_changes',
        value=1,
        count=1,
        tags=[
            'kafka_cluster_id:test-cluster-id',
            'consumer_group:test-group',
            'consumer_group_state:STABLE',
            'coordinator:1',
            'partition_assignor:range',
            'consumer_group_type:CONSUMER',
            'is_simple_consumer_group:false',
        ],
    )


def test_consumer_group_rebalancing_when_assignment_none_but_target_present(check, aggregator):
    """A KIP-848 member with no current assignment but a non-empty target reports rebalancing=1."""
    member = _make_member(assignment_tps=None, target_tps=[('orders', 0)])
    describe_result = _make_group_describe(state_name='STABLE', members=[member])
    _collect_groups(check, describe_result)
    aggregator.assert_metric('kafka.consumer_group.rebalancing', value=1)


def test_membership_hash_delimiter_collision(check, aggregator):
    """Member IDs that share characters with the delimiter produce distinct hashes."""
    ids_a = ['a,b', 'c']
    ids_b = ['a', 'b,c']
    hash_a = hashlib.sha256(json.dumps(sorted(ids_a), separators=(',', ':')).encode()).hexdigest()
    hash_b = hashlib.sha256(json.dumps(sorted(ids_b), separators=(',', ':')).encode()).hexdigest()
    assert hash_a != hash_b


def test_malformed_cache_does_not_abort_collection(check, aggregator):
    """A non-dict cache value is silently discarded and group gauges are still emitted."""
    cache_key = 'kafka_consumer_group_members_cache'
    describe_result = _make_group_describe(members=[_make_member()])
    _collect_groups_with_cache(
        check,
        describe_result,
        seed={cache_key: json.dumps([])},  # list instead of dict
    )
    aggregator.assert_metric('kafka.consumer_group.members', count=1)
    aggregator.assert_metric('kafka.consumer_group.membership_changes', count=0)


def _consumer_membership_events(check):
    """Return parsed data-streams-message payloads with config_type 'consumer_membership'."""
    events = []
    for call in check.event_platform_event.call_args_list:
        args = call[0]
        if len(args) > 1 and args[1] == 'data-streams-message':
            payload = json.loads(args[0])
            if payload.get('config_type') == 'consumer_membership':
                events.append(payload)
    return events


def test_consumer_membership_event_emitted(check):
    """A consumer_membership event is emitted per group with the cluster id, group id and members."""
    members = [_make_member(client_id='c1', host='h1'), _make_member(client_id='c2', host='h2')]
    describe_result = _make_group_describe(members=members)
    kafka_consumer_check = _collect_groups_with_cache(check, describe_result)

    events = _consumer_membership_events(kafka_consumer_check)
    assert len(events) == 1
    event = events[0]
    assert event['kafka_cluster_id'] == 'test-cluster-id'
    assert event['group_id'] == 'test-group'
    assert event['member_ids'] == ['m-c1', 'm-c2']
    # Per-member detail includes client_id and member_host (captured for free from describe).
    assert event['members'] == [
        {'member_id': 'm-c1', 'client_id': 'c1', 'member_host': 'h1'},
        {'member_id': 'm-c2', 'client_id': 'c2', 'member_host': 'h2'},
    ]


def test_heartbeat_connect_api_status_present_when_urls_configured(check):
    """connect_api_status appears in heartbeat payload when Connect URLs are configured."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'kafka_connect_url': 'http://connect:8083',
    }
    kafka_consumer_check = check(instance)
    kafka_consumer_check.event_platform_event = mock.Mock()

    with mock.patch.object(
        kafka_consumer_check._connector_collector,
        'collect',
        return_value={'http://connect:8083': True},
    ):
        kafka_consumer_check._send_cluster_monitoring_heartbeat(
            total_contexts=0,
            cluster_id='test-cluster',
            connect_status={'http://connect:8083': True},
        )

    calls = kafka_consumer_check.event_platform_event.call_args_list
    hb_events = [json.loads(c[0][0]) for c in calls if c[0][1] == 'data-streams-message']
    hb_events = [e for e in hb_events if e.get('config_type') == 'heartbeat']
    assert len(hb_events) == 1
    assert 'connect_api_status' in hb_events[0]
    assert hb_events[0]['connect_api_status'] == {'http://connect:8083': True}


def test_heartbeat_connect_api_status_absent_when_no_urls(check):
    """connect_api_status is absent from heartbeat payload when no Connect URLs are configured."""
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)
    kafka_consumer_check.event_platform_event = mock.Mock()

    kafka_consumer_check._send_cluster_monitoring_heartbeat(total_contexts=0, cluster_id='test-cluster')

    calls = kafka_consumer_check.event_platform_event.call_args_list
    hb_events = [json.loads(c[0][0]) for c in calls if c[0][1] == 'data-streams-message']
    hb_events = [e for e in hb_events if e.get('config_type') == 'heartbeat']
    assert len(hb_events) == 1
    assert 'connect_api_status' not in hb_events[0]


def test_collect_connect_status_returns_none_when_unconfigured(check):
    """_collect_connect_status returns None when no Connect URLs are configured."""
    instance = {'kafka_connect_str': 'localhost:9092', 'enable_cluster_monitoring': True}
    kafka_consumer_check = check(instance)

    result = kafka_consumer_check._collect_connect_status('test-cluster')
    assert result is None


def test_collect_connect_status_degrades_to_empty_dict_on_exception(check):
    """_collect_connect_status returns {} when the collector raises, instead of propagating."""
    instance = {
        'kafka_connect_str': 'localhost:9092',
        'enable_cluster_monitoring': True,
        'kafka_connect_url': 'http://connect:8083',
    }
    kafka_consumer_check = check(instance)

    with mock.patch.object(
        kafka_consumer_check._connector_collector,
        'collect',
        side_effect=Exception("connection refused"),
    ):
        result = kafka_consumer_check._collect_connect_status('test-cluster')

    assert result == {}
