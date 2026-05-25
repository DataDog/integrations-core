# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Advanced ClickHouse query definitions sourced from per-system-table JSON files.

The check appends ``warm_cache`` to its ``check_initializations`` deque so the data is
parsed once on the first check run. Module attributes (``SystemEvents`` etc.) remain
accessible through ``__getattr__`` for callers that import them directly.
"""

from __future__ import annotations

import json
import os
from typing import Any

__all__ = ['SystemAsynchronousMetrics', 'SystemErrors', 'SystemEvents', 'SystemMetrics']

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

NAMES = {
    'SystemEvents': 'system_events',
    'SystemMetrics': 'system_metrics',
    'SystemAsynchronousMetrics': 'system_async_metrics',
    'SystemErrors': 'system_errors',
}

_cache: dict[str, dict[str, Any]] = {}


def load(name: str) -> dict[str, Any]:
    """Return the QueryManager-shaped query dict for ``name`` (e.g. ``"system_events"``)."""
    try:
        with open(os.path.join(DATA_DIR, f'{name}.json'), encoding='utf-8') as f:
            spec = json.load(f)
        # Verbatim format: spec carries a pre-built `columns` list; otherwise build from compact `items`.
        if 'columns' in spec:
            return {'name': spec['name'], 'query': spec['query'], 'columns': spec['columns']}
        items = _build_items(spec['items'], spec['prefix'])
        return {
            'name': spec['name'],
            'query': spec['query'],
            'columns': [
                {'name': spec['value_column'], 'type': 'source'},
                {
                    'name': spec['match_column'],
                    'type': 'match',
                    'source': spec['value_column'],
                    'items': items,
                },
            ],
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        raise RuntimeError(f'failed to load advanced query {name!r}') from exc


def _build_items(compact: dict[str, list[str] | dict[str, str]], prefix: str) -> dict[str, dict[str, Any]]:
    """Expand the compact ``{type: keys | {key: scale}}`` map to the per-entry dict shape."""
    merged: dict[str, dict[str, Any]] = {}
    for type_name, group in compact.items():
        if isinstance(group, dict):
            for key, scale in group.items():
                merged[key] = {'name': f'{prefix}.{key}', 'type': type_name, 'scale': scale}
        else:
            for key in group:
                merged[key] = {'name': f'{prefix}.{key}', 'type': type_name}
    return dict(sorted(merged.items()))


def warm_cache() -> None:
    """Populate the module cache for every known query name. Idempotent."""
    for attr, file in NAMES.items():
        if attr not in _cache:
            _cache[attr] = load(file)


def __getattr__(name: str) -> dict[str, Any]:
    if name not in NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name not in _cache:
        _cache[name] = load(NAMES[name])
    return _cache[name]
