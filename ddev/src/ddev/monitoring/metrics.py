# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The public metrics interface: count, gauge and distribution, enriched and handed to a sink."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

from ddev.monitoring.context import EMPTY_FIELDS, MonitorContext, enrich

EMPTY_TAGS: Mapping[str, str] = MappingProxyType({})

type TagProjector = Callable[[Mapping[str, Any]], Mapping[str, str]]


class MetricKind(StrEnum):
    COUNT = 'count'
    GAUGE = 'gauge'
    DISTRIBUTION = 'distribution'


@dataclass(frozen=True)
class MetricRecord:
    """An emission-time snapshot; tags are the finalized set every sink must deliver."""

    name: str
    kind: MetricKind
    value: float
    timestamp: int
    tags: Mapping[str, str]
    interval: int | None = None
    unit: str | None = None

    def __post_init__(self) -> None:
        # Callers may hand in a mapping they keep mutating; a sink-facing record is final.
        object.__setattr__(self, 'tags', MappingProxyType(dict(self.tags)))


class MetricsSink(Protocol):
    """Accept records without blocking the emitting thread; close drains and releases resources."""

    def record(self, record: MetricRecord) -> None: ...

    def close(self) -> None: ...


class Metrics:
    """No export occurs without a sink or after the runtime closes."""

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

    def count(
        self,
        name: str,
        value: float = 1,
        *,
        tags: Mapping[str, str] | None = None,
        interval: int = 1,
        unit: str | None = None,
        **fields: Any,
    ) -> None:
        self._emit(MetricKind.COUNT, name, value, tags, fields, interval=interval, unit=unit)

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
        interval: int | None = None,
        unit: str | None = None,
    ) -> None:
        if self._is_closed() or self._sink is None:
            return
        context = self._context
        protected = context.protected_fields
        kept_tags = {key: value for key, value in tags.items() if key not in protected} if tags else {}
        enriched = enrich(context.base_fields, context.scoped, {**self._fields, **fields, **kept_tags}, protected)
        try:
            # The projector owns tag selection: without one, only explicit tags survive, so context
            # fields never become raw tags by accident.
            final_tags = dict(self._tag_projector(enriched)) if self._tag_projector is not None else kept_tags
            record = MetricRecord(
                name=name,
                kind=kind,
                value=value,
                timestamp=int(time.time()),
                tags=final_tags,
                interval=interval,
                unit=unit,
            )
            self._sink.record(record)
        except Exception:
            pass  # A broken projector or sink cannot affect the monitored application.
