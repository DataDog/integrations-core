# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from collections import Counter
from typing import Any


def _key(item: Any) -> str:
    return json.dumps(item, sort_keys=True, separators=(',', ':'))


def diff_outputs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return multiset additions/removals for each top-level output collection."""
    diff: dict[str, Any] = {'changed': False, 'collections': {}}
    for name in ('metrics', 'service_checks', 'events'):
        old_counts = Counter(_key(item) for item in old.get(name, []))
        new_counts = Counter(_key(item) for item in new.get(name, []))
        removed = list((old_counts - new_counts).elements())
        added = list((new_counts - old_counts).elements())
        collection_diff = {
            'removed': [json.loads(item) for item in removed],
            'added': [json.loads(item) for item in added],
        }
        if removed or added:
            diff['changed'] = True
        diff['collections'][name] = collection_diff
    return diff
