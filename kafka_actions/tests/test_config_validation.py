# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import base64
from contextlib import nullcontext

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.kafka_actions.config import KafkaActionsConfig

pytestmark = [pytest.mark.unit]


def _update_consumer_group_offsets_instance(offsets=None):
    """Build an instance dict for the update_consumer_group_offsets action, omitting 'offsets' when None."""
    action_config = {'cluster': 'test', 'consumer_group': 'test'}
    if offsets is not None:
        action_config['offsets'] = offsets
    return {
        'remote_config_id': 'test-id',
        'kafka_connect_str': 'localhost:9092',
        'update_consumer_group_offsets': action_config,
    }


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

    def test_kafka_connect_str_list(self, dd_run_check):
        """Test that kafka_connect_str accepts a list of brokers and joins them."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': ['broker1:9092', 'broker2:9092'],
            'produce_message': {'cluster': 'test', 'topic': 'test', 'value': 'test'},
        }

        config = KafkaActionsConfig(instance, None)
        config.validate_config()
        assert config.kafka_connect_str == 'broker1:9092,broker2:9092'

    def test_kafka_connect_str_string(self, dd_run_check):
        """Test that kafka_connect_str works as a plain string."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'broker1:9092,broker2:9092',
            'produce_message': {'cluster': 'test', 'topic': 'test', 'value': 'test'},
        }

        config = KafkaActionsConfig(instance, None)
        config.validate_config()
        assert config.kafka_connect_str == 'broker1:9092,broker2:9092'


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

    def test_invalid_start_timestamp(self):
        """Test that invalid start_timestamp raises error."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test', 'start_timestamp': -5},
        }

        with pytest.raises(ConfigurationError, match="start_timestamp must be a non-negative integer"):
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

    @pytest.mark.parametrize(
        ('offsets', 'expected_error'),
        [
            pytest.param(None, "update_consumer_group_offsets action requires 'offsets' list", id='missing_offsets'),
            pytest.param(
                [{'topic': 'test'}],
                r"offsets\[0\] requires 'offset' or 'timestamp'",
                id='missing_offset_and_timestamp',
            ),
            pytest.param(
                [{'topic': 'test', 'partition': 0, 'offset': 100, 'timestamp': 1735689600000}],
                r"offsets\[0\] cannot specify both 'offset' and 'timestamp'",
                id='both_offset_and_timestamp',
            ),
            pytest.param(
                [{'topic': 'test', 'offset': 100}],
                r"offsets\[0\] requires 'partition' when 'offset' is specified",
                id='missing_partition_with_offset',
            ),
            pytest.param(
                [{'topic': 'test', 'partition': 0, 'offset': -3}],
                r"offsets\[0\].offset must be -2",
                id='out_of_range_offset',
            ),
            pytest.param(
                [
                    {'topic': 'test', 'partition': 0, 'offset': -2},
                    {'topic': 'test', 'partition': 1, 'offset': -1},
                ],
                None,
                id='sentinel_offsets_are_valid',
            ),
            pytest.param(
                [{'topic': 'test', 'partition': -1, 'offset': 0}],
                r"offsets\[0\].partition must be a non-negative integer",
                id='negative_partition',
            ),
            pytest.param(
                [{'topic': 'test', 'partition': -1, 'timestamp': 1735689600000}],
                r"offsets\[0\].partition must be a non-negative integer",
                id='negative_partition_with_timestamp',
            ),
            pytest.param(
                [{'topic': 'test', 'timestamp': -1}],
                r"offsets\[0\].timestamp must be a positive integer",
                id='invalid_timestamp',
            ),
            pytest.param([{'topic': 'test', 'timestamp': 1735689600000}], None, id='valid_timestamp_all_partitions'),
            pytest.param(
                [{'topic': 'test', 'partition': 2, 'timestamp': 1735689600000}],
                None,
                id='valid_timestamp_specific_partition',
            ),
        ],
    )
    def test_offsets_validation(self, offsets, expected_error):
        """Test update_consumer_group_offsets offsets validation across valid and invalid entries."""
        instance = _update_consumer_group_offsets_instance(offsets)
        expectation = pytest.raises(ConfigurationError, match=expected_error) if expected_error else nullcontext()

        with expectation:
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

    def test_schema_registry_requirement_violations(self):
        """Test that value_uses_schema_registry rejects a missing schema_registry_url."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {
                'cluster': 'test',
                'topic': 'test',
                'value': 'test',
                'value_uses_schema_registry': True,
            },
        }

        with pytest.raises(ConfigurationError, match="requires 'schema_registry_url' to be configured"):
            config = KafkaActionsConfig(instance, None)
            config.validate_config()

    def test_schema_subject_override_does_not_require_schema_registry_url(self):
        """Test that value_schema_subject alone (without value_uses_schema_registry) needs no registry."""
        instance = {
            'remote_config_id': 'test-id',
            'kafka_connect_str': 'localhost:9092',
            'produce_message': {
                'cluster': 'test',
                'topic': 'test',
                'value': base64.b64encode(b'test').decode('utf-8'),
                'value_schema_subject': 'custom-subject',
            },
        }

        config = KafkaActionsConfig(instance, None)
        config.validate_config()
