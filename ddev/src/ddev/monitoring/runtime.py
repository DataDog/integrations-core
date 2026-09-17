# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The monitoring runtime: one shared context, logger, metrics interface and lifetime per command."""

from __future__ import annotations

import itertools
import logging
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from ddev.monitoring.context import MonitorContext
from ddev.monitoring.logger import logger_processors
from ddev.monitoring.metrics import Metrics, MetricsSink

_runtime_names = itertools.count()


class ComponentMonitor:
    """A component view sharing the runtime's context and lifetime."""

    def __init__(self, logger: BoundLogger, metrics: Metrics, context: MonitorContext) -> None:
        self._logger = logger
        self._metrics = metrics
        self._context = context

    @property
    def logger(self) -> BoundLogger:
        return self._logger

    @property
    def metrics(self) -> Metrics:
        return self._metrics

    def bind(self, **fields: Any) -> ComponentMonitor:
        """Bind fields to this view's logs and metrics without changing other components."""
        return ComponentMonitor(self._logger.bind(**fields), self._metrics.bind(**fields), self._context)

    @contextmanager
    def scope(self, **fields: Any) -> Iterator[None]:
        """Task-local fields shared with every component view of the runtime inside the block."""
        with self._context.scope(fields):
            yield


class MonitoringRuntime:
    """Owned by the entry point; component views share its context and lifetime."""

    def __init__(
        self,
        *,
        console_handler: logging.Handler | None = None,
        metrics_sink: MetricsSink | None = None,
        protected_fields: Collection[str] = (),
    ) -> None:
        self._closed = False
        self._context = MonitorContext(protected_fields)
        # An unregistered logger isolates handlers from other command invocations, and the
        # NullHandler keeps stdlib from writing to `lastResort` when no console handler was supplied.
        self._stdlib_logger = logging.Logger(f'ddev.monitoring.{next(_runtime_names)}', level=logging.DEBUG)
        self._stdlib_logger.propagate = False
        self._stdlib_logger.addHandler(logging.NullHandler())
        if console_handler is not None:
            self._stdlib_logger.addHandler(console_handler)
        self._logger = structlog.wrap_logger(
            self._stdlib_logger,
            processors=logger_processors(self._context, lambda: self._closed),
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
        ).bind()
        self._metrics = Metrics(self._context, sink=metrics_sink, is_closed=lambda: self._closed)

    @property
    def context(self) -> MonitorContext:
        return self._context

    def set_run_fields(self, **fields: Any) -> None:
        self._context.set_fields(**fields)

    def add_log_handler(self, handler: logging.Handler) -> None:
        """Attach a caller-owned handler using a ProcessorFormatter to render structured ``record.msg``."""
        self._stdlib_logger.addHandler(handler)

    def component(self, name: str, **fields: Any) -> ComponentMonitor:
        return ComponentMonitor(
            logger=self._logger.bind(component=name, **fields),
            metrics=self._metrics.bind(component=name, **fields),
            context=self._context,
        )

    def close(self) -> None:
        """Stop all emissions, detach attached handlers, and leave caller-owned streams open."""
        self._closed = True
        for handler in list(self._stdlib_logger.handlers):
            self._stdlib_logger.removeHandler(handler)
