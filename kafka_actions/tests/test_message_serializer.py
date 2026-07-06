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

# Base64-encoded FileDescriptorSet, as used for inline protobuf schemas (value_schema/key_schema).
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

    def test_serialize_raw_format(self, serializer):
        original = b'hello world'
        encoded = base64.b64encode(original).decode('ascii')

        result = serializer.serialize_message(encoded, 'raw')
        assert result == original

    def test_serialize_string_format(self, serializer):
        result = serializer.serialize_message('hello world', 'string')
        assert result == b'hello world'

    def test_serialize_json_format(self, serializer):
        value = json.dumps({"order_id": "12345", "status": "pending"})
        result = serializer.serialize_message(value, 'json')
        assert json.loads(result.decode('utf-8')) == json.loads(value)

    def test_serialize_json_format_invalid_json_raises(self, serializer):
        with pytest.raises(ValueError, match="Failed to serialize json message"):
            serializer.serialize_message('not valid json', 'json')

    def test_serialize_bson_format(self, log, serializer):
        value = json.dumps({"order_id": "12345", "status": "pending"})
        result = serializer.serialize_message(value, 'bson')
        assert isinstance(result, bytes)

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'bson', None, False)
        assert json.loads(decoded) == {"order_id": "12345", "status": "pending"}
        assert schema_id is None

    def test_serialize_avro_inline_schema_round_trip(self, log, serializer):
        result = serializer.serialize_message(BOOK_JSON, 'avro', schema_str=AVRO_SCHEMA)
        assert isinstance(result, bytes)

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'avro', AVRO_SCHEMA, False)
        assert json.loads(decoded) == json.loads(BOOK_JSON)
        assert schema_id is None

    def test_serialize_protobuf_inline_schema_round_trip(self, log, serializer):
        result = serializer.serialize_message(BOOK_JSON, 'protobuf', schema_str=PROTOBUF_SCHEMA)
        assert isinstance(result, bytes)

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'protobuf', PROTOBUF_SCHEMA, False)
        assert json.loads(decoded) == BOOK_DICT_AFTER_PROTOBUF_ROUND_TRIP
        assert schema_id is None

    @pytest.mark.parametrize("fmt", ["avro", "protobuf"])
    def test_serialize_schema_format_without_schema_raises(self, serializer, fmt):
        with pytest.raises(ValueError, match=f"Failed to serialize {fmt} message"):
            serializer.serialize_message(BOOK_JSON, fmt)

    def test_serialize_avro_schema_registry_round_trip(self, log, serializer):
        schema_registry = MagicMock()
        schema_registry.get_schema.return_value = (AVRO_SCHEMA, 'AVRO', [])
        serializer.schema_registry = schema_registry

        result = serializer.serialize_message(BOOK_JSON, 'avro', uses_schema_registry=True, schema_id=350)

        assert result[:5] == b'\x00\x00\x00\x01\x5e'
        schema_registry.get_schema.assert_called_once_with(350)

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'avro', AVRO_SCHEMA, True)
        assert json.loads(decoded) == json.loads(BOOK_JSON)
        assert schema_id == 350

    def test_serialize_protobuf_schema_registry_round_trip(self, log, serializer):
        schema_registry = MagicMock()
        schema_registry.get_schema.return_value = (PROTOBUF_SCHEMA_REGISTRY, 'PROTOBUF', [])
        serializer.schema_registry = schema_registry

        result = serializer.serialize_message(BOOK_JSON, 'protobuf', uses_schema_registry=True, schema_id=350)

        # magic byte + schema id + message indices (empty array -> single zero byte)
        assert result[:6] == b'\x00\x00\x00\x01\x5e\x00'

        deserializer = MessageDeserializer(log)
        decoded, schema_id = deserializer.deserialize_message(result, 'protobuf', PROTOBUF_SCHEMA, True)
        assert json.loads(decoded) == BOOK_DICT_AFTER_PROTOBUF_ROUND_TRIP
        assert schema_id == 350

    def test_serialize_avro_schema_registry_fetch_is_cached(self, serializer):
        schema_registry = MagicMock()
        schema_registry.get_schema.return_value = (AVRO_SCHEMA, 'AVRO', [])
        serializer.schema_registry = schema_registry

        serializer.serialize_message(BOOK_JSON, 'avro', uses_schema_registry=True, schema_id=350)
        serializer.serialize_message(BOOK_JSON, 'avro', uses_schema_registry=True, schema_id=350)

        schema_registry.get_schema.assert_called_once_with(350)

    def test_serialize_avro_inline_schema_build_is_cached(self, serializer, monkeypatch):
        import datadog_checks.kafka_actions.message_serializer as message_serializer_module

        build_calls = []
        original_build_schema_for_format = message_serializer_module.build_schema_for_format

        def counting_build_schema_for_format(*args, **kwargs):
            build_calls.append(args[1] if len(args) > 1 else kwargs.get('schema_str'))
            return original_build_schema_for_format(*args, **kwargs)

        monkeypatch.setattr(message_serializer_module, "build_schema_for_format", counting_build_schema_for_format)

        serializer.serialize_message(BOOK_JSON, 'avro', schema_str=AVRO_SCHEMA)
        serializer.serialize_message(BOOK_JSON, 'avro', schema_str=AVRO_SCHEMA)

        assert len(build_calls) == 1

    def test_serialize_schema_registry_without_registry_raises(self, serializer):
        with pytest.raises(ValueError, match="no Schema Registry is configured"):
            serializer.serialize_message(BOOK_JSON, 'avro', uses_schema_registry=True, schema_id=350)

    def test_serialize_schema_registry_without_schema_id_raises(self, serializer):
        serializer.schema_registry = MagicMock()

        with pytest.raises(ValueError, match="requires a schema_id"):
            serializer.serialize_message(BOOK_JSON, 'avro', uses_schema_registry=True)
