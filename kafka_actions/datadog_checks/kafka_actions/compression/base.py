# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Base class for app-level payload compression codecs."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CompressionCodec(ABC):
    """Plug-in interface for app-level payload decompression."""

    name: str = ''

    def check_availability(self) -> None:
        """Verify any optional backing library is importable.

        Override in codecs with optional dependencies so config validation can
        surface an actionable ``install X`` error up front instead of a
        per-message decompression failure. Raise ``ImportError`` if a required
        package is missing.
        """
        return None

    @abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Return the uncompressed payload bytes."""
        raise NotImplementedError
