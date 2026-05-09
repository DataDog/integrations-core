# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Compression codec registry for kafka_actions.

Some producers compress message payloads at the application layer (before
handing bytes to the Kafka producer) using a variety of algorithms, separate
from the broker-negotiated ``compression.type`` setting. This module exposes
a pluggable codec interface so consumers can decompress those payloads
before deserialization.

No codecs ship in the core wheel — install a plugin wheel that registers
codecs on the ``datadog_kafka_actions.compressions`` entry-point group, or
register them directly via :func:`register_codec` in tests.
"""

from .base import CompressionCodec
from .registry import get_codec, list_codecs, register_codec

__all__ = ['CompressionCodec', 'get_codec', 'list_codecs', 'register_codec']
