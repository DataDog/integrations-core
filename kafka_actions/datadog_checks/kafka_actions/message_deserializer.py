# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Message deserialization for Kafka messages.

Format handlers and compression codecs are pluggable via the
``datadog_kafka_actions.formats`` and ``datadog_kafka_actions.compressions``
entry-point groups. This wheel ships built-in handlers for
json/string/raw/bson/avro/protobuf; compression codecs are provided by
plugin wheels (none ship in core).
"""

from __future__ import annotations

import base64
import datetime
import decimal
import hashlib
import json
import uuid

from google.protobuf import (
    any_pb2,
    api_pb2,
    descriptor_pb2,
    duration_pb2,
    empty_pb2,
    field_mask_pb2,
    source_context_pb2,
    struct_pb2,
    timestamp_pb2,
    type_pb2,
    wrappers_pb2,
)

from .compression import get_codec as _get_compression_codec
from .formats import get_handler as _get_format_handler
from .formats.registry import register_handler as _register_handler

SCHEMA_REGISTRY_MAGIC_BYTE = 0x00

_WELL_KNOWN_TYPE_MODULES = (
    any_pb2,
    duration_pb2,
    empty_pb2,
    field_mask_pb2,
    source_context_pb2,
    struct_pb2,
    timestamp_pb2,
    wrappers_pb2,
    type_pb2,
    api_pb2,
)


def _preload_well_known_types(pool):
    """Add google/protobuf/*.proto well-known types to a fresh DescriptorPool."""
    for module in _WELL_KNOWN_TYPE_MODULES:
        file_name = module.DESCRIPTOR.name
        try:
            pool.FindFileByName(file_name)
            continue
        except KeyError:
            pass
        fd_proto = descriptor_pb2.FileDescriptorProto()
        module.DESCRIPTOR.CopyToProto(fd_proto)
        pool.Add(fd_proto)


class _AvroJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles types returned by fastavro for Avro logical types."""

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('ascii')
        return super().default(obj)


def _read_varint(data):
    shift = 0
    result = 0
    bytes_read = 0
    for byte in data:
        bytes_read += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            return result, bytes_read
        shift += 7
    raise ValueError("Incomplete varint")


def read_protobuf_message_indices(payload):
    """Read the Confluent Protobuf message indices array after the schema ID."""
    array_len, bytes_read = _read_varint(payload)
    payload = payload[bytes_read:]
    indices = []
    for _ in range(array_len):
        index, bytes_read = _read_varint(payload)
        indices.append(index)
        payload = payload[bytes_read:]
    return indices, payload


def get_protobuf_message_class(schema_info, message_indices):
    from google.protobuf import message_factory

    pool, descriptor_set = schema_info
    file_descriptor = descriptor_set.file[0]
    message_descriptor_proto = file_descriptor.message_type[message_indices[0]]
    package = file_descriptor.package
    name_parts = [message_descriptor_proto.name]

    current_proto = message_descriptor_proto
    for idx in message_indices[1:]:
        current_proto = current_proto.nested_type[idx]
        name_parts.append(current_proto.name)

    full_name = f"{package}.{'.'.join(name_parts)}" if package else '.'.join(name_parts)
    message_descriptor = pool.FindMessageTypeByName(full_name)
    return message_factory.GetMessageClass(message_descriptor)


def _deserialize_json(message):
    if not message:
        return None
    decoded = message.decode('utf-8').strip()
    if not decoded:
        return None
    json.loads(decoded)
    return decoded


def _deserialize_string(message):
    if not message:
        return None
    decoded = message.decode('utf-8')
    if not decoded:
        return None
    return json.dumps(decoded)


def _deserialize_raw(message):
    if not message:
        return None
    return json.dumps(base64.b64encode(message).decode('ascii'))


def _deserialize_bson(message):
    if not message:
        return None
    from bson import decode as bson_decode
    from bson.json_util import dumps as bson_dumps

    try:
        return bson_dumps(bson_decode(message))
    except Exception as e:
        raise ValueError(f"Failed to deserialize BSON message: {e}")


def _deserialize_avro(message, schema):
    if not message:
        return None
    if schema is None:
        raise ValueError("Avro schema is required")
    from io import BytesIO

    from fastavro import schemaless_reader

    try:
        bio = BytesIO(message)
        initial = bio.tell()
        data = schemaless_reader(bio, schema)
        bytes_read = bio.tell() - initial
        if bytes_read != len(message):
            raise ValueError(
                f"Not all bytes were consumed during Avro decoding! "
                f"Read {bytes_read} bytes, but message has {len(message)} bytes."
            )
        return json.dumps(data, cls=_AvroJSONEncoder)
    except Exception as e:
        raise ValueError(f"Failed to deserialize Avro message: {e}")


def _deserialize_protobuf(message, schema, uses_schema_registry):
    from google.protobuf.json_format import MessageToJson

    if not message:
        return None
    if schema is None:
        raise ValueError("Protobuf schema is required")
    try:
        if uses_schema_registry:
            message_indices, message = read_protobuf_message_indices(message)
            if not message_indices:
                message_indices = [0]
        else:
            message_indices = [0]

        message_class = get_protobuf_message_class(schema, message_indices)
        instance = message_class()
        consumed = instance.ParseFromString(message)
        if consumed != len(message):
            raise ValueError(
                f"Not all bytes were consumed during Protobuf decoding! "
                f"Read {consumed} bytes, but message has {len(message)} bytes."
            )
        return MessageToJson(instance)
    except Exception as e:
        raise ValueError(f"Failed to deserialize Protobuf message: {e}")


def _build_avro_schema(schema_str):
    schema = json.loads(schema_str)
    if schema is None:
        raise ValueError("Avro schema cannot be None")
    return schema


def _build_protobuf_schema(schema_str):
    from google.protobuf import descriptor_pb2, descriptor_pool

    schema_bytes = base64.b64decode(schema_str)
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(schema_bytes)

    pool = descriptor_pool.DescriptorPool()
    _preload_well_known_types(pool)
    for fd_proto in descriptor_set.file:
        pool.Add(fd_proto)
    return (pool, descriptor_set)


def _build_protobuf_schema_from_registry(schema_str, dep_schemas):
    from google.protobuf import descriptor_pb2, descriptor_pool

    pool = descriptor_pool.DescriptorPool()
    _preload_well_known_types(pool)
    descriptor_set = descriptor_pb2.FileDescriptorSet()

    for dep_name, dep_b64 in dep_schemas:
        try:
            pool.FindFileByName(dep_name)
            continue
        except KeyError:
            pass
        dep_bytes = base64.b64decode(dep_b64)
        dep_proto = descriptor_pb2.FileDescriptorProto()
        dep_proto.ParseFromString(dep_bytes)
        dep_proto.name = dep_name
        pool.Add(dep_proto)

    schema_bytes = base64.b64decode(schema_str)
    fd_proto = descriptor_pb2.FileDescriptorProto()
    fd_proto.ParseFromString(schema_bytes)
    descriptor_set.file.append(fd_proto)
    pool.Add(fd_proto)
    return (pool, descriptor_set)


def _bootstrap_format_handlers():
    """Direct-register bundled handlers.

    Entry points only resolve once the wheel has been ``pip install``ed.
    For source-mode tests and ``ddev test`` runs we register the builtins
    directly so the check is functional without an install step. Idempotent
    once the entry-point loader has populated the registry with the same
    names.
    """
    from .formats.builtins import (
        AvroHandler,
        BsonHandler,
        JsonHandler,
        ProtobufHandler,
        RawHandler,
        StringHandler,
    )

    for h in (JsonHandler(), StringHandler(), RawHandler(), BsonHandler(), AvroHandler(), ProtobufHandler()):
        _register_handler(h)


_bootstrap_format_handlers()


class MessageDeserializer:
    """Deserialize Kafka messages with pluggable format + compression support."""

    def __init__(self, log, schema_registry=None, value_compression=None, key_compression=None):
        self.log = log
        self.schema_registry = schema_registry
        self.value_compression = value_compression
        self.key_compression = key_compression
        self._schema_cache: dict[tuple[str, str], object] = {}
        self._registry_schema_cache: dict[tuple[str, int], tuple[object, str]] = {}

    def deserialize_message(
        self,
        raw_bytes: bytes | None,
        format_type: str = 'json',
        schema_str: str | None = None,
        uses_schema_registry: bool = False,
        skip_bytes: int = 0,
        compression: str | None = None,
    ) -> tuple[str | None, int | None]:
        """Deserialize a message (key or value).

        Args:
            raw_bytes: Raw message bytes from Kafka.
            format_type: Name of a registered format handler. Built-in:
                'json', 'string', 'raw', 'bson', 'avro', 'protobuf'.
                Third-party handlers may be installed via the
                ``datadog_kafka_actions.formats`` entry-point group.
            schema_str: Schema definition (for protobuf/avro), or arbitrary
                schema material for custom handlers.
            uses_schema_registry: If True, expect Confluent Schema Registry
                wire format (magic byte 0x00 + 4-byte schema id).
            skip_bytes: Drop this many bytes from the start of raw_bytes
                before any other processing (custom producer prefixes).
            compression: Name of a registered compression codec to apply
                BEFORE the format handler runs. No codecs ship in core;
                install a plugin wheel that registers them on the
                ``datadog_kafka_actions.compressions`` entry-point group.

        Returns:
            Tuple of (deserialized_string, schema_id).
        """
        if not raw_bytes:
            return None, None

        if skip_bytes:
            if skip_bytes < 0:
                self.log.warning("skip_bytes must be non-negative, got %d", skip_bytes)
                return f"<deserialization error: skip_bytes must be non-negative, got {skip_bytes}>", None
            if skip_bytes > len(raw_bytes):
                self.log.warning("skip_bytes=%d exceeds message length %d", skip_bytes, len(raw_bytes))
                return (
                    f"<deserialization error: skip_bytes={skip_bytes} exceeds message length {len(raw_bytes)}>",
                    None,
                )
            raw_bytes = raw_bytes[skip_bytes:]
            if not raw_bytes:
                return None, None

        if compression:
            codec = _get_compression_codec(compression)
            if codec is None:
                return f"<deserialization error: unknown compression codec '{compression}'>", None
            try:
                raw_bytes = codec.decompress(raw_bytes)
            except Exception as e:
                self.log.warning("Failed to decompress %s payload: %s", compression, e)
                return f"<deserialization error: {compression} decompression failed: {e}>", None
            if not raw_bytes:
                return None, None

        handler = _get_format_handler(format_type)
        if handler is None:
            return f"<deserialization error: unknown format '{format_type}'>", None

        try:
            schema = None
            if schema_str and not (uses_schema_registry and self.schema_registry is not None):
                schema = self._get_or_build_schema(handler, format_type, schema_str)
            return self._deserialize_bytes_maybe_schema_registry(
                raw_bytes, handler, format_type, schema, uses_schema_registry
            )
        except Exception as e:
            self.log.warning("Failed to deserialize message: %s", e)
            return f"<deserialization error: {e}>", None

    def _deserialize_bytes_maybe_schema_registry(
        self, message: bytes, handler, format_type: str, schema, uses_schema_registry: bool
    ) -> tuple[str | None, int | None]:
        if uses_schema_registry:
            if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
                msg_hex = message[:5].hex() if len(message) >= 5 else message.hex()
                raise ValueError(
                    f"Expected schema registry format (magic byte 0x00 + 4-byte schema ID), "
                    f"but message is too short or has wrong magic byte: {msg_hex}"
                )
            schema_id = int.from_bytes(message[1:5], 'big')
            message = message[5:]

            actual_handler = handler
            if self.schema_registry is not None:
                schema, actual_format = self._fetch_and_build_schema(schema_id, format_type)
                if actual_format != format_type:
                    actual_handler = _get_format_handler(actual_format) or handler

            return (
                actual_handler.deserialize(message, schema, log=self.log, uses_schema_registry=True),
                schema_id,
            )

        try:
            return (
                handler.deserialize(message, schema, log=self.log, uses_schema_registry=False),
                None,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
            if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
                raise e
            schema_id = int.from_bytes(message[1:5], 'big')
            message = message[5:]
            return (
                handler.deserialize(message, schema, log=self.log, uses_schema_registry=True),
                schema_id,
            )

    def _fetch_and_build_schema(self, schema_id: int, format_type: str):
        cache_key = (format_type, schema_id)
        cached = self._registry_schema_cache.get(cache_key)
        if cached is not None:
            return cached

        schema_str, schema_type, dep_schemas = self.schema_registry.get_schema(schema_id)
        registry_type_map = {'AVRO': 'avro', 'PROTOBUF': 'protobuf', 'JSON': 'json'}
        actual_format = registry_type_map.get(schema_type, format_type)

        handler = _get_format_handler(actual_format)
        if handler is None:
            raise ValueError(f"No format handler registered for registry type '{actual_format}'")

        schema_hash = hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
        schema_cache_key = (actual_format, schema_hash + ':registry')
        schema = self._schema_cache.get(schema_cache_key)
        if schema is None:
            schema = handler.build_schema_from_registry(schema_str, dep_schemas or [])
            self._schema_cache[schema_cache_key] = schema

        result = (schema, actual_format)
        self._registry_schema_cache[cache_key] = result
        return result

    def _get_or_build_schema(self, handler, format_type: str, schema_str: str):
        schema_hash = hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
        cache_key = (format_type, schema_hash)
        cached = self._schema_cache.get(cache_key)
        if cached is not None:
            return cached
        schema = handler.build_schema(schema_str)
        self._schema_cache[cache_key] = schema
        return schema


class DeserializedMessage:
    """Represents a deserialized Kafka message with metadata."""

    def __init__(self, kafka_msg, deserializer: MessageDeserializer, config: dict):
        self.kafka_msg = kafka_msg
        self.deserializer = deserializer
        self.config = config

        self._key_deserialized = None
        self._value_deserialized = None
        self._key_schema_id = None
        self._value_schema_id = None

    @property
    def offset(self) -> int:
        return self.kafka_msg.offset()

    @property
    def partition(self) -> int:
        return self.kafka_msg.partition()

    @property
    def timestamp(self) -> int:
        ts_type, ts_value = self.kafka_msg.timestamp()
        return ts_value if ts_value else 0

    @property
    def topic(self) -> str:
        return self.kafka_msg.topic()

    @property
    def headers(self) -> dict:
        headers = {}
        if self.kafka_msg.headers():
            for key, value in self.kafka_msg.headers():
                try:
                    headers[key] = value.decode('utf-8') if value else None
                except UnicodeDecodeError:
                    headers[key] = f"<base64>{base64.b64encode(value).decode('ascii')}"
        return headers

    @staticmethod
    def _parse_deserialized(deserialized: str | None):
        if not deserialized:
            return None
        try:
            return json.loads(deserialized)
        except (json.JSONDecodeError, ValueError):
            return deserialized

    @property
    def key(self) -> dict | str | None:
        if self._key_deserialized is None and self.kafka_msg.key():
            deserialized, schema_id = self.deserializer.deserialize_message(
                self.kafka_msg.key(),
                self.config.get('key_format', 'json'),
                self.config.get('key_schema'),
                self.config.get('key_uses_schema_registry', False),
                skip_bytes=self.config.get('key_skip_bytes', 0),
                compression=self.deserializer.key_compression,
            )
            self._key_deserialized = self._parse_deserialized(deserialized)
            self._key_schema_id = schema_id
        return self._key_deserialized

    @property
    def value(self) -> dict | str | None:
        if self._value_deserialized is None and self.kafka_msg.value():
            deserialized, schema_id = self.deserializer.deserialize_message(
                self.kafka_msg.value(),
                self.config.get('value_format', 'json'),
                self.config.get('value_schema'),
                self.config.get('value_uses_schema_registry', False),
                skip_bytes=self.config.get('value_skip_bytes', 0),
                compression=self.deserializer.value_compression,
            )
            self._value_deserialized = self._parse_deserialized(deserialized)
            self._value_schema_id = schema_id
        return self._value_deserialized

    @property
    def key_schema_id(self) -> int | None:
        _ = self.key
        return self._key_schema_id

    @property
    def value_schema_id(self) -> int | None:
        _ = self.value
        return self._value_schema_id

    def to_dict(self) -> dict:
        return {
            'offset': self.offset,
            'partition': self.partition,
            'timestamp': self.timestamp,
            'topic': self.topic,
            'headers': self.headers,
            'key': self.key,
            'value': self.value,
        }
