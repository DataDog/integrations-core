# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared-context enrichment and per-handler rendering for structlog."""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Mapping
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from ddev.monitoring.context import MonitorContext, enrich

REDACTED = '[REDACTED]'
UNSERIALIZABLE = '[UNSERIALIZABLE]'
SECRET_FIELD_PATTERN = re.compile(r'token|secret|password|passwd|authorization|credential|api[-_]?key', re.IGNORECASE)
URL_PATTERN = re.compile(r'https?://\S+')


def is_secret_field(name: str) -> bool:
    return SECRET_FIELD_PATTERN.search(name) is not None


def _strip_url_query(value: str) -> str:
    def strip(match: re.Match[str]) -> str:
        return match.group(0).split('?', 1)[0].split('#', 1)[0]

    return URL_PATTERN.sub(strip, value)


def redact_value(value: Any, seen: set[int] | None = None) -> Any:
    """Redact nested credentials and signed URL parameters without mutating the input."""
    if isinstance(value, str):
        return _strip_url_query(value)
    if not isinstance(value, (Mapping, list, tuple, set, frozenset)):
        return value

    seen = set() if seen is None else seen
    identity = id(value)
    if identity in seen:
        return UNSERIALIZABLE
    seen.add(identity)
    try:
        if isinstance(value, Mapping):
            return {
                str(key): REDACTED if is_secret_field(str(key)) else redact_value(nested, seen)
                for key, nested in value.items()
            }
        if isinstance(value, (set, frozenset)):
            return sorted((redact_value(item, seen) for item in value), key=str)
        return [redact_value(item, seen) for item in value]
    finally:
        seen.remove(identity)


def redact_event(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    for key, value in tuple(event_dict.items()):
        event_dict[key] = REDACTED if is_secret_field(key) else redact_value(value)
    return event_dict


def logger_processors(context: MonitorContext, is_closed: Callable[[], bool]) -> tuple[Processor, ...]:
    """Resolve context and ``exc_info=True`` before deferred handlers leave the emitting frame."""

    def enrich_and_gate(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
        if is_closed():
            raise structlog.DropEvent
        base = context.base_fields
        return enrich(base, context.scoped, event_dict, context.protected_fields)

    return (
        enrich_and_gate,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.format_exc_info,
        redact_event,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    )


def console_formatter(hidden_fields: Collection[str] = ()) -> structlog.stdlib.ProcessorFormatter:
    """Hide metadata on the formatter's copy, but always retain the message and traceback."""
    hidden = frozenset(hidden_fields) - {'event', 'exception', 'stack'}

    def project(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
        for key in hidden:
            event_dict.pop(key, None)
        # Level presentation belongs to the application display methods, not the line.
        event_dict.pop('level', None)
        return event_dict

    return structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            project,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
    )
