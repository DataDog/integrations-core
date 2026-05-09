# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Built-in format handlers, registered via entry points in pyproject.toml."""

from __future__ import annotations

import base64
import datetime
import decimal
import json
import uuid
from io import BytesIO

from .base import FormatHandler


class JsonHandler(FormatHandler):
    name = 'json'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        if not message:
            return None
        decoded = message.decode('utf-8').strip()
        if not decoded:
            return None
        json.loads(decoded)
        return decoded


class StringHandler(FormatHandler):
    name = 'string'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        if not message:
            return None
        decoded = message.decode('utf-8')
        if not decoded:
            return None
        return json.dumps(decoded)


class RawHandler(FormatHandler):
    name = 'raw'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        if not message:
            return None
        return json.dumps(base64.b64encode(message).decode('ascii'))


class BsonHandler(FormatHandler):
    name = 'bson'

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        if not message:
            return None
        from bson import decode as bson_decode
        from bson.json_util import dumps as bson_dumps

        try:
            return bson_dumps(bson_decode(message))
        except Exception as e:
            raise ValueError(f"Failed to deserialize BSON message: {e}")


class _AvroJSONEncoder(json.JSONEncoder):
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


class AvroHandler(FormatHandler):
    name = 'avro'

    def build_schema(self, schema_str):
        schema = json.loads(schema_str)
        if schema is None:
            raise ValueError("Avro schema cannot be None")
        return schema

    def build_schema_from_registry(self, schema_str, dep_schemas):
        return self.build_schema(schema_str)

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        if not message:
            return None
        if schema is None:
            raise ValueError("Avro schema is required")
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
    array_len, bytes_read = _read_varint(payload)
    payload = payload[bytes_read:]
    indices = []
    for _ in range(array_len):
        index, bytes_read = _read_varint(payload)
        indices.append(index)
        payload = payload[bytes_read:]
    return indices, payload


def _preload_well_known_types(pool):
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

    modules = (
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
    for module in modules:
        file_name = module.DESCRIPTOR.name
        try:
            pool.FindFileByName(file_name)
            continue
        except KeyError:
            pass
        fd_proto = descriptor_pb2.FileDescriptorProto()
        module.DESCRIPTOR.CopyToProto(fd_proto)
        pool.Add(fd_proto)


def _get_protobuf_message_class(schema_info, message_indices):
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


class ProtobufHandler(FormatHandler):
    name = 'protobuf'

    def build_schema(self, schema_str):
        from google.protobuf import descriptor_pb2, descriptor_pool

        schema_bytes = base64.b64decode(schema_str)
        descriptor_set = descriptor_pb2.FileDescriptorSet()
        descriptor_set.ParseFromString(schema_bytes)

        pool = descriptor_pool.DescriptorPool()
        _preload_well_known_types(pool)
        for fd_proto in descriptor_set.file:
            pool.Add(fd_proto)
        return (pool, descriptor_set)

    def build_schema_from_registry(self, schema_str, dep_schemas):
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

    def deserialize(self, message, schema, *, log, uses_schema_registry):
        from google.protobuf.json_format import MessageToJson

        if not message:
            return None
        if schema is None:
            raise ValueError("Protobuf schema is required")
        try:
            if uses_schema_registry:
                message_indices, message = _read_protobuf_message_indices(message)
                if not message_indices:
                    message_indices = [0]
            else:
                message_indices = [0]

            message_class = _get_protobuf_message_class(schema, message_indices)
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
