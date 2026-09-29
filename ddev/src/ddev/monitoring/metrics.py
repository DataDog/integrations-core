# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The public metrics interface: enrich an emission and hand its final record to a sink."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

from ddev.monitoring.context import EMPTY_FIELDS, MonitorContext, enrich
from ddev.monitoring.diagnostics import DiagnosticCategory, DiagnosticSink

EMPTY_TAGS: Mapping[str, str] = MappingProxyType({})

type TagProjector = Callable[[Mapping[str, Any]], Mapping[str, str]]


class MetricKind(StrEnum):
    COUNT = 'count'
    GAUGE = 'gauge'
    DISTRIBUTION = 'distribution'


@dataclass(frozen=True)
class MetricRecord:
    """A metric value and its finalized tags at the time of emission.

    `timestamp` is the wall-clock emission time carried by submitted gauge and
    distribution points; count points are windowed by the sink, which timestamps them at
    the instant it accepts the record.
    """

    name: str
    kind: MetricKind
    value: float
    timestamp: int
    tags: Mapping[str, str]
    unit: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'tags', MappingProxyType(dict(self.tags)))


class MetricsSink(Protocol):
    """Queue records without blocking and expose where delivery failures are reported."""

    @property
    def diagnostics(self) -> DiagnosticSink | None: ...

    @diagnostics.setter
    def diagnostics(self, sink: DiagnosticSink | None) -> None: ...

    def record(self, record: MetricRecord) -> None: ...

    def close(self) -> None: ...


class Metrics:
    """A context-aware metrics view backed by one sink for its lifetime."""

    def __init__(
        self,
        context: MonitorContext,
        *,
        sink: MetricsSink | None = None,
        tag_projector: TagProjector | None = None,
        fields: Mapping[str, Any] = EMPTY_FIELDS,
        is_closed: Callable[[], bool] | None = None,
    ) -> None:
        self._context = context
        self._sink = sink
        self._tag_projector = tag_projector
        self._is_closed = is_closed if is_closed is not None else (lambda: False)
        self._fields = dict(fields)

    def bind(self, **fields: Any) -> Metrics:
        return Metrics(
            self._context,
            sink=self._sink,
            tag_projector=self._tag_projector,
            fields={**self._fields, **fields},
            is_closed=self._is_closed,
        )

    def with_tag_projector(self, tag_projector: TagProjector) -> Metrics:
        """The same view, rendering its tags with *tag_projector* instead of the runtime's."""
        return Metrics(
            self._context,
            sink=self._sink,
            tag_projector=tag_projector,
            fields=self._fields,
            is_closed=self._is_closed,
        )

    def count(
        self,
        name: str,
        value: float = 1,
        *,
        tags: Mapping[str, str] | None = None,
        unit: str | None = None,
        **fields: Any,
    ) -> None:
        """Add one increment; the exporter sums a collection window into a single count point."""
        self._emit(MetricKind.COUNT, name, value, tags, fields, unit=unit)

    def gauge(
        self,
        name: str,
        value: float,
        *,
        tags: Mapping[str, str] | None = None,
        unit: str | None = None,
        **fields: Any,
    ) -> None:
        self._emit(MetricKind.GAUGE, name, value, tags, fields, unit=unit)

    def distribution(self, name: str, value: float, *, tags: Mapping[str, str] | None = None, **fields: Any) -> None:
        self._emit(MetricKind.DISTRIBUTION, name, value, tags, fields)

    def _emit(
        self,
        kind: MetricKind,
        name: str,
        value: float,
        tags: Mapping[str, str] | None,
        fields: Mapping[str, Any],
        *,
        unit: str | None = None,
    ) -> None:
        if self._is_closed() or self._sink is None:
            return
        context = self._context
        protected = context.protected_fields
        kept_tags = {key: value for key, value in tags.items() if key not in protected} if tags else {}
        enriched = enrich(context.base_fields, context.scoped, {**self._fields, **fields, **kept_tags}, protected)
        try:
            final_tags = dict(self._tag_projector(enriched)) if self._tag_projector is not None else kept_tags
            self._sink.record(
                MetricRecord(
                    name=name,
                    kind=kind,
                    value=value,
                    timestamp=int(time.time()),
                    tags=final_tags,
                    unit=unit,
                )
            )
        except Exception as error:
            try:
                diagnostics = self._sink.diagnostics
                if diagnostics is not None:
                    diagnostics(
                        DiagnosticCategory.CONVERSION,
                        'Metric emission failed',
                        {
                            'metric_name': name,
                            'metric_kind': kind.value,
                            'error': f'{type(error).__name__}: {error}',
                        },
                    )
            except Exception:
                pass
