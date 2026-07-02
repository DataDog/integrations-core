# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Lazy registry of compression codecs."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from threading import Lock

from .base import CompressionCodec

_LOG = logging.getLogger(__name__)
_ENTRY_POINT_GROUP = 'datadog_kafka_actions.compressions'

_lock = Lock()
_codecs: dict[str, CompressionCodec] = {}
_loaded = False


def register_codec(codec: CompressionCodec) -> None:
    if not codec.name:
        raise ValueError(f"CompressionCodec {type(codec).__name__} has no name set")
    with _lock:
        _codecs[codec.name] = codec


def _register_builtins() -> None:
    """Direct-register built-in compression codecs.

    Third-party codecs (snappy, lz4, zstd) have lazy imports inside their
    ``decompress`` methods — they register unconditionally but raise
    ``ImportError`` if the backing library is not installed. Imported lazily
    here to avoid pulling the codec modules in at registry import time.
    """
    from .codecs import GzipCodec, Lz4Codec, Lz4DdHdrCodec, SnappyCodec, ZlibCodec, ZstdCodec

    for codec in (GzipCodec(), ZlibCodec(), SnappyCodec(), Lz4Codec(), Lz4DdHdrCodec(), ZstdCodec()):
        _codecs.setdefault(codec.name, codec)


def _load_entry_points() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        _register_builtins()
        try:
            eps = entry_points(group=_ENTRY_POINT_GROUP)
        except TypeError:  # pragma: no cover
            eps = entry_points().get(_ENTRY_POINT_GROUP, [])
        for ep in eps:
            if ep.name in _codecs:
                continue
            try:
                cls = ep.load()
                instance = cls() if isinstance(cls, type) else cls
                if not isinstance(instance, CompressionCodec):
                    _LOG.warning("Entry point %s did not produce a CompressionCodec", ep.name)
                    continue
                if not instance.name:
                    instance.name = ep.name
                _codecs[instance.name] = instance
            except Exception as e:
                _LOG.warning("Failed to load compression codec '%s': %s", ep.name, e)
        _loaded = True


def ensure_codecs_registered() -> None:
    """Register built-in codecs and resolve entry points (idempotent, lazy)."""
    _load_entry_points()


def get_codec(name: str) -> CompressionCodec | None:
    _load_entry_points()
    return _codecs.get(name)


def list_codecs() -> list[str]:
    _load_entry_points()
    return sorted(_codecs)
