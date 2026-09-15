# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test doubles for the monitoring runtime: a metrics sink and logging handlers that keep records."""

from __future__ import annotations

import json
import logging
from typing import Any

import structlog

from ddev.monitoring.metrics import MetricRecord


class RecordingSink:
    """A ``MetricsSink`` collecting every record it is handed."""

    def __init__(self) -> None:
        self.records: list[MetricRecord] = []

    def record(self, record: MetricRecord) -> None:
        self.records.append(record)

    def records_named(self, name: str) -> list[MetricRecord]:
        return [record for record in self.records if record.name == name]

    def field_values(self, name: str, key: str) -> list[Any]:
        """The values one field took on the records named *name*, in emission order."""
        return [record.fields.get(key) for record in self.records_named(name)]


class RecordingJsonHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict[str, Any]] = []
        self.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
            )
        )

    def emit(self, record: logging.LogRecord) -> None:
        self.events.append(json.loads(self.format(record)))
