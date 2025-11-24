# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Comprehensive tests for message filtering logic."""

import json
from unittest.mock import MagicMock

import pytest

from datadog_checks.kafka_actions.check import KafkaActionsCheck
from datadog_checks.kafka_actions.message_deserializer import DeserializedMessage, MessageDeserializer

pytestmark = [pytest.mark.unit]


class MockKafkaMessage:
    """Mock confluent_kafka.Message for testing."""

    def __init__(self, key, value, topic='test-topic', partition=0, offset=0):
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
        return None


class TestFilteringOperators:
    """Test all filtering operators."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, value_dict):
        """Helper to create a deserialized message from a value dict."""
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_equality_operator(self):
        """Test == operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test', 'filter': '.value.status == "active"'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        # Match
        msg = self.create_message({'status': 'active'})
        assert check._evaluate_filter('.value.status == "active"', msg) is True

        # No match
        msg = self.create_message({'status': 'inactive'})
        assert check._evaluate_filter('.value.status == "active"', msg) is False

    def test_inequality_operator(self):
        """Test != operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test', 'filter': '.value.status != "deleted"'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'status': 'active'})
        assert check._evaluate_filter('.value.status != "deleted"', msg) is True

        msg = self.create_message({'status': 'deleted'})
        assert check._evaluate_filter('.value.status != "deleted"', msg) is False

    def test_greater_than_operator(self):
        """Test > operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'amount': 1500})
        assert check._evaluate_filter('.value.amount > 1000', msg) is True

        msg = self.create_message({'amount': 500})
        assert check._evaluate_filter('.value.amount > 1000', msg) is False

        msg = self.create_message({'amount': 1000})
        assert check._evaluate_filter('.value.amount > 1000', msg) is False

    def test_less_than_operator(self):
        """Test < operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'age': 15})
        assert check._evaluate_filter('.value.age < 18', msg) is True

        msg = self.create_message({'age': 25})
        assert check._evaluate_filter('.value.age < 18', msg) is False

    def test_greater_than_or_equal_operator(self):
        """Test >= operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'percentage': 100})
        assert check._evaluate_filter('.value.percentage >= 100', msg) is True

        msg = self.create_message({'percentage': 101})
        assert check._evaluate_filter('.value.percentage >= 100', msg) is True

        msg = self.create_message({'percentage': 99})
        assert check._evaluate_filter('.value.percentage >= 100', msg) is False

    def test_less_than_or_equal_operator(self):
        """Test <= operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'stock': 5})
        assert check._evaluate_filter('.value.stock <= 10', msg) is True

        msg = self.create_message({'stock': 10})
        assert check._evaluate_filter('.value.stock <= 10', msg) is True

        msg = self.create_message({'stock': 15})
        assert check._evaluate_filter('.value.stock <= 10', msg) is False

    def test_contains_operator_string(self):
        """Test contains operator with strings."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'email': 'user@datadoghq.com'})
        assert check._evaluate_filter('.value.email contains "@datadoghq.com"', msg) is True

        msg = self.create_message({'email': 'user@gmail.com'})
        assert check._evaluate_filter('.value.email contains "@datadoghq.com"', msg) is False

    def test_contains_operator_array(self):
        """Test contains operator with arrays."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'tags': ['vip', 'premium', 'active']})
        assert check._evaluate_filter('.value.tags contains "vip"', msg) is True

        msg = self.create_message({'tags': ['basic', 'active']})
        assert check._evaluate_filter('.value.tags contains "vip"', msg) is False


class TestLogicalOperators:
    """Test logical AND and OR operators."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, value_dict):
        """Helper to create a deserialized message from a value dict."""
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_and_operator(self):
        """Test AND operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        # Both conditions true
        msg = self.create_message({'status': 'failed', 'region': 'US'})
        assert check._evaluate_filter('.value.status == "failed" and .value.region == "US"', msg) is True

        # First true, second false
        msg = self.create_message({'status': 'failed', 'region': 'EU'})
        assert check._evaluate_filter('.value.status == "failed" and .value.region == "US"', msg) is False

        # First false, second true
        msg = self.create_message({'status': 'success', 'region': 'US'})
        assert check._evaluate_filter('.value.status == "failed" and .value.region == "US"', msg) is False

    def test_or_operator(self):
        """Test OR operator."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        # First true
        msg = self.create_message({'priority': 'high', 'urgent': False})
        assert check._evaluate_filter('.value.priority == "high" or .value.urgent == true', msg) is True

        # Second true
        msg = self.create_message({'priority': 'low', 'urgent': True})
        assert check._evaluate_filter('.value.priority == "high" or .value.urgent == true', msg) is True

        # Both false
        msg = self.create_message({'priority': 'low', 'urgent': False})
        assert check._evaluate_filter('.value.priority == "high" or .value.urgent == true', msg) is False

    def test_complex_logical_expression(self):
        """Test complex expression with multiple AND/OR."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        # All conditions match
        msg = self.create_message({'amount': 1500, 'status': 'failed', 'tier': 'premium'})
        filter_expr = '.value.amount > 1000 and .value.status == "failed" and .value.tier == "premium"'
        assert check._evaluate_filter(filter_expr, msg) is True

        # One condition fails
        msg = self.create_message({'amount': 500, 'status': 'failed', 'tier': 'premium'})
        assert check._evaluate_filter(filter_expr, msg) is False


class TestNestedFieldAccess:
    """Test nested field access in filters."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, value_dict):
        """Helper to create a deserialized message from a value dict."""
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_nested_field_two_levels(self):
        """Test accessing nested fields (2 levels)."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'user': {'country': 'US'}})
        assert check._evaluate_filter('.value.user.country == "US"', msg) is True

        msg = self.create_message({'user': {'country': 'UK'}})
        assert check._evaluate_filter('.value.user.country == "US"', msg) is False

    def test_nested_field_three_levels(self):
        """Test accessing deeply nested fields (3 levels)."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'user': {'profile': {'subscription': {'tier': 'enterprise'}}}})
        assert check._evaluate_filter('.value.user.profile.subscription.tier == "enterprise"', msg) is True

    def test_nested_field_missing_path(self):
        """Test that missing nested fields return None and filter fails gracefully."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        # Missing intermediate field
        msg = self.create_message({'user': {}})
        assert check._evaluate_filter('.value.user.country == "US"', msg) is False

        # Missing top-level field
        msg = self.create_message({'other': 'data'})
        assert check._evaluate_filter('.value.user.country == "US"', msg) is False


class TestExistenceChecks:
    """Test existence checks (field without operator)."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, value_dict):
        """Helper to create a deserialized message from a value dict."""
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_field_exists(self):
        """Test checking if field exists."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'error': 'Some error message'})
        assert check._evaluate_filter('.value.error', msg) is True

        msg = self.create_message({'status': 'success'})
        assert check._evaluate_filter('.value.error', msg) is False

    def test_nested_field_exists(self):
        """Test checking if nested field exists."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'metadata': {'user_id': '12345'}})
        assert check._evaluate_filter('.value.metadata.user_id', msg) is True

        msg = self.create_message({'metadata': {}})
        assert check._evaluate_filter('.value.metadata.user_id', msg) is False


class TestKeyFiltering:
    """Test filtering on message keys."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, key_str, value_dict):
        """Helper to create a deserialized message with specific key and value."""
        key_bytes = key_str.encode('utf-8') if key_str else None
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=key_bytes, value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_filter_by_key(self):
        """Test filtering by message key."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message('user-12345', {'data': 'value'})
        assert check._evaluate_filter('.key == "user-12345"', msg) is True

        msg = self.create_message('user-67890', {'data': 'value'})
        assert check._evaluate_filter('.key == "user-12345"', msg) is False

    def test_filter_key_and_value(self):
        """Test filtering on both key and value."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message('user-12345', {'status': 'active'})
        assert check._evaluate_filter('.key == "user-12345" and .value.status == "active"', msg) is True

        msg = self.create_message('user-12345', {'status': 'inactive'})
        assert check._evaluate_filter('.key == "user-12345" and .value.status == "active"', msg) is False


class TestLiteralParsing:
    """Test parsing of literal values in filters."""

    def setup_method(self):
        """Setup test fixtures."""
        self.log = MagicMock()
        self.deserializer = MessageDeserializer(self.log)

    def create_message(self, value_dict):
        """Helper to create a deserialized message from a value dict."""
        value_bytes = json.dumps(value_dict).encode('utf-8')
        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)
        config = {'key_format': 'string', 'value_format': 'json', 'value_uses_schema_registry': False}
        return DeserializedMessage(kafka_msg, self.deserializer, config)

    def test_string_literal(self):
        """Test string literal parsing."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'name': 'John Doe'})
        assert check._evaluate_filter('.value.name == "John Doe"', msg) is True

    def test_number_literal(self):
        """Test number literal parsing."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'count': 42})
        assert check._evaluate_filter('.value.count == 42', msg) is True

        msg = self.create_message({'price': 99.99})
        assert check._evaluate_filter('.value.price == 99.99', msg) is True

    def test_boolean_literal(self):
        """Test boolean literal parsing."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'active': True})
        assert check._evaluate_filter('.value.active == true', msg) is True

        msg = self.create_message({'deleted': False})
        assert check._evaluate_filter('.value.deleted == false', msg) is True

    def test_null_literal(self):
        """Test null literal parsing."""
        instance = {
            'remote_config_id': 'test',
            'kafka_connect_str': 'localhost:9092',
            'read_messages': {'cluster': 'test', 'topic': 'test'},
        }
        check = KafkaActionsCheck('kafka_actions', {}, [instance])

        msg = self.create_message({'optional_field': None})
        assert check._evaluate_filter('.value.optional_field == null', msg) is True


if __name__ == '__main__':
    pytest.main([__file__, '-vv'])
