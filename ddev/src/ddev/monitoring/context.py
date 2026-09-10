# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The run context: one source of fields for every log record and metric a run emits."""

from __future__ import annotations

from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import Any

EMPTY_FIELDS: Mapping[str, Any] = MappingProxyType({})


def enrich(
    base: Mapping[str, Any], scope: Mapping[str, Any], call: Mapping[str, Any], protected: Collection[str] = ()
) -> dict[str, Any]:
    """Apply local overrides without changing protected run identity."""
    fields = {**base, **scope, **call}
    for key in protected:
        if key in base:
            fields[key] = base[key]
    return fields


class MonitorContext:
    """Run metadata and task-local scopes, shared by logs and metrics."""

    def __init__(self, protected: Collection[str] = ()) -> None:
        self._base: dict[str, Any] = {}
        self._protected = frozenset(protected)
        # A module-level variable would leak scopes between runtimes.
        self._scope: ContextVar[Mapping[str, Any]] = ContextVar('ddev_monitoring_scope', default=EMPTY_FIELDS)

    @property
    def protected_fields(self) -> frozenset[str]:
        return self._protected

    def set_fields(self, **fields: Any) -> None:
        """Updates affect subsequent records, not already-emitted snapshots."""
        self._base.update(fields)

    @property
    def base_fields(self) -> Mapping[str, Any]:
        return MappingProxyType(dict(self._base))

    @property
    def scoped(self) -> Mapping[str, Any]:
        return self._scope.get()

    @property
    def fields(self) -> Mapping[str, Any]:
        return MappingProxyType(enrich(self._base, self._scope.get(), EMPTY_FIELDS, self._protected))

    @contextmanager
    def scope(self, fields: Mapping[str, Any] | None = None) -> Iterator[None]:
        """Restore the enclosing scope on exit, including cancellation."""
        if not fields:
            yield
            return
        token = self._scope.set({**self._scope.get(), **fields})
        try:
            yield
        finally:
            self._scope.reset(token)
