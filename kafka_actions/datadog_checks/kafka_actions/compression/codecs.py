# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""App-level compression codecs for kafka_actions.

Coverage is driven by patterns observed in Datadog's dd-go and dd-source
producers. ``lz4_dd_hdr`` covers the DataDog/golz4 framing used by
xray-converter (4-byte little-endian uncompressed-size header followed by
raw LZ4 block bytes), which is not the standard LZ4 frame format.

Third-party libraries (python-snappy, lz4, zstandard) are imported lazily
inside each method. If a library is not installed, the codec raises
``ImportError`` when called; the check continues to work for all other formats.
To enable a codec, install the corresponding package into the Agent's embedded
Python (e.g. ``agent integration install python-snappy``).
"""

from __future__ import annotations

import gzip
import struct
import zlib

from .base import CompressionCodec

# Upper bound on the producer-supplied uncompressed-size header for lz4_dd_hdr.
# The header is trusted internal DataDog/golz4 framing, but a corrupt or
# malicious value could otherwise trigger a multi-GB allocation. 512 MiB is far
# larger than any realistic single Kafka message.
LZ4_DD_HDR_MAX_UNCOMPRESSED_SIZE = 512 * 1024 * 1024


class GzipCodec(CompressionCodec):
    name = 'gzip'

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)


class ZlibCodec(CompressionCodec):
    name = 'zlib'

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)


class SnappyCodec(CompressionCodec):
    name = 'snappy'

    def decompress(self, data: bytes) -> bytes:
        import snappy

        return snappy.decompress(data)


class Lz4Codec(CompressionCodec):
    """Standard LZ4 frame format."""

    name = 'lz4'

    def decompress(self, data: bytes) -> bytes:
        import lz4.frame

        return lz4.frame.decompress(data)


class Lz4DdHdrCodec(CompressionCodec):
    """DataDog/golz4 framing: 4-byte little-endian uncompressed size + raw LZ4 block.

    Used by ``cloud-integrations/aws/xray-converter``. Not interchangeable
    with the standard LZ4 frame format.
    """

    name = 'lz4_dd_hdr'

    def decompress(self, data: bytes) -> bytes:
        import lz4.block

        if len(data) < 4:
            raise ValueError("lz4_dd_hdr payload too short for length header")
        (uncompressed_size,) = struct.unpack('<I', data[:4])
        if uncompressed_size > LZ4_DD_HDR_MAX_UNCOMPRESSED_SIZE:
            raise ValueError(
                f"lz4_dd_hdr uncompressed size {uncompressed_size} exceeds the maximum "
                f"allowed {LZ4_DD_HDR_MAX_UNCOMPRESSED_SIZE} bytes"
            )
        return lz4.block.decompress(data[4:], uncompressed_size=uncompressed_size)


class ZstdCodec(CompressionCodec):
    name = 'zstd'

    def decompress(self, data: bytes) -> bytes:
        import zstandard

        return zstandard.ZstdDecompressor().decompress(data)
