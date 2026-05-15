# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Built-in format handlers.

Thin wrappers over the module-level helpers in
``..message_deserializer`` so deserialization logic lives in one place.
"""

from __future__ import annotations

from datadog_checks.kafka_actions.formats.base import FormatHandler
from datadog_checks.kafka_actions.message_deserializer import (
    _build_avro_schema,
    _build_protobuf_schema,
    _build_protobuf_schema_from_registry,
    _deserialize_avro,
    _deserialize_bson,
    _deserialize_json,
    _deserialize_protobuf,
    _deserialize_raw,
    _deserialize_string,
)


class JsonHandler(FormatHandler):
    name = 'json'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_json(message)


class StringHandler(FormatHandler):
    name = 'string'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_string(message)


class RawHandler(FormatHandler):
    name = 'raw'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_raw(message)


class BsonHandler(FormatHandler):
    name = 'bson'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_bson(message)


class AvroHandler(FormatHandler):
    name = 'avro'

    def build_schema(self, schema_str):
        return _build_avro_schema(schema_str)

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_avro(message, schema)


class ProtobufHandler(FormatHandler):
    name = 'protobuf'

    def build_schema(self, schema_str):
        return _build_protobuf_schema(schema_str)

    def build_schema_from_registry(self, schema_str, dep_schemas):
        return _build_protobuf_schema_from_registry(schema_str, dep_schemas)

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        return _deserialize_protobuf(message, schema, uses_schema_registry)
