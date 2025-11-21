# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for message deserialization."""

import json
from unittest.mock import MagicMock

import pytest

from datadog_checks.kafka_actions.message_deserializer import DeserializedMessage, MessageDeserializer


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
        return (1, 1732128000000)  # (timestamp_type, timestamp_ms)

    def headers(self):
        return None


class TestMessageDeserializer:
    """Test MessageDeserializer class."""

    def test_deserialize_string_key_with_schema_registry_json_value(self):
        """Test deserializing a message with string key and Schema Registry JSON value."""
        # Setup
        log = MagicMock()
        deserializer = MessageDeserializer(log, schema_registry_client=None)

        # Key (raw string bytes)
        key_bytes = b'key-35457'

        # Value (Schema Registry wire format: magic byte + schema_id + JSON)
        # Magic byte: 0x00
        # Schema ID: 0x00000001 (1 in big-endian)
        # JSON payload
        json_payload = {
            "id": 35457,
            "timestamp": "2025-11-20T18:19:40.135349",
            "message": "Hello from producer! Message #35457",
            "data": {"value": 354570, "status": "active"},
        }
        json_bytes = json.dumps(json_payload).encode('utf-8')
        value_bytes = b'\x00\x00\x00\x00\x01' + json_bytes

        # Create mock Kafka message
        kafka_msg = MockKafkaMessage(key=key_bytes, value=value_bytes)

        # Configuration
        config = {
            'key_format': 'string',  # String format for simple string keys
            'key_uses_schema_registry': False,
            'value_format': 'json',  # JSON format
            'value_uses_schema_registry': True,  # With Schema Registry prefix
        }

        # Create DeserializedMessage
        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        # Test key deserialization
        key = deserialized_msg.key
        assert key == 'key-35457', f"Expected 'key-35457', got {key}"

        # Test value deserialization
        value = deserialized_msg.value
        assert isinstance(value, dict), f"Expected dict, got {type(value)}"
        assert value['id'] == 35457
        assert value['message'] == "Hello from producer! Message #35457"
        assert value['data']['value'] == 354570
        assert value['data']['status'] == 'active'

        # Test schema ID extraction
        assert deserialized_msg.value_schema_id == 1, f"Expected schema_id=1, got {deserialized_msg.value_schema_id}"
        assert deserialized_msg.key_schema_id is None

        # Test to_dict
        msg_dict = deserialized_msg.to_dict()
        assert msg_dict['key'] == 'key-35457'
        assert msg_dict['value']['id'] == 35457
        assert msg_dict['topic'] == 'test-topic'
        assert msg_dict['partition'] == 0
        assert msg_dict['offset'] == 0

    def test_deserialize_empty_key(self):
        """Test deserializing a message with empty key."""
        log = MagicMock()
        deserializer = MessageDeserializer(log, schema_registry_client=None)

        # Empty key, value with Schema Registry format
        key_bytes = None
        json_payload = {"test": "value"}
        json_bytes = json.dumps(json_payload).encode('utf-8')
        value_bytes = b'\x00\x00\x00\x00\x01' + json_bytes

        kafka_msg = MockKafkaMessage(key=key_bytes, value=value_bytes)

        config = {
            'key_format': 'string',
            'key_uses_schema_registry': False,
            'value_format': 'json',
            'value_uses_schema_registry': True,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        # Empty key should be None
        assert deserialized_msg.key is None

        # Value should deserialize correctly
        value = deserialized_msg.value
        assert value['test'] == 'value'

    def test_deserialize_json_without_schema_registry_auto_detect(self):
        """Test auto-detection of Schema Registry format when uses_schema_registry=False."""
        log = MagicMock()
        deserializer = MessageDeserializer(log, schema_registry_client=None)

        # Value with Schema Registry format, but uses_schema_registry=False
        # Should auto-detect and strip prefix
        json_payload = {"auto": "detect"}
        json_bytes = json.dumps(json_payload).encode('utf-8')
        value_bytes = b'\x00\x00\x00\x00\x02' + json_bytes

        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)

        config = {
            'key_format': 'string',
            'key_uses_schema_registry': False,
            'value_format': 'json',
            'value_uses_schema_registry': False,  # False, but should auto-detect
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        # Should auto-detect Schema Registry format
        value = deserialized_msg.value
        assert value['auto'] == 'detect'
        assert deserialized_msg.value_schema_id == 2

    def test_deserialize_plain_json_without_schema_registry(self):
        """Test deserializing plain JSON without Schema Registry prefix."""
        log = MagicMock()
        deserializer = MessageDeserializer(log, schema_registry_client=None)

        # Plain JSON (no Schema Registry prefix)
        json_payload = {"plain": "json"}
        value_bytes = json.dumps(json_payload).encode('utf-8')

        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)

        config = {
            'key_format': 'string',
            'key_uses_schema_registry': False,
            'value_format': 'json',
            'value_uses_schema_registry': False,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        value = deserialized_msg.value
        assert value['plain'] == 'json'
        assert deserialized_msg.value_schema_id is None

    def test_deserialize_string_format(self):
        """Test that string format returns the raw string value."""
        log = MagicMock()
        deserializer = MessageDeserializer(log, schema_registry_client=None)

        key_bytes = b'simple-string-key'
        value_bytes = b'simple-string-value'

        kafka_msg = MockKafkaMessage(key=key_bytes, value=value_bytes)

        config = {
            'key_format': 'string',
            'key_uses_schema_registry': False,
            'value_format': 'string',
            'value_uses_schema_registry': False,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        assert deserialized_msg.key == 'simple-string-key'
        assert deserialized_msg.value == 'simple-string-value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
