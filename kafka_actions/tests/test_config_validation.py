# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_actions.config import KafkaActionsConfig

pytestmark = [pytest.mark.unit]


class TestConfigValidation:
    """Test configuration validation."""

    def test_missing_remote_config_id(self, dd_run_check):
        """Test that missing remote_config_id raises error."""
        instance = {
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {'cluster': 'test', 'topic': 'test', 'value': 'test'},
        }

        with pytest.raises(ConfigurationError, match="remote_config_id is required"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_kafka_connect_str(self, dd_run_check):
        """Test that missing kafka_connect_str raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'produce_message': {'cluster': 'test', 'topic': 'test', 'value': 'test'},
        }

        with pytest.raises(ConfigurationError, match="kafka_connect_str is required"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_no_action_configured(self, dd_run_check):
        """Test that missing action raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
        }

        with pytest.raises(ConfigurationError, match="No action detected"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()


class TestReadMessagesValidation:
    """Test read_messages action validation."""

    def test_missing_cluster(self):
        """Test that missing cluster raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'topic': 'test'},
        }

        with pytest.raises(ConfigurationError, match="read_messages action requires 'cluster' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_topic(self):
        """Test that missing topic raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test'},
        }

        with pytest.raises(ConfigurationError, match="read_messages action requires 'topic' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_invalid_value_format(self):
        """Test that invalid value_format raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test', 'value_format': 'invalid'},
        }

        with pytest.raises(ConfigurationError, match="Invalid value_format"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_protobuf_without_schema(self):
        """Test that protobuf format without schema raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {
                'cluster': 'test',
                'topic': 'test',
                'value_format': 'protobuf',
                'value_uses_schema_registry': False,
            },
        }

        with pytest.raises(ConfigurationError, match="value_format='protobuf' requires"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()


class TestCreateTopicValidation:
    """Test create_topic action validation."""

    def test_missing_cluster(self):
        """Test that missing cluster raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {'topic': 'test', 'num_partitions': 1, 'replication_factor': 1},
        }

        with pytest.raises(ConfigurationError, match="create_topic action requires 'cluster' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_topic(self):
        """Test that missing topic raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {'cluster': 'test', 'num_partitions': 1, 'replication_factor': 1},
        }

        with pytest.raises(ConfigurationError, match="create_topic action requires 'topic' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_num_partitions(self):
        """Test that missing num_partitions raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {'cluster': 'test', 'topic': 'test', 'replication_factor': 1},
        }

        with pytest.raises(ConfigurationError, match="create_topic action requires 'num_partitions' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_replication_factor(self):
        """Test that missing replication_factor raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {'cluster': 'test', 'topic': 'test', 'num_partitions': 1},
        }

        with pytest.raises(ConfigurationError, match="create_topic action requires 'replication_factor' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_invalid_num_partitions(self):
        """Test that invalid num_partitions raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'create_topic': {'cluster': 'test', 'topic': 'test', 'num_partitions': 0, 'replication_factor': 1},
        }

        with pytest.raises(ConfigurationError, match="num_partitions must be a positive integer"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()


class TestDeleteTopicValidation:
    """Test delete_topic action validation."""

    def test_missing_cluster(self):
        """Test that missing cluster raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'delete_topic': {'topic': 'test'},
        }

        with pytest.raises(ConfigurationError, match="delete_topic action requires 'cluster' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_missing_topic(self):
        """Test that missing topic raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'delete_topic': {'cluster': 'test'},
        }

        with pytest.raises(ConfigurationError, match="delete_topic action requires 'topic' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()


class TestUpdateConsumerGroupOffsetsValidation:
    """Test update_consumer_group_offsets action validation."""

    def test_missing_offsets(self):
        """Test that missing offsets raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {'cluster': 'test', 'consumer_group': 'test'},
        }

        with pytest.raises(ConfigurationError, match="update_consumer_group_offsets action requires 'offsets' list"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_invalid_offset_entry(self):
        """Test that invalid offset entry raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'update_consumer_group_offsets': {
                'cluster': 'test',
                'consumer_group': 'test',
                'offsets': [{'topic': 'test'}],  # Missing partition and offset
            },
        }

        with pytest.raises(ConfigurationError, match="offsets\\[0\\] requires 'partition' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()


class TestProduceMessageValidation:
    """Test produce_message action validation."""

    def test_missing_value(self):
        """Test that missing value raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {'cluster': 'test', 'topic': 'test'},
        }

        with pytest.raises(ConfigurationError, match="produce_message action requires 'value' parameter"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_valid_config(self):
        """Test that valid config passes validation."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {
                'cluster': 'test',
                'topic': 'test',
                'value': base64.b64encode(b'test').decode('utf-8'),
            },
        }

        config = KafkaActionsConfig(instance, None)
        config.validate_config()

        assert config.action == 'produce_message'
        assert config.remote_config_id == 'test-id'
        assert config.kafka_connect_str == 'localhost:9092'
