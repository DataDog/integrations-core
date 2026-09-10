# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The public metrics interface: count, gauge and distribution, enriched and handed to a sink."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Protocol

from ddev.monitoring.context import EMPTY_FIELDS, MonitorContext, enrich

EMPTY_TAGS: Mapping[str, str] = MappingProxyType({})


class MetricKind(StrEnum):
    COUNT = 'count'
    GAUGE = 'gauge'
    DISTRIBUTION = 'distribution'


@dataclass(frozen=True)
class MetricRecord:
    """An emission-time snapshot; fields include tags after identity protection."""

    name: str
    kind: MetricKind
    value: float
    tags: Mapping[str, str]
    fields: Mapping[str, Any]


class MetricsSink(Protocol):
    """Accept records without blocking the emitting thread."""

    def record(self, record: MetricRecord) -> None: ...


class Metrics:
    """No export occurs without a sink or after the runtime closes."""

    def __init__(
        self,
        context: MonitorContext,
        *,
        sink: MetricsSink | None = None,
        fields: Mapping[str, Any] = EMPTY_FIELDS,
        is_closed: Callable[[], bool] | None = None,
    ) -> None:
        self._context = context
        self._sink = sink
        self._is_closed = is_closed if is_closed is not None else (lambda: False)
        self._fields = dict(fields)

    def bind(self, **fields: Any) -> Metrics:
        return Metrics(self._context, sink=self._sink, fields={**self._fields, **fields}, is_closed=self._is_closed)

    def count(self, name: str, value: float = 1, *, tags: Mapping[str, str] | None = None, **fields: Any) -> None:
        self._emit(MetricKind.COUNT, name, value, tags, fields)

    def gauge(self, name: str, value: float, *, tags: Mapping[str, str] | None = None, **fields: Any) -> None:
        self._emit(MetricKind.GAUGE, name, value, tags, fields)

    def distribution(self, name: str, value: float, *, tags: Mapping[str, str] | None = None, **fields: Any) -> None:
        self._emit(MetricKind.DISTRIBUTION, name, value, tags, fields)

    def _emit(
        self,
        kind: MetricKind,
        name: str,
        value: float,
        tags: Mapping[str, str] | None,
        fields: Mapping[str, Any],
    ) -> None:
        if self._is_closed() or self._sink is None:
            return
        context = self._context
        protected = context.protected_fields
        kept_tags = {key: value for key, value in tags.items() if key not in protected} if tags else {}
        call = {**self._fields, **fields, **kept_tags}
        self._sink.record(
            MetricRecord(
                name=name,
                kind=kind,
                value=value,
                tags=MappingProxyType(kept_tags) if kept_tags else EMPTY_TAGS,
                fields=enrich(context.base_fields, context.scoped, call, protected),
            )
        )
