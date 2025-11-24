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
        deserializer = MessageDeserializer(log)

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
        deserializer = MessageDeserializer(log)

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
        deserializer = MessageDeserializer(log)

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
        deserializer = MessageDeserializer(log)

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
        deserializer = MessageDeserializer(log)

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

    def test_deserialize_bson_format(self):
        """Test BSON message deserialization."""
        log = MagicMock()
        deserializer = MessageDeserializer(log)

        # Create BSON data
        from bson import encode as bson_encode

        bson_data = {'user_id': 12345, 'name': 'John Doe', 'active': True, 'score': 98.5}
        value_bytes = bson_encode(bson_data)

        kafka_msg = MockKafkaMessage(key=b'test-key', value=value_bytes)

        config = {
            'key_format': 'string',
            'key_uses_schema_registry': False,
            'value_format': 'bson',
            'value_uses_schema_registry': False,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)

        # BSON deserialization returns a dict
        assert isinstance(deserialized_msg.value, dict)
        assert deserialized_msg.value['user_id'] == 12345
        assert deserialized_msg.value['name'] == 'John Doe'
        assert deserialized_msg.value['active'] is True
        assert deserialized_msg.value['score'] == 98.5

    def test_avro_explicit_schema_registry_configuration(self):
        """Test that explicit Avro schema registry configuration is enforced."""
        log = MagicMock()
        deserializer = MessageDeserializer(log)

        # Avro schema for Book (isbn: long, title: string, author: string)
        avro_schema = (
            '{"type": "record", "name": "Book", "namespace": "com.book", '
            '"fields": [{"name": "isbn", "type": "long"}, {"name": "title", "type": "string"}, '
            '{"name": "author", "type": "string"}]}'
        )

        # Avro message WITHOUT Schema Registry format
        # Book: isbn=9780134190440, title="The Go Programming Language", author="Alan Donovan"
        avro_message_no_sr = b'\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'

        # Avro message WITH Schema Registry format (magic byte 0x00 + schema ID 350 = 0x015E)
        avro_message_with_sr = (
            b'\x00\x00\x00\x01\x5e\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
        )

        key_bytes = b'{"name": "Peter Parker"}'

        # Test 1: uses_schema_registry=False with plain Avro message - should succeed
        result = deserializer.deserialize_message(avro_message_no_sr, 'avro', avro_schema, False)
        assert result[0] is not None, "Should succeed when uses_schema_registry=False"
        assert result[1] is None, "Should have no schema ID"
        assert 'The Go Programming Language' in result[0]

        # Test 2: uses_schema_registry=True with plain Avro message - should fail (missing magic byte)
        result = deserializer.deserialize_message(avro_message_no_sr, 'avro', avro_schema, True)
        assert result[0].startswith("<deserialization error:"), "Should fail when uses_schema_registry=True"
        assert result[1] is None

        # Test 3: uses_schema_registry=True with Schema Registry format - should succeed
        result = deserializer.deserialize_message(avro_message_with_sr, 'avro', avro_schema, True)
        assert result[0] is not None, "Should succeed when uses_schema_registry=True with SR format"
        assert result[1] == 350, "Should extract schema ID 350"
        assert 'The Go Programming Language' in result[0]

        # Test 4: Wrong magic byte - should fail
        wrong_magic_byte = (
            b'\x01\x00\x00\x01\x5e\xd0\xf5\xe4\xd6\xa3\xb9\x046The Go Programming Language\x18Alan Donovan'
        )
        result = deserializer.deserialize_message(wrong_magic_byte, 'avro', avro_schema, True)
        assert result[0].startswith("<deserialization error:"), "Should fail with wrong magic byte"

        # Test 5: Message too short (less than 5 bytes) - should fail
        too_short = b'\x00\x00\x01'
        result = deserializer.deserialize_message(too_short, 'avro', avro_schema, True)
        assert result[0].startswith("<deserialization error:"), "Should fail when message too short"

        # Test 6: Test through DeserializedMessage wrapper
        kafka_msg = MockKafkaMessage(key=key_bytes, value=avro_message_no_sr)
        config = {
            'key_format': 'json',
            'key_uses_schema_registry': False,
            'value_format': 'avro',
            'value_schema': avro_schema,
            'value_uses_schema_registry': False,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)
        assert isinstance(deserialized_msg.value, dict)
        assert deserialized_msg.value['isbn'] == 9780134190440
        assert deserialized_msg.value['title'] == 'The Go Programming Language'
        assert deserialized_msg.value['author'] == 'Alan Donovan'
        assert deserialized_msg.value_schema_id is None

        # Test 7: With Schema Registry format through DeserializedMessage
        kafka_msg_sr = MockKafkaMessage(key=key_bytes, value=avro_message_with_sr)
        config_sr = {
            'key_format': 'json',
            'key_uses_schema_registry': False,
            'value_format': 'avro',
            'value_schema': avro_schema,
            'value_uses_schema_registry': True,
        }

        deserialized_msg_sr = DeserializedMessage(kafka_msg_sr, deserializer, config_sr)
        assert isinstance(deserialized_msg_sr.value, dict)
        assert deserialized_msg_sr.value['title'] == 'The Go Programming Language'
        assert deserialized_msg_sr.value_schema_id == 350

    def test_protobuf_explicit_schema_registry_configuration(self):
        """Test that explicit Protobuf schema registry configuration is enforced."""
        log = MagicMock()
        deserializer = MessageDeserializer(log)

        # Protobuf schema (base64-encoded FileDescriptorSet for Book with isbn, title, author)
        protobuf_schema = (
            'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
            'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
        )

        # Protobuf message WITHOUT Schema Registry format
        # Book: isbn=9780134190440, title="The Go Programming Language", author="Alan Donovan"
        protobuf_message_no_sr = (
            b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
            b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
        )

        # Protobuf message WITH Schema Registry format (magic byte 0x00 + schema ID 350 = 0x015E)
        protobuf_message_with_sr = (
            b'\x00\x00\x00\x01\x5e'
            b'\x08\xe8\xba\xb2\xeb\xd1\x9c\x02\x12\x1b\x54\x68\x65\x20\x47\x6f\x20\x50\x72\x6f\x67\x72\x61\x6d\x6d\x69\x6e\x67\x20\x4c\x61\x6e\x67\x75\x61\x67\x65'
            b'\x1a\x0c\x41\x6c\x61\x6e\x20\x44\x6f\x6e\x6f\x76\x61\x6e'
        )

        key_bytes = b'{"name": "Peter Parker"}'

        # Test 1: uses_schema_registry=False with plain Protobuf message - should succeed
        result = deserializer.deserialize_message(protobuf_message_no_sr, 'protobuf', protobuf_schema, False)
        assert result[0] is not None, "Protobuf should succeed when uses_schema_registry=False"
        assert result[1] is None, "Should have no schema ID"
        assert 'The Go Programming Language' in result[0]

        # Test 2: uses_schema_registry=True with plain Protobuf message - should fail
        result = deserializer.deserialize_message(protobuf_message_no_sr, 'protobuf', protobuf_schema, True)
        assert result[0].startswith("<deserialization error:"), (
            "Protobuf should fail when uses_schema_registry=True but no SR format"
        )
        assert result[1] is None

        # Test 3: uses_schema_registry=True with Schema Registry format - should succeed
        result = deserializer.deserialize_message(protobuf_message_with_sr, 'protobuf', protobuf_schema, True)
        assert result[0] is not None, "Protobuf should succeed when uses_schema_registry=True with SR format"
        assert result[1] == 350, "Should extract schema ID 350"
        assert 'The Go Programming Language' in result[0]

        # Test 4: Wrong magic byte - should fail
        wrong_magic_byte = b'\x01\x00\x00\x01\x5e' + protobuf_message_no_sr
        result = deserializer.deserialize_message(wrong_magic_byte, 'protobuf', protobuf_schema, True)
        assert result[0].startswith("<deserialization error:"), "Should fail with wrong magic byte"

        # Test 5: Message too short (less than 5 bytes) - should fail
        too_short = b'\x00\x00\x01'
        result = deserializer.deserialize_message(too_short, 'protobuf', protobuf_schema, True)
        assert result[0].startswith("<deserialization error:"), "Should fail when message too short"

        # Test 6: Test through DeserializedMessage wrapper
        kafka_msg = MockKafkaMessage(key=key_bytes, value=protobuf_message_no_sr)
        config = {
            'key_format': 'json',
            'key_uses_schema_registry': False,
            'value_format': 'protobuf',
            'value_schema': protobuf_schema,
            'value_uses_schema_registry': False,
        }

        deserialized_msg = DeserializedMessage(kafka_msg, deserializer, config)
        assert isinstance(deserialized_msg.value, dict)
        # Note: Protobuf JSON conversion uses camelCase for field names
        assert deserialized_msg.value['isbn'] == '9780134190440'  # int64 becomes string in JSON
        assert deserialized_msg.value['title'] == 'The Go Programming Language'
        assert deserialized_msg.value['author'] == 'Alan Donovan'
        assert deserialized_msg.value_schema_id is None

        # Test 7: With Schema Registry format through DeserializedMessage
        kafka_msg_sr = MockKafkaMessage(key=key_bytes, value=protobuf_message_with_sr)
        config_sr = {
            'key_format': 'json',
            'key_uses_schema_registry': False,
            'value_format': 'protobuf',
            'value_schema': protobuf_schema,
            'value_uses_schema_registry': True,
        }

        deserialized_msg_sr = DeserializedMessage(kafka_msg_sr, deserializer, config_sr)
        assert isinstance(deserialized_msg_sr.value, dict)
        assert deserialized_msg_sr.value['title'] == 'The Go Programming Language'
        assert deserialized_msg_sr.value_schema_id == 350


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
