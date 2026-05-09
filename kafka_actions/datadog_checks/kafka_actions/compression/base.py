# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Base class for app-level payload compression codecs."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CompressionCodec(ABC):
    """Plug-in interface for app-level payload decompression."""

    name: str = ''

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Return the uncompressed payload bytes."""
        raise NotImplementedError
