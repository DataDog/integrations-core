# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Message deserialization for Kafka messages."""

import base64
import hashlib
import json
from io import BytesIO

from bson import decode as bson_decode
from bson.json_util import dumps as bson_dumps
from fastavro import schemaless_reader
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.json_format import MessageToJson

SCHEMA_REGISTRY_MAGIC_BYTE = 0x00


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


def _read_protobuf_message_indices(payload):
    """
    Read the Confluent Protobuf message indices array.

    The Confluent Protobuf wire format includes message indices after the schema ID:
    [message_indices_length:varint][message_indices:varint...]

    The indices indicate which message type to use from the .proto schema.
    For example, [0] = first message, [1] = second message, [0, 0] = nested message.

    Args:
        payload: bytes after the schema ID

    Returns:
        tuple: (message_indices list, remaining payload bytes)
    """
    array_len, bytes_read = _read_varint(payload)
    payload = payload[bytes_read:]

    indices = []
    for _ in range(array_len):
        index, bytes_read = _read_varint(payload)
        indices.append(index)
        payload = payload[bytes_read:]

    return indices, payload


def _get_protobuf_message_class(schema_info, message_indices):
    """Get the protobuf message class based on schema info and message indices.

    Args:
        schema_info: Tuple of (descriptor_pool, file_descriptor_set)
        message_indices: List of indices (e.g., [0], [1], [2, 0] for nested)

    Returns:
        Message class for the specified type
    """
    pool, descriptor_set = schema_info

    # First index is the message type in the file
    file_descriptor = descriptor_set.file[0]
    message_descriptor_proto = file_descriptor.message_type[message_indices[0]]

    package = file_descriptor.package
    name_parts = [message_descriptor_proto.name]

    # Handle nested messages if there are more indices
    current_proto = message_descriptor_proto
    for idx in message_indices[1:]:
        current_proto = current_proto.nested_type[idx]
        name_parts.append(current_proto.name)

    if package:
        full_name = f"{package}.{'.'.join(name_parts)}"
    else:
        full_name = '.'.join(name_parts)

    message_descriptor = pool.FindMessageTypeByName(full_name)
    return message_factory.GetMessageClass(message_descriptor)


class MessageDeserializer:
    """Handles deserialization of Kafka messages with support for JSON, BSON, Protobuf, and Avro."""

    def __init__(self, log):
        """Initialize the deserializer.

        Args:
            log: Logger instance
        """
        self.log = log

        # Cache for built schemas to avoid rebuilding for every message
        # Key: (format_type, schema_str_hash)
        self._schema_cache = {}

    def deserialize_message(
        self,
        raw_bytes: bytes | None,
        format_type: str = 'json',
        schema_str: str | None = None,
        uses_schema_registry: bool = False,
    ) -> tuple[str | None, int | None]:
        """Deserialize a message (key or value).

        Args:
            raw_bytes: Raw message bytes
            format_type: 'json', 'bson', 'protobuf', or 'avro'
            schema_str: Schema definition (for protobuf/avro)
            uses_schema_registry: Whether to expect Schema Registry format

        Returns:
            Tuple of (deserialized_string, schema_id)
            - deserialized_string: JSON string representation of the message
            - schema_id: Schema ID from Schema Registry (if used), or None
        """
        if not raw_bytes:
            return None, None

        try:
            schema = None
            if format_type in ('protobuf', 'avro') and schema_str:
                schema = self._get_or_build_schema(format_type, schema_str)

            return self._deserialize_bytes_maybe_schema_registry(raw_bytes, format_type, schema, uses_schema_registry)
        except Exception as e:
            self.log.warning("Failed to deserialize message: %s", e)
            return f"<deserialization error: {e}>", None

    def _deserialize_bytes_maybe_schema_registry(
        self, message: bytes, message_format: str, schema, uses_schema_registry: bool
    ) -> tuple[str | None, int | None]:
        """Deserialize message, handling Schema Registry format if present."""
        if uses_schema_registry:
            if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
                msg_hex = message[:5].hex() if len(message) >= 5 else message.hex()
                raise ValueError(
                    f"Expected schema registry format (magic byte 0x00 + 4-byte schema ID), "
                    f"but message is too short or has wrong magic byte: {msg_hex}"
                )
            schema_id = int.from_bytes(message[1:5], 'big')
            message = message[5:]  # Skip the magic byte and schema ID bytes
            return self._deserialize_bytes(message, message_format, schema, uses_schema_registry=True), schema_id
        else:
            # Fallback behavior: try without schema registry format first, then with it
            try:
                return self._deserialize_bytes(message, message_format, schema, uses_schema_registry=False), None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
                # If the message is not valid, it might be a schema registry message
                if len(message) < 5 or message[0] != SCHEMA_REGISTRY_MAGIC_BYTE:
                    raise e
                schema_id = int.from_bytes(message[1:5], 'big')
                message = message[5:]  # Skip the magic byte and schema ID bytes
                return self._deserialize_bytes(message, message_format, schema, uses_schema_registry=True), schema_id

    def _deserialize_bytes(
        self, message: bytes, message_format: str, schema, uses_schema_registry: bool = False
    ) -> str | None:
        """Deserialize message bytes to JSON string.

        Args:
            message: Raw message bytes
            message_format: 'json', 'bson', 'protobuf', 'avro', or 'string'
            schema: Schema object (for protobuf/avro)
            uses_schema_registry: Whether to extract Confluent message indices from the message

        Returns:
            JSON string representation, or None if message is empty
        """
        if not message:
            return None

        if message_format == 'protobuf':
            return self._deserialize_protobuf(message, schema, uses_schema_registry)
        elif message_format == 'avro':
            return self._deserialize_avro(message, schema)
        elif message_format == 'bson':
            return self._deserialize_bson(message)
        elif message_format == 'string':
            return self._deserialize_string(message)
        else:  # Default to json
            return self._deserialize_json(message)

    def _deserialize_json(self, message: bytes) -> str | None:
        """Deserialize JSON message."""
        if not message:
            return None

        decoded = message.decode('utf-8').strip()
        if not decoded:
            return None

        json.loads(decoded)
        return decoded

    def _deserialize_string(self, message: bytes) -> str | None:
        """Deserialize plain string message (not JSON, just UTF-8 text).

        Returns JSON-encoded string for consistency with other deserializers.
        """
        if not message:
            return None

        decoded = message.decode('utf-8')
        if not decoded:
            return None

        # Return as JSON string (quoted string)
        return json.dumps(decoded)

    def _deserialize_bson(self, message: bytes) -> str | None:
        """Deserialize BSON message to JSON string.

        BSON (Binary JSON) is commonly used with MongoDB and some Kafka producers.
        This method decodes BSON bytes and converts to JSON representation.
        """
        if not message:
            return None

        try:
            bson_doc = bson_decode(message)
            return bson_dumps(bson_doc)
        except Exception as e:
            raise ValueError(f"Failed to deserialize BSON message: {e}")

    def _deserialize_protobuf(self, message: bytes, schema_info, uses_schema_registry: bool) -> str:
        """Deserialize Protobuf message using google.protobuf with strict validation.
        
        Args:
            message: Raw protobuf bytes
            schema_info: Tuple of (descriptor_pool, file_descriptor_set) from _build_protobuf_schema
            uses_schema_registry: Whether to extract Confluent message indices from the message
        """
        if schema_info is None:
            raise ValueError("Protobuf schema is required")

        try:
            if uses_schema_registry:
                message_indices, message = _read_protobuf_message_indices(message)
                # Empty indices array means use the first message type (index 0)
                if not message_indices:
                    message_indices = [0]
            else:
                message_indices = [0]

            message_class = _get_protobuf_message_class(schema_info, message_indices)
            schema_instance = message_class()

            bytes_consumed = schema_instance.ParseFromString(message)

            # Strict validation: ensure all bytes consumed
            if bytes_consumed != len(message):
                raise ValueError(
                    f"Not all bytes were consumed during Protobuf decoding! "
                    f"Read {bytes_consumed} bytes, but message has {len(message)} bytes."
                )

            return MessageToJson(schema_instance)
        except Exception as e:
            raise ValueError(f"Failed to deserialize Protobuf message: {e}")

    def _deserialize_avro(self, message: bytes, schema) -> str:
        """Deserialize Avro message."""
        if schema is None:
            raise ValueError("Avro schema is required")

        try:
            bio = BytesIO(message)
            initial_position = bio.tell()
            data = schemaless_reader(bio, schema)
            final_position = bio.tell()

            # Strict validation: ensure all bytes consumed
            bytes_read = final_position - initial_position
            total_bytes = len(message)

            if bytes_read != total_bytes:
                raise ValueError(
                    f"Not all bytes were consumed during Avro decoding! "
                    f"Read {bytes_read} bytes, but message has {total_bytes} bytes."
                )

            return json.dumps(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize Avro message: {e}")

    def _get_or_build_schema(self, message_format: str, schema_str: str):
        """Get cached schema or build it if not in cache.

        Args:
            message_format: 'protobuf' or 'avro'
            schema_str: Schema definition string

        Returns:
            Schema object (cached or newly built)
        """
        schema_hash = hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
        cache_key = (message_format, schema_hash)

        if cache_key in self._schema_cache:
            self.log.debug("Using cached schema for %s (hash: %s...)", message_format, schema_hash[:8])
            return self._schema_cache[cache_key]

        self.log.debug("Building new schema for %s (hash: %s...)", message_format, schema_hash[:8])
        schema = self._build_schema(message_format, schema_str)

        self._schema_cache[cache_key] = schema
        return schema

    def _build_schema(self, message_format: str, schema_str: str):
        """Build schema object from schema string.

        Args:
            message_format: 'protobuf' or 'avro'
            schema_str: Schema definition string

        Returns:
            Schema object
        """
        if message_format == 'protobuf':
            return self._build_protobuf_schema(schema_str)
        elif message_format == 'avro':
            return self._build_avro_schema(schema_str)
        return None

    def _build_avro_schema(self, schema_str: str):
        """Build an Avro schema from a JSON string."""
        schema = json.loads(schema_str)

        if schema is None:
            raise ValueError("Avro schema cannot be None")

        return schema

    def _build_protobuf_schema(self, schema_str: str):
        """Build a Protobuf schema from base64-encoded FileDescriptorSet.
        
        Returns:
            Tuple of (descriptor_pool, file_descriptor_set) for use with
            _get_protobuf_message_class to select the correct message type.
        """
        schema_bytes = base64.b64decode(schema_str)
        descriptor_set = descriptor_pb2.FileDescriptorSet()
        descriptor_set.ParseFromString(schema_bytes)

        pool = descriptor_pool.DescriptorPool()
        for fd_proto in descriptor_set.file:
            pool.Add(fd_proto)

        return (pool, descriptor_set)


class DeserializedMessage:
    """Represents a deserialized Kafka message with metadata."""

    def __init__(self, kafka_msg, deserializer: MessageDeserializer, config: dict):
        """Initialize deserialized message.

        Args:
            kafka_msg: Raw confluent_kafka.Message object
            deserializer: MessageDeserializer instance
            config: Deserialization configuration (value_format, key_format, etc.)
        """
        self.kafka_msg = kafka_msg
        self.deserializer = deserializer
        self.config = config

        # Lazy deserialization - only deserialize when accessed
        self._key_deserialized = None
        self._value_deserialized = None
        self._key_schema_id = None
        self._value_schema_id = None

    @property
    def offset(self) -> int:
        """Message offset."""
        return self.kafka_msg.offset()

    @property
    def partition(self) -> int:
        """Partition number."""
        return self.kafka_msg.partition()

    @property
    def timestamp(self) -> int:
        """Message timestamp."""
        ts_type, ts_value = self.kafka_msg.timestamp()
        return ts_value if ts_value else 0

    @property
    def topic(self) -> str:
        """Topic name."""
        return self.kafka_msg.topic()

    @property
    def headers(self) -> dict:
        """Message headers as dict."""
        headers = {}
        if self.kafka_msg.headers():
            for key, value in self.kafka_msg.headers():
                try:
                    headers[key] = value.decode('utf-8') if value else None
                except UnicodeDecodeError:
                    headers[key] = f"<binary, {len(value)} bytes>"
        return headers

    @property
    def key(self) -> dict | str | None:
        """Deserialized key (lazy)."""
        if self._key_deserialized is None and self.kafka_msg.key():
            key_format = self.config.get('key_format', 'json')
            key_schema = self.config.get('key_schema')
            key_uses_sr = self.config.get('key_uses_schema_registry', False)

            deserialized, schema_id = self.deserializer.deserialize_message(
                self.kafka_msg.key(), key_format, key_schema, key_uses_sr
            )

            # deserialize_message returns JSON string (or None for empty)
            # Parse it to get the actual object
            if deserialized:
                self._key_deserialized = json.loads(deserialized)
            else:
                self._key_deserialized = None

            self._key_schema_id = schema_id

        return self._key_deserialized

    @property
    def value(self) -> dict | str | None:
        """Deserialized value (lazy)."""
        if self._value_deserialized is None and self.kafka_msg.value():
            value_format = self.config.get('value_format', 'json')
            value_schema = self.config.get('value_schema')
            value_uses_sr = self.config.get('value_uses_schema_registry', False)

            deserialized, schema_id = self.deserializer.deserialize_message(
                self.kafka_msg.value(), value_format, value_schema, value_uses_sr
            )

            # deserialize_message returns JSON string (or None for empty)
            # Parse it to get the actual object
            if deserialized:
                self._value_deserialized = json.loads(deserialized)
            else:
                self._value_deserialized = None

            self._value_schema_id = schema_id

        return self._value_deserialized

    @property
    def key_schema_id(self) -> int | None:
        """Schema Registry schema ID for key (if any)."""
        # Trigger lazy deserialization if needed
        _ = self.key
        return self._key_schema_id

    @property
    def value_schema_id(self) -> int | None:
        """Schema Registry schema ID for value (if any)."""
        # Trigger lazy deserialization if needed
        _ = self.value
        return self._value_schema_id

    def to_dict(self) -> dict:
        """Convert message to dict for filtering/output."""
        return {
            'offset': self.offset,
            'partition': self.partition,
            'timestamp': self.timestamp,
            'topic': self.topic,
            'headers': self.headers,
            'key': self.key,
            'value': self.value,
        }
