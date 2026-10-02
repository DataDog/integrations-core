# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Message serialization for kafka_actions' produce_message action.

Without a Schema Registry, key/value are always base64-encoded raw bytes.
With a Schema Registry, the wire format (avro/protobuf/json) is whatever the
latest registered schema for the subject reports, framed with the Confluent
wire format so a message produced this way can be read back with
``read_messages`` against the same registry.
"""

from __future__ import annotations

import base64
import json
from io import BytesIO

from fastavro import schemaless_writer
from google.protobuf import json_format as protobuf_json_format

from .schema_helpers import (
    REGISTRY_TYPE_MAP,
    SCHEMA_REGISTRY_MAGIC_BYTE,
    build_schema_for_format,
    get_protobuf_message_class,
    write_protobuf_message_indices,
)


class MessageSerializer:
    """Serializes a config-supplied string into Kafka message bytes for produce_message."""

    def __init__(self, log, schema_registry=None):
        self.log = log
        self.schema_registry = schema_registry
        self._registry_schema_cache: dict[int, tuple[object, str, int]] = {}

    def serialize_message(
        self,
        value: str,
        uses_schema_registry: bool = False,
        schema_subject: str | None = None,
    ) -> bytes:
        """Serialize ``value`` (a config-supplied string) into message bytes.

        Without a Schema Registry, ``value`` is base64-encoded and decoded as-is.
        With one, the latest schema registered for schema_subject is resolved and
        its reported type (avro/protobuf/json) determines how value is parsed and
        framed with the Confluent wire format (magic byte + 4-byte schema ID).
        """
        if not uses_schema_registry:
            try:
                return base64.b64decode(value)
            except Exception as e:
                raise ValueError(f"Failed to decode base64 value for subject '{schema_subject}': {e}") from e

        if self.schema_registry is None:
            raise ValueError("uses_schema_registry is set but no Schema Registry is configured")
        if not schema_subject:
            raise ValueError("uses_schema_registry requires a schema_subject to resolve")

        try:
            schema, actual_format, schema_id = self._fetch_and_build_schema(schema_subject)
            payload = self._serialize_bytes(value, actual_format, schema)
        except Exception as e:
            raise ValueError(f"Failed to serialize message for subject '{schema_subject}': {e}") from e

        header = SCHEMA_REGISTRY_MAGIC_BYTE.to_bytes(1, 'big') + schema_id.to_bytes(4, 'big')
        if actual_format == 'protobuf':
            header += write_protobuf_message_indices([])
        return header + payload

    def _serialize_bytes(self, value: str, format_type: str, schema) -> bytes:
        if format_type == 'protobuf':
            return self._serialize_protobuf(value, schema)
        elif format_type == 'avro':
            return self._serialize_avro(value, schema)
        else:
            return self._serialize_json(value)

    def _serialize_json(self, value: str) -> bytes:
        """Validate ``value`` is JSON text, then encode it as UTF-8 bytes."""
        json.loads(value)
        return value.encode('utf-8')

    def _serialize_avro(self, value: str, schema) -> bytes:
        record = json.loads(value)
        bio = BytesIO()
        schemaless_writer(bio, schema, record)
        return bio.getvalue()

    def _serialize_protobuf(self, value: str, schema_info) -> bytes:
        message_class = get_protobuf_message_class(schema_info, [0])
        instance = message_class()
        protobuf_json_format.Parse(value, instance)
        return instance.SerializeToString()

    def _fetch_and_build_schema(self, schema_subject: str) -> tuple[object, str, int]:
        """Resolve the latest schema for schema_subject and build it, caching by schema_id.

        The subject -> schema_id lookup is never cached (a new version may be registered
        between calls), but the built schema is cached forever once a given schema_id is seen.

        Returns:
            Tuple of (schema_object, actual_format, schema_id), where actual_format is
            the format reported by the registry ('avro', 'protobuf', or 'json').
        """
        schema_id = self.schema_registry.get_latest_schema_id(schema_subject)

        cached = self._registry_schema_cache.get(schema_id)
        if cached is not None:
            return cached

        schema_str, schema_type, dep_schemas = self.schema_registry.get_schema(schema_id)
        if schema_type not in REGISTRY_TYPE_MAP:
            raise ValueError(f"Unsupported schema type '{schema_type}' from Schema Registry")
        actual_format = REGISTRY_TYPE_MAP[schema_type]

        schema = build_schema_for_format(actual_format, schema_str, from_registry=True, dep_schemas=dep_schemas)

        result = (schema, actual_format, schema_id)
        self._registry_schema_cache[schema_id] = result
        return result
