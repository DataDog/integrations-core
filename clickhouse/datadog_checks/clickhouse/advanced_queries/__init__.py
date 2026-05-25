# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Advanced ClickHouse query definitions sourced from per-system-table JSON files.

The check registers ``initializer(check)`` on its ``check_initializations`` deque so the
data is parsed once on the first check run. Module attributes (``SystemEvents`` etc.)
remain accessible through ``__getattr__`` for callers that import them directly.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

NAMES = {
    'SystemEvents': 'system_events',
    'SystemMetrics': 'system_metrics',
    'SystemAsynchronousMetrics': 'system_async_metrics',
    'SystemErrors': 'system_errors',
}


def load(name: str) -> dict:
    """Return the QueryManager-shaped query dict for ``name`` (e.g. ``"system_events"``)."""
    with open(os.path.join(DATA_DIR, f'{name}.json'), encoding='utf-8') as f:
        spec = json.load(f)
    if 'items' not in spec:
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


def _build_items(compact: dict, prefix: str) -> dict:
    """Expand the compact ``{type: keys | {key: scale}}`` map to the per-entry dict shape."""
    merged: dict[str, dict] = {}
    for type_name, group in compact.items():
        if isinstance(group, dict):
            for key, scale in group.items():
                merged[key] = {'name': f'{prefix}.{key}', 'type': type_name, 'scale': scale}
        else:
            for key in group:
                merged[key] = {'name': f'{prefix}.{key}', 'type': type_name}
    return dict(sorted(merged.items()))


_cache: dict[str, dict] = {}


def __getattr__(name: str) -> dict:
    if name not in NAMES:
        raise AttributeError(name)
    if name not in _cache:
        _cache[name] = load(NAMES[name])
    return _cache[name]


def initializer(check) -> Callable[[], None]:
    """Return a no-arg callable that warms the module cache on first check run."""

    def _load() -> None:
        for attr, file in NAMES.items():
            _cache.setdefault(attr, load(file))

    return _load
