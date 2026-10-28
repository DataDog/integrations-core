# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""A stdlib `logging.Logger` facade over a component's structured logger."""

from __future__ import annotations

import logging

from ddev.monitoring.runtime import ComponentMonitor

# Built-in `LogRecord` attributes are excluded so only caller `extra` fields become event fields.
STANDARD_LOG_RECORD_FIELDS = frozenset(logging.LogRecord('adapter', 0, 'adapter', 0, 'adapter', None, None).__dict__)
STANDARD_LOG_RECORD_FIELDS |= {'message', 'asctime'}


class ComponentLogAdapter(logging.Logger):
    """A `logging.Logger` whose records become structured events on a component view.

    Generic code that speaks stdlib logging, like the GitHub client and the event bus, can route its
    diagnostics through the monitoring runtime this way without importing monitoring concepts.
    """

    def __init__(self, monitor: ComponentMonitor) -> None:
        # Unregistered, so nothing but the runtime's own handlers see these records.
        super().__init__(f'ddev.monitoring.adapter.{id(monitor):x}', level=logging.DEBUG)
        self._monitor = monitor

    def handle(self, record: logging.LogRecord) -> None:
        # Copy before `getMessage()` adds `message` to the record's dictionary.
        fields = {key: value for key, value in record.__dict__.items() if key not in STANDARD_LOG_RECORD_FIELDS}
        if record.exc_info is not None:
            # The runtime's exception formatter needs the tuple. A null `exc_info` would leak as a field.
            fields['exc_info'] = record.exc_info
        emit = getattr(self._monitor.logger, record.levelname.lower())
        emit(record.getMessage(), **fields)
