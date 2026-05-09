# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Lazy registry of format handlers, populated from entry points + direct registration."""

from __future__ import annotations

import logging
from importlib.metadata import entry_points
from threading import Lock

from .base import FormatHandler

_LOG = logging.getLogger(__name__)
_ENTRY_POINT_GROUP = 'datadog_kafka_actions.formats'

_lock = Lock()
_handlers: dict[str, FormatHandler] = {}
_loaded = False


def register_handler(handler: FormatHandler) -> None:
    """Register a handler instance directly (bypasses entry points).

    Useful for tests and for environments where the wheel was not installed
    via pip (e.g. running from a source checkout).
    """
    if not handler.name:
        raise ValueError(f"FormatHandler {type(handler).__name__} has no name set")
    with _lock:
        _handlers[handler.name] = handler


def _load_entry_points() -> None:
    global _loaded
    if _loaded:
        return
    with _lock:
        if _loaded:
            return
        try:
            eps = entry_points(group=_ENTRY_POINT_GROUP)
        except TypeError:  # pragma: no cover — older importlib.metadata
            eps = entry_points().get(_ENTRY_POINT_GROUP, [])
        for ep in eps:
            if ep.name in _handlers:
                continue
            try:
                cls = ep.load()
                instance = cls() if isinstance(cls, type) else cls
                if not isinstance(instance, FormatHandler):
                    _LOG.warning("Entry point %s did not produce a FormatHandler", ep.name)
                    continue
                if not instance.name:
                    instance.name = ep.name
                _handlers[instance.name] = instance
            except Exception as e:
                _LOG.warning("Failed to load format handler '%s': %s", ep.name, e)
        _loaded = True


def get_handler(name: str) -> FormatHandler | None:
    _load_entry_points()
    return _handlers.get(name)


def list_handlers() -> list[str]:
    _load_entry_points()
    return sorted(_handlers)
