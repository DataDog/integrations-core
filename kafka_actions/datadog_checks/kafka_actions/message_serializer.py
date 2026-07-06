# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Message serialization for kafka_actions' produce_message action.

Mirrors the format set supported by :mod:`.message_deserializer` (json,
string, raw, bson, avro, protobuf) so a message produced through one of
these formats can be read back with ``read_messages`` using the same
format/schema configuration.
"""

from __future__ import annotations

import base64
import hashlib
import json
from io import BytesIO

import bson
from bson.json_util import loads as bson_json_loads
from fastavro import schemaless_writer
from google.protobuf import json_format as protobuf_json_format

from .schema_helpers import (
    REGISTRY_TYPE_MAP,
    SCHEMA_FORMATS,
    SCHEMA_REGISTRY_MAGIC_BYTE,
    build_avro_schema,
    build_protobuf_schema,
    build_protobuf_schema_from_registry,
    get_protobuf_message_class,
    write_protobuf_message_indices,
)


class MessageSerializer:
    """Serializes a config-supplied string into Kafka message bytes for produce_message."""

    def __init__(self, log, schema_registry=None):
        self.log = log
        self.schema_registry = schema_registry
        self._registry_schema_cache: dict[tuple[str, int], tuple[object, str]] = {}
        self._schema_cache: dict[tuple[str, str], object] = {}

    def serialize_message(
        self,
        value: str,
        format_type: str = 'raw',
        schema_str: str | None = None,
        uses_schema_registry: bool = False,
        schema_id: int | None = None,
    ) -> bytes:
        """Serialize ``value`` (a config-supplied string) into message bytes.

        Args:
            value: The configured key/value string. Its expected shape depends
                on format_type: base64 for 'raw', plain text for 'string',
                JSON text for 'json'/'bson'/'avro'/'protobuf'.
            format_type: 'raw', 'string', 'json', 'bson', 'avro', or 'protobuf'.
            schema_str: Inline schema definition for 'avro'/'protobuf'. Ignored
                when uses_schema_registry is True.
            uses_schema_registry: Whether to fetch the schema from the Schema
                Registry by schema_id and frame the payload with the Confluent
                wire format (magic byte + 4-byte schema ID).
            schema_id: Schema Registry schema ID to embed. Required when
                uses_schema_registry is True.

        Returns:
            Serialized message bytes, ready to hand to the Kafka producer.
        """
        if format_type == 'raw':
            return base64.b64decode(value)

        actual_format = format_type
        schema = None

        if format_type in SCHEMA_FORMATS or uses_schema_registry:
            if uses_schema_registry:
                if self.schema_registry is None:
                    raise ValueError("uses_schema_registry is set but no Schema Registry is configured")
                if schema_id is None:
                    raise ValueError("uses_schema_registry requires a schema_id to embed in the message")
                schema, actual_format = self._fetch_and_build_schema(schema_id, format_type)
            elif schema_str:
                schema = self._build_schema(format_type, schema_str)

        try:
            payload = self._serialize_bytes(value, actual_format, schema)
        except Exception as e:
            raise ValueError(f"Failed to serialize {format_type} message: {e}") from e

        if uses_schema_registry:
            header = SCHEMA_REGISTRY_MAGIC_BYTE.to_bytes(1, 'big') + schema_id.to_bytes(4, 'big')
            if actual_format == 'protobuf':
                header += write_protobuf_message_indices([])
            return header + payload

        return payload

    def _serialize_bytes(self, value: str, format_type: str, schema) -> bytes:
        if format_type == 'protobuf':
            return self._serialize_protobuf(value, schema)
        elif format_type == 'avro':
            return self._serialize_avro(value, schema)
        elif format_type == 'bson':
            return self._serialize_bson(value)
        elif format_type == 'string':
            return value.encode('utf-8')
        else:  # json (and any registry JSON schema type)
            return self._serialize_json(value)

    def _serialize_json(self, value: str) -> bytes:
        """Validate ``value`` is JSON text, then encode it as UTF-8 bytes."""
        json.loads(value)
        return value.encode('utf-8')

    def _serialize_bson(self, value: str) -> bytes:
        """Encode BSON-extended-JSON text (as produced by bson.json_util.dumps) to BSON bytes."""
        doc = bson_json_loads(value)
        return bson.encode(doc)

    def _serialize_avro(self, value: str, schema) -> bytes:
        if schema is None:
            raise ValueError("Avro schema is required")

        record = json.loads(value)
        bio = BytesIO()
        schemaless_writer(bio, schema, record)
        return bio.getvalue()

    def _serialize_protobuf(self, value: str, schema_info) -> bytes:
        if schema_info is None:
            raise ValueError("Protobuf schema is required")

        message_class = get_protobuf_message_class(schema_info, [0])
        instance = message_class()
        protobuf_json_format.Parse(value, instance)
        return instance.SerializeToString()

    def _fetch_and_build_schema(self, schema_id: int, format_type: str):
        """Fetch schema from the registry by ID and build it, caching by (format_type, schema_id).

        Returns:
            Tuple of (schema_object, actual_format), where actual_format is
            the format reported by the registry (may differ from format_type).
        """
        cache_key = (format_type, schema_id)
        cached = self._registry_schema_cache.get(cache_key)
        if cached is not None:
            return cached

        schema_str, schema_type, dep_schemas = self.schema_registry.get_schema(schema_id)
        actual_format = REGISTRY_TYPE_MAP.get(schema_type, format_type)

        if actual_format == 'protobuf':
            schema = build_protobuf_schema_from_registry(schema_str, dep_schemas)
        elif actual_format == 'avro':
            schema = build_avro_schema(schema_str)
        else:
            schema = None

        result = (schema, actual_format)
        self._registry_schema_cache[cache_key] = result
        return result

    def _build_schema(self, format_type: str, schema_str: str):
        """Build a schema from an inline schema string, caching by (format_type, schema hash)."""
        cache_key = (format_type, hashlib.sha256(schema_str.encode('utf-8')).hexdigest())
        if cache_key in self._schema_cache:
            return self._schema_cache[cache_key]

        if format_type == 'protobuf':
            schema = build_protobuf_schema(schema_str)
        elif format_type == 'avro':
            schema = build_avro_schema(schema_str)
        else:
            schema = None

        self._schema_cache[cache_key] = schema
        return schema
