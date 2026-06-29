# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for extras format handlers and compression codecs."""

import base64
import datetime
import gzip
import json
import logging
import struct
import zlib

import pytest

pytestmark = [pytest.mark.unit]


@pytest.fixture
def log():
    return logging.getLogger('test')


# ---------------------------------------------------------------------------
# MsgpackHandler
# ---------------------------------------------------------------------------


@pytest.fixture
def msgpack_handler():
    from datadog_checks.kafka_actions.formats.extras import MsgpackHandler

    return MsgpackHandler()


def test_msgpack_simple_dict(msgpack_handler, log):
    import msgpack

    payload = msgpack.packb({'a': 1, 'b': 'two', 'c': [1, 2, 3]})
    out = msgpack_handler.deserialize(payload, None, log=log, uses_schema_registry=False)
    assert json.loads(out) == {'a': 1, 'b': 'two', 'c': [1, 2, 3]}


def test_msgpack_nested(msgpack_handler, log):
    import msgpack

    payload = msgpack.packb({'outer': {'inner': [None, True, False]}})
    out = msgpack_handler.deserialize(payload, None, log=log, uses_schema_registry=False)
    assert json.loads(out) == {'outer': {'inner': [None, True, False]}}


def test_msgpack_bytes_field_base64_encoded(msgpack_handler, log):
    import msgpack

    payload = msgpack.packb({'data': b'\x00\x01\x02'})
    out = msgpack_handler.deserialize(payload, None, log=log, uses_schema_registry=False)
    assert json.loads(out)['data'] == base64.b64encode(b'\x00\x01\x02').decode('ascii')


def test_msgpack_datetime_isoformat(msgpack_handler, log):
    import msgpack

    payload = msgpack.packb(
        {'when': datetime.datetime(2025, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)},
        datetime=True,
        use_bin_type=True,
    )
    out = msgpack_handler.deserialize(payload, None, log=log, uses_schema_registry=False)
    assert '2025-01-02T03:04:05' in json.loads(out)['when']


def test_msgpack_empty_returns_none(msgpack_handler, log):
    assert msgpack_handler.deserialize(b'', None, log=log, uses_schema_registry=False) is None


def test_msgpack_invalid_raises(msgpack_handler, log):
    with pytest.raises(ValueError, match="Failed to deserialize msgpack"):
        msgpack_handler.deserialize(b'\xff\xff\xff\xff', None, log=log, uses_schema_registry=False)


def test_msgpack_via_message_deserializer(log):
    """MsgpackHandler is reachable through the MessageDeserializer API."""
    import msgpack

    from datadog_checks.kafka_actions.message_deserializer import MessageDeserializer

    payload = msgpack.packb({'x': 42})
    deserializer = MessageDeserializer(log)
    result, _ = deserializer.deserialize_message(
        payload,
        'msgpack',
        schema_str=None,
        uses_schema_registry=False,
    )
    assert json.loads(result) == {'x': 42}


# ---------------------------------------------------------------------------
# ProtobufMsgpackHandler helpers
# ---------------------------------------------------------------------------


def _build_envelope_descriptor_b64():
    """FileDescriptorSet for test.Envelope { bytes message=1; int32 org_id=2; }."""
    from google.protobuf import descriptor_pb2

    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = 'envelope.proto'
    fd.syntax = 'proto3'
    fd.package = 'test'
    msg = fd.message_type.add()
    msg.name = 'Envelope'
    f = msg.field.add()
    f.name = 'message'
    f.number = 1
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f = msg.field.add()
    f.name = 'org_id'
    f.number = 2
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    fds = descriptor_pb2.FileDescriptorSet()
    fds.file.append(fd)
    return base64.b64encode(fds.SerializeToString()).decode('ascii')


def _encode_envelope(inner_bytes: bytes, org_id: int) -> bytes:
    out = bytearray()
    out.append((1 << 3) | 2)
    out.append(len(inner_bytes))
    out += inner_bytes
    out.append((2 << 3) | 0)
    out.append(org_id & 0x7F)
    return bytes(out)


@pytest.fixture
def proto_msgpack_handler():
    from datadog_checks.kafka_actions.formats.extras import ProtobufMsgpackHandler

    return ProtobufMsgpackHandler()


def test_protobuf_msgpack_decodes_inner_field(proto_msgpack_handler, log):
    import msgpack

    schema_b64 = _build_envelope_descriptor_b64()
    inner = {'service': 'orders', 'env': 'prod', 'count': 3}
    inner_bytes = msgpack.packb(inner, use_bin_type=True)
    payload = _encode_envelope(inner_bytes, org_id=42)

    schema_str = json.dumps({'schema': schema_b64, 'msgpack_fields': ['test.Envelope.message']})
    schema = proto_msgpack_handler.build_schema(schema_str)
    out = proto_msgpack_handler.deserialize(payload, schema, log=log, uses_schema_registry=False)
    parsed = json.loads(out)
    assert parsed['org_id'] == 42
    assert parsed['message'] == inner


def test_protobuf_msgpack_empty_returns_none(proto_msgpack_handler, log):
    schema_b64 = _build_envelope_descriptor_b64()
    schema_str = json.dumps({'schema': schema_b64, 'msgpack_fields': []})
    schema = proto_msgpack_handler.build_schema(schema_str)
    assert proto_msgpack_handler.deserialize(b'', schema, log=log, uses_schema_registry=False) is None


def test_protobuf_msgpack_non_bytes_field_raises(proto_msgpack_handler, log):
    import msgpack

    schema_b64 = _build_envelope_descriptor_b64()
    payload = _encode_envelope(msgpack.packb({'a': 1}, use_bin_type=True), org_id=99)
    schema_str = json.dumps({'schema': schema_b64, 'msgpack_fields': ['test.Envelope.org_id']})
    schema = proto_msgpack_handler.build_schema(schema_str)
    with pytest.raises(ValueError, match='non-bytes'):
        proto_msgpack_handler.deserialize(payload, schema, log=log, uses_schema_registry=False)


def test_protobuf_msgpack_invalid_inner_raises(proto_msgpack_handler, log):
    schema_b64 = _build_envelope_descriptor_b64()
    payload = _encode_envelope(b'\xff\xff\xff', org_id=1)
    schema_str = json.dumps({'schema': schema_b64, 'msgpack_fields': ['test.Envelope.message']})
    schema = proto_msgpack_handler.build_schema(schema_str)
    with pytest.raises(ValueError, match="Failed to deserialize protobuf_msgpack"):
        proto_msgpack_handler.deserialize(payload, schema, log=log, uses_schema_registry=False)


def test_protobuf_msgpack_uses_schema_registry_path(proto_msgpack_handler, log):
    import msgpack

    schema_b64 = _build_envelope_descriptor_b64()
    inner = {'k': 'v'}
    body = _encode_envelope(msgpack.packb(inner, use_bin_type=True), org_id=7)
    framed = b'\x00' + body  # varint array_len=0, then the body

    schema_str = json.dumps({'schema': schema_b64, 'msgpack_fields': ['test.Envelope.message']})
    schema = proto_msgpack_handler.build_schema(schema_str)
    out = proto_msgpack_handler.deserialize(framed, schema, log=log, uses_schema_registry=True)
    parsed = json.loads(out)
    assert parsed['org_id'] == 7
    assert parsed['message'] == inner


def test_protobuf_msgpack_build_schema_from_registry(proto_msgpack_handler):
    fd_b64 = _build_envelope_descriptor_b64()
    schema_str = json.dumps({'schema': fd_b64, 'msgpack_fields': ['test.Envelope.message']})
    schema = proto_msgpack_handler.build_schema_from_registry(schema_str, [])
    assert isinstance(schema, tuple)
    assert 'test.Envelope.message' in schema[1]


# ---------------------------------------------------------------------------
# Compression codecs — stdlib (always available)
# ---------------------------------------------------------------------------


def test_gzip_codec_round_trip():
    from datadog_checks.kafka_actions.compression.codecs import GzipCodec

    data = b'hello gzip world'
    compressed = gzip.compress(data)
    assert GzipCodec().decompress(compressed) == data


def test_zlib_codec_round_trip():
    from datadog_checks.kafka_actions.compression.codecs import ZlibCodec

    data = b'hello zlib world'
    compressed = zlib.compress(data)
    assert ZlibCodec().decompress(compressed) == data


# ---------------------------------------------------------------------------
# Compression codecs — third-party (optional packages)
# ---------------------------------------------------------------------------


def test_snappy_codec_round_trip():
    import snappy

    from datadog_checks.kafka_actions.compression.codecs import SnappyCodec

    data = b'hello snappy world'
    compressed = snappy.compress(data)
    assert SnappyCodec().decompress(compressed) == data


def test_lz4_codec_round_trip():
    import lz4.frame

    from datadog_checks.kafka_actions.compression.codecs import Lz4Codec

    data = b'hello lz4 world'
    compressed = lz4.frame.compress(data)
    assert Lz4Codec().decompress(compressed) == data


def test_lz4_dd_hdr_codec_round_trip():
    import lz4.block

    from datadog_checks.kafka_actions.compression.codecs import Lz4DdHdrCodec

    data = b'hello lz4_dd_hdr world'
    raw_block = lz4.block.compress(data, store_size=False)
    framed = struct.pack('<I', len(data)) + raw_block
    assert Lz4DdHdrCodec().decompress(framed) == data


def test_lz4_dd_hdr_too_short_raises():
    from datadog_checks.kafka_actions.compression.codecs import Lz4DdHdrCodec

    with pytest.raises(ValueError, match="too short"):
        Lz4DdHdrCodec().decompress(b'\x00\x01')


def test_zstd_codec_round_trip():
    import zstandard

    from datadog_checks.kafka_actions.compression.codecs import ZstdCodec

    data = b'hello zstd world'
    compressed = zstandard.ZstdCompressor().compress(data)
    assert ZstdCodec().decompress(compressed) == data


# ---------------------------------------------------------------------------
# Codec registry bootstrap
# ---------------------------------------------------------------------------


def test_codecs_registered_via_bootstrap():
    from datadog_checks.kafka_actions.compression.registry import list_codecs

    registered = list_codecs()
    for name in ('gzip', 'zlib', 'snappy', 'lz4', 'lz4_dd_hdr', 'zstd'):
        assert name in registered, f"Expected codec '{name}' in registry"


def test_gzip_decompression_via_message_deserializer(log):
    """End-to-end: gzip-compressed JSON payload decoded through MessageDeserializer."""
    from datadog_checks.kafka_actions.message_deserializer import MessageDeserializer

    payload = {'msg': 'hello'}
    compressed = gzip.compress(json.dumps(payload).encode())
    deserializer = MessageDeserializer(log)
    result, _ = deserializer.deserialize_message(
        compressed,
        'json',
        schema_str=None,
        uses_schema_registry=False,
        compression='gzip',
    )
    assert json.loads(result) == payload
