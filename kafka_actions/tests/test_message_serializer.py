# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for message serialization."""

import base64
import json
from unittest.mock import MagicMock

import pytest
from google.protobuf import descriptor_pb2

from datadog_checks.kafka_actions.message_deserializer import MessageDeserializer
from datadog_checks.kafka_actions.message_serializer import MessageSerializer

from . import common

pytestmark = [pytest.mark.unit]

AVRO_SCHEMA = common.BOOK_AVRO_SCHEMA

# Base64-encoded FileDescriptorSet, as used by the Schema Registry's inline test fixtures.
PROTOBUF_SCHEMA = (
    'CmoKDHNjaGVtYS5wcm90bxIIY29tLmJvb2siSAoEQm9vaxISCgRpc2JuGAEgASgDUgRpc2Ju'
    'EhQKBXRpdGxlGAIgASgJUgV0aXRsZRIWCgZhdXRob3IYAyABKAlSBmF1dGhvcmIGcHJvdG8z'
)

# The Schema Registry's ?format=serialized endpoint returns a single base64-encoded
# FileDescriptorProto rather than a FileDescriptorSet, so derive that form for the
# schema-registry round-trip test.
book_descriptor_set = descriptor_pb2.FileDescriptorSet()
book_descriptor_set.ParseFromString(base64.b64decode(PROTOBUF_SCHEMA))
PROTOBUF_SCHEMA_REGISTRY = base64.b64encode(book_descriptor_set.file[0].SerializeToString()).decode('ascii')

BOOK_JSON = json.dumps(common.BOOK)
# proto3 JSON encodes int64 fields as strings, so round-tripped isbn comes back as a string.
BOOK_DICT_AFTER_PROTOBUF_ROUND_TRIP = {
    "isbn": "9780134190440",
    "title": "The Go Programming Language",
    "author": "Alan Donovan",
}


@pytest.fixture
def log():
    return MagicMock()


@pytest.fixture
def serializer(log):
    return MessageSerializer(log)


class TestMessageSerializer:
    """Test MessageSerializer class."""

    def test_serialize_raw(self, serializer):
        original = b'hello world'
        encoded = base64.b64encode(original).decode('ascii')

        result = serializer.serialize_message(encoded)
        assert result == original

    def test_serialize_avro_schema_registry_round_trip(self, log, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = (AVRO_SCHEMA, 'AVRO', [])
        serializer.schema_registry = schema_registry

        result = serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')

        assert result[:5] == b'\x00\x00\x00\x01\x5e'
        schema_registry.get_latest_schema_id.assert_called_once_with('books-value')
        schema_registry.get_schema.assert_called_once_with(350)

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'avro', AVRO_SCHEMA, True)
        assert json.loads(decoded) == json.loads(BOOK_JSON)
        assert schema_id == 350

    def test_serialize_protobuf_schema_registry_round_trip(self, log, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = (PROTOBUF_SCHEMA_REGISTRY, 'PROTOBUF', [])
        serializer.schema_registry = schema_registry

        result = serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')

        # magic byte + schema id + message indices (empty array -> single zero byte)
        assert result[:6] == b'\x00\x00\x00\x01\x5e\x00'

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'protobuf', PROTOBUF_SCHEMA, True)
        assert json.loads(decoded) == BOOK_DICT_AFTER_PROTOBUF_ROUND_TRIP
        assert schema_id == 350

    def test_serialize_json_schema_registry_round_trip(self, log, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = ('{}', 'JSON', [])
        serializer.schema_registry = schema_registry

        value = json.dumps({"order_id": "12345", "status": "pending"})
        result = serializer.serialize_message(value, uses_schema_registry=True, schema_subject='orders-value')

        assert result[:5] == b'\x00\x00\x00\x01\x5e'

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'json', None, True)
        assert json.loads(decoded) == json.loads(value)
        assert schema_id == 350

    def test_serialize_avro_schema_registry_fetch_is_cached(self, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = (AVRO_SCHEMA, 'AVRO', [])
        serializer.schema_registry = schema_registry

        serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')
        serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')

        # The subject -> id lookup always re-runs (a new version may have been registered)...
        assert schema_registry.get_latest_schema_id.call_count == 2
        # ...but the schema itself, once fetched for a given id, is cached.
        schema_registry.get_schema.assert_called_once_with(350)

    def test_serialize_schema_registry_without_registry_raises(self, serializer):
        with pytest.raises(ValueError, match="no Schema Registry is configured"):
            serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')

    def test_serialize_schema_registry_without_schema_subject_raises(self, serializer):
        serializer.schema_registry = MagicMock()

        with pytest.raises(ValueError, match="requires a schema_subject"):
            serializer.serialize_message(BOOK_JSON, uses_schema_registry=True)

    def test_serialize_avro_schema_registry_invalid_json_raises(self, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = (AVRO_SCHEMA, 'AVRO', [])
        serializer.schema_registry = schema_registry

        with pytest.raises(ValueError, match="Failed to serialize message for subject 'books-value'"):
            serializer.serialize_message('not valid json', uses_schema_registry=True, schema_subject='books-value')

    def test_serialize_schema_registry_unsupported_schema_type_raises(self, serializer):
        schema_registry = MagicMock()
        schema_registry.get_latest_schema_id.return_value = 350
        schema_registry.get_schema.return_value = ('<xml/>', 'XML', [])
        serializer.schema_registry = schema_registry

        with pytest.raises(ValueError, match="Unsupported schema type 'XML'"):
            serializer.serialize_message(BOOK_JSON, uses_schema_registry=True, schema_subject='books-value')
