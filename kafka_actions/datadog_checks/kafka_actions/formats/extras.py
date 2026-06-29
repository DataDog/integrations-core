# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Additional format handlers: msgpack and protobuf_msgpack.

``msgpack`` requires the ``msgpack`` package.
``protobuf_msgpack`` requires ``msgpack`` and ``protobuf``.

Both are imported lazily inside the deserialize methods so the check works
without these packages installed; the handler raises ``ImportError`` only when
actually used.
"""

from __future__ import annotations

import base64
import datetime
import json
import logging
from typing import Any

from .base import FormatHandler


class _MsgpackJSONEncoder(json.JSONEncoder):
    """JSON encoder for types msgpack may emit (bytes, datetime via timestamp ext type)."""

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('ascii')
        return super().default(obj)


class MsgpackHandler(FormatHandler):
    """Decodes msgpack bytes into a JSON string.

    Schemaless — no schema registry support. bytes fields are base64-encoded,
    timestamp ext-type values become ISO-format strings.
    """

    name = 'msgpack'

    def check_availability(self) -> None:
        import msgpack  # noqa: F401

    def deserialize(
        self, message: bytes, schema: Any, *, log: logging.Logger, uses_schema_registry: bool
    ) -> str | None:
        if not message:
            return None
        import msgpack

        try:
            decoded = msgpack.unpackb(message, raw=False, timestamp=3)
        except Exception as e:
            raise ValueError(f"Failed to deserialize msgpack message: {e}") from e
        return json.dumps(decoded, cls=_MsgpackJSONEncoder)


class ProtobufMsgpackHandler(FormatHandler):
    """Protobuf envelope where one or more ``bytes`` fields carry msgpack payloads.

    Same shape as dd-go ``RawPipelineStats``: a protobuf message with a
    ``bytes`` field whose contents are msgpack. Nested messages are supported.

    The ``schema_str`` is a JSON wrapper::

        {
          "schema": "<base64 FileDescriptorSet>",
          "msgpack_fields": ["pkg.OuterMsg.payload", "pkg.InnerMsg.details"]
        }

    Each entry in ``msgpack_fields`` is the fully-qualified protobuf path of a
    ``bytes`` field: ``<package>.<MessageType>.<field_name>``.
    """

    name = 'protobuf_msgpack'

    def check_availability(self) -> None:
        import msgpack  # noqa: F401
        from google.protobuf import json_format  # noqa: F401

    requires_schema = True

    def build_schema(self, schema_str: str):
        from ._helpers import _build_protobuf_schema

        wrapper = json.loads(schema_str)
        proto_schema = _build_protobuf_schema(wrapper['schema'])
        return (proto_schema, set(wrapper.get('msgpack_fields') or []))

    def build_schema_from_registry(self, schema_str: str, dep_schemas: list):
        from ._helpers import _build_protobuf_schema_from_registry

        wrapper = json.loads(schema_str)
        proto_schema = _build_protobuf_schema_from_registry(wrapper['schema'], dep_schemas)
        return (proto_schema, set(wrapper.get('msgpack_fields') or []))

    def deserialize(
        self, message: bytes, schema: Any, *, log: logging.Logger, uses_schema_registry: bool
    ) -> str | None:
        from google.protobuf.json_format import MessageToDict

        from datadog_checks.kafka_actions.formats._helpers import (
            get_protobuf_message_class,
            read_protobuf_message_indices,
        )

        if not message:
            return None
        proto_schema, msgpack_paths = schema

        if uses_schema_registry:
            message_indices, message = read_protobuf_message_indices(message)
            if not message_indices:
                message_indices = [0]
        else:
            message_indices = [0]

        try:
            message_class = get_protobuf_message_class(proto_schema, message_indices)
            instance = message_class()
            consumed = instance.ParseFromString(message)
            if consumed != len(message):
                raise ValueError(
                    f"Not all bytes were consumed during Protobuf decoding! "
                    f"Read {consumed} bytes, but message has {len(message)} bytes."
                )

            result = MessageToDict(instance, preserving_proto_field_name=True)
            if msgpack_paths:
                _apply_msgpack_fields(instance, result, msgpack_paths)
            return json.dumps(result, cls=_MsgpackJSONEncoder)
        except Exception as e:
            raise ValueError(f"Failed to deserialize protobuf_msgpack message: {e}") from e


def _apply_msgpack_fields(instance: Any, result_dict: dict[str, Any], msgpack_paths: set[str]) -> None:
    """Walk ``instance`` + ``result_dict`` in lockstep; decode msgpack bytes fields."""
    import msgpack
    from google.protobuf.descriptor import FieldDescriptor

    def walk(msg, out):
        msg_full = msg.DESCRIPTOR.full_name
        for field_desc, value in msg.ListFields():
            full_path = f"{msg_full}.{field_desc.name}"
            key = field_desc.name
            is_repeated = field_desc.is_repeated
            if full_path in msgpack_paths:
                if field_desc.type != FieldDescriptor.TYPE_BYTES:
                    raise ValueError(f"msgpack_fields path '{full_path}' refers to a non-bytes field")
                if is_repeated:
                    out[key] = [msgpack.unpackb(bytes(b), raw=False, timestamp=3) for b in value]
                else:
                    out[key] = msgpack.unpackb(bytes(value), raw=False, timestamp=3)
                continue
            if field_desc.message_type is None:
                continue
            if field_desc.message_type.GetOptions().map_entry:
                continue
            sub_out = out.get(key)
            if sub_out is None:
                continue
            if is_repeated:
                for sub_msg, sub_d in zip(value, sub_out):
                    walk(sub_msg, sub_d)
            else:
                walk(value, sub_out)

    walk(instance, result_dict)
