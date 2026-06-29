# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Compression codec registry for kafka_actions.

Some producers compress message payloads at the application layer (before
handing bytes to the Kafka producer) using a variety of algorithms, separate
from the broker-negotiated ``compression.type`` setting. This module exposes
a pluggable codec interface so consumers can decompress those payloads
before deserialization.

Built-in codecs (gzip, zlib, snappy, lz4, lz4_dd_hdr, zstd) ship in this
wheel. gzip and zlib work out of the box; snappy/lz4/lz4_dd_hdr/zstd require
their optional packages to be installed (see the integration README).
"""

from .base import CompressionCodec
from .registry import get_codec, list_codecs, register_codec

__all__ = ['CompressionCodec', 'get_codec', 'list_codecs', 'register_codec']
