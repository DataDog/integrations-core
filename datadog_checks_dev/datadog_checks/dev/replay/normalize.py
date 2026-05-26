# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from typing import Any


def _sorted_tags(tags: Any) -> Any:
    if tags is None:
        return None
    return sorted(tags)


def _json_sort_key(item: Any) -> str:
    return json.dumps(item, sort_keys=True, separators=(',', ':'), default=str)


def _normalize_external_tags(external_tags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in external_tags:
        source_map = item.get('source_map') or {}
        normalized.append(
            {
                'hostname': item.get('hostname'),
                'source_map': {str(source): sorted(tags or []) for source, tags in sorted(source_map.items())},
            }
        )
    return sorted(normalized, key=_json_sort_key)


def _normalize_collection(output: dict[str, Any], name: str) -> list[Any]:
    return sorted([dict(item) for item in output.get(name, [])], key=_json_sort_key)


def _normalize_check_states(check_states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for state in check_states:
        item = dict(state)
        for attr in ('tags', 'service_check_tags', '_non_internal_tags'):
            if attr in item:
                item[attr] = _sorted_tags(item[attr])
        normalized.append(item)
    return sorted(normalized, key=_json_sort_key)


def normalize_output(output: dict[str, Any]) -> dict[str, Any]:
    """Normalize check output enough for deterministic first-slice comparisons."""
    metrics = []
    for metric in output.get('metrics', []):
        item = dict(metric)
        item['tags'] = _sorted_tags(item.get('tags'))
        metrics.append(item)

    service_checks = []
    for service_check in output.get('service_checks', []):
        item = dict(service_check)
        item['tags'] = _sorted_tags(item.get('tags'))
        service_checks.append(item)

    return {
        'metrics': sorted(
            metrics,
            key=lambda m: (
                m.get('name'),
                m.get('type'),
                m.get('value'),
                m.get('hostname'),
                m.get('device'),
                m.get('tags') or [],
            ),
        ),
        'service_checks': sorted(
            service_checks,
            key=lambda s: (s.get('name'), s.get('status'), s.get('hostname'), s.get('message'), s.get('tags') or []),
        ),
        'events': output.get('events', []),
        'event_platform_events': output.get('event_platform_events', {}),
        'metadata': _normalize_collection(output, 'metadata'),
        'external_tags': _normalize_external_tags(output.get('external_tags', [])),
        'persistent_cache': _normalize_collection(output, 'persistent_cache'),
        'agent_logs': _normalize_collection(output, 'agent_logs'),
        'telemetry': _normalize_collection(output, 'telemetry'),
        'check_states': _normalize_check_states(output.get('check_states', [])),
        'adapter_stats': _normalize_collection(output, 'adapter_stats'),
    }
