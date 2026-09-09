# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Shared-context enrichment and per-handler rendering for structlog."""

from __future__ import annotations

from collections.abc import Callable, Collection
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from ddev.monitoring.context import MonitorContext, enrich


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
