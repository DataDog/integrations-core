# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from collections import Counter
from typing import Any


def _key(item: Any) -> str:
    return json.dumps(item, sort_keys=True, separators=(',', ':'))


OUTPUT_COLLECTIONS = (
    'metrics',
    'service_checks',
    'events',
    'metadata',
    'external_tags',
    'persistent_cache',
    'agent_logs',
    'telemetry',
    'adapter_stats',
)

# Adapter stats are diagnostic metadata about how replay was captured/exercised,
# not integration output. Keep their additions/removals in diff artifacts for
# troubleshooting, but do not make otherwise-identical compare-check runs fail.
NON_BLOCKING_COLLECTIONS = {'adapter_stats'}


def diff_outputs(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Return multiset additions/removals for each top-level output collection."""
    diff: dict[str, Any] = {'changed': False, 'collections': {}}
    for name in OUTPUT_COLLECTIONS:
        old_counts = Counter(_key(item) for item in old.get(name, []))
        new_counts = Counter(_key(item) for item in new.get(name, []))
        removed = list((old_counts - new_counts).elements())
        added = list((new_counts - old_counts).elements())
        collection_diff = {
            'removed': [json.loads(item) for item in removed],
            'added': [json.loads(item) for item in added],
        }
        if name not in NON_BLOCKING_COLLECTIONS and (removed or added):
            diff['changed'] = True
        diff['collections'][name] = collection_diff
    return diff
