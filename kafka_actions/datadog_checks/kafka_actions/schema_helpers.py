# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Schema-building and Confluent wire-format helpers shared by deserialization and serialization."""

from __future__ import annotations

import base64
import json

from google.protobuf import (
    any_pb2,
    api_pb2,
    descriptor_pb2,
    descriptor_pool,
    duration_pb2,
    empty_pb2,
    field_mask_pb2,
    message_factory,
    source_context_pb2,
    struct_pb2,
    timestamp_pb2,
    type_pb2,
    wrappers_pb2,
)

SCHEMA_REGISTRY_MAGIC_BYTE = 0x00

VALID_FORMATS = frozenset({'raw', 'string', 'json', 'bson', 'avro', 'protobuf'})
SCHEMA_FORMATS = frozenset({'avro', 'protobuf'})

# Maps the Schema Registry's schemaType field to our format names.
REGISTRY_TYPE_MAP = {
    'AVRO': 'avro',
    'PROTOBUF': 'protobuf',
    'JSON': 'json',
}

WELL_KNOWN_TYPE_MODULES = (
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


def preload_well_known_types(pool):
    """Add google/protobuf/*.proto well-known types to a fresh DescriptorPool.

    Registry-provided FileDescriptorProtos may depend on well-known types
    (e.g. google/protobuf/timestamp.proto) without listing them as references.
    A custom DescriptorPool doesn't have them by default, so we copy them from
    the generated modules before adding user schemas.
    """
    for module in WELL_KNOWN_TYPE_MODULES:
        file_name = module.DESCRIPTOR.name
        try:
            pool.FindFileByName(file_name)
            continue
        except KeyError:
            pass
        fd_proto = descriptor_pb2.FileDescriptorProto()
        module.DESCRIPTOR.CopyToProto(fd_proto)
        pool.Add(fd_proto)


def read_varint(data: bytes) -> tuple[int, int]:
    """Read a single protobuf-style varint from the start of ``data``.

    Returns (value, bytes_read).
    """
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


def write_varint(value: int) -> bytes:
    """Encode a non-negative integer as a protobuf-style varint."""
    if value < 0:
        raise ValueError(f"varint value must be non-negative, got {value}")

    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def read_protobuf_message_indices(payload: bytes) -> tuple[list[int], bytes]:
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
    array_len, bytes_read = read_varint(payload)
    payload = payload[bytes_read:]

    indices = []
    for _ in range(array_len):
        index, bytes_read = read_varint(payload)
        indices.append(index)
        payload = payload[bytes_read:]

    return indices, payload


def write_protobuf_message_indices(indices: list[int]) -> bytes:
    """Encode a Confluent Protobuf message indices array.

    An empty list encodes to a single zero-length-array byte, which the read
    side treats as "use the first (or only) message type" (index [0]).
    """
    return write_varint(len(indices)) + b''.join(write_varint(index) for index in indices)


def get_protobuf_message_class(schema_info, message_indices: list[int]):
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


def build_avro_schema(schema_str: str):
    """Build an Avro schema from a JSON string."""
    schema = json.loads(schema_str)

    if schema is None:
        raise ValueError("Avro schema cannot be None")

    return schema


def build_protobuf_schema(schema_str: str):
    """Build a Protobuf schema from a base64-encoded FileDescriptorSet.

    Used for inline schemas provided via configuration (value_schema/key_schema).

    Returns:
        Tuple of (descriptor_pool, file_descriptor_set) for use with
        get_protobuf_message_class to select the correct message type.
    """
    schema_bytes = base64.b64decode(schema_str)
    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(schema_bytes)

    pool = descriptor_pool.DescriptorPool()
    preload_well_known_types(pool)
    for fd_proto in descriptor_set.file:
        pool.Add(fd_proto)

    return (pool, descriptor_set)


def build_schema_for_format(
    format_type: str, schema_str: str, from_registry: bool = False, dep_schemas: list[str] | None = None
):
    """Dispatch to the appropriate schema builder for 'protobuf' or 'avro'.

    Returns None for any other format_type (e.g. 'json', 'bson', 'string').
    """
    if format_type == 'protobuf':
        if from_registry:
            return build_protobuf_schema_from_registry(schema_str, dep_schemas or [])
        return build_protobuf_schema(schema_str)
    elif format_type == 'avro':
        return build_avro_schema(schema_str)
    return None


def build_protobuf_schema_from_registry(schema_str: str, dep_schemas: list):
    """Build a Protobuf schema from base64-encoded FileDescriptorProtos.

    The Confluent Schema Registry's ?format=serialized endpoint returns a
    base64-encoded FileDescriptorProto (single file). Schemas with imports
    (e.g., google/protobuf/timestamp.proto) have references that must be
    added to the descriptor pool before the main schema.

    The registry sets all FileDescriptorProto names to 'default', so we
    fix dependency names to match their import paths (e.g.,
    'google/protobuf/timestamp.proto') before adding to the pool.

    Args:
        schema_str: Base64-encoded FileDescriptorProto for the main schema.
        dep_schemas: List of (name, base64_schema) tuples for dependencies,
                     in dependency order (deps of deps come first). The name
                     is the import path used to fix the descriptor name.

    Returns:
        Tuple of (descriptor_pool, file_descriptor_set) for use with
        get_protobuf_message_class to select the correct message type.
    """
    pool = descriptor_pool.DescriptorPool()
    preload_well_known_types(pool)
    descriptor_set = descriptor_pb2.FileDescriptorSet()

    # Add dependencies first (in dependency order), fixing names
    for dep_name, dep_b64 in dep_schemas:
        try:
            pool.FindFileByName(dep_name)
            continue
        except KeyError:
            pass
        dep_bytes = base64.b64decode(dep_b64)
        dep_proto = descriptor_pb2.FileDescriptorProto()
        dep_proto.ParseFromString(dep_bytes)
        # Fix the name from 'default' to the actual import path
        dep_proto.name = dep_name
        pool.Add(dep_proto)

    # Add the main schema
    schema_bytes = base64.b64decode(schema_str)
    fd_proto = descriptor_pb2.FileDescriptorProto()
    fd_proto.ParseFromString(schema_bytes)
    descriptor_set.file.append(fd_proto)
    pool.Add(fd_proto)

    return (pool, descriptor_set)
