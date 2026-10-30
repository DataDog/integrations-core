# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Test doubles for the monitoring runtime: a metrics sink and logging handlers that keep records."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

import structlog

from ddev.monitoring import ComponentMonitor, MonitoringRuntime
from ddev.monitoring.diagnostics import DiagnosticSink
from ddev.monitoring.metrics import MetricRecord


def make_monitor(name: str, *, handler: logging.Handler | None = None) -> ComponentMonitor:
    return MonitoringRuntime(console_handler=handler).component(name)


def projector_for(*names: str):
    """A tag projector promoting the named context fields, to observe enrichment in tests."""
    selected = frozenset(names)

    def project(fields: Mapping[str, Any]) -> dict[str, str]:
        return {name: str(value) for name, value in fields.items() if name in selected and value is not None}

    return project


class RecordingSink:
    """A `MetricsSink` collecting every record it is handed."""

    def __init__(self) -> None:
        self.records: list[MetricRecord] = []
        self.close_count = 0
        self.diagnostics: DiagnosticSink | None = None

    def record(self, record: MetricRecord) -> None:
        self.records.append(record)

    def close(self) -> None:
        self.close_count += 1

    def records_named(self, name: str) -> list[MetricRecord]:
        return [record for record in self.records if record.name == name]


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
