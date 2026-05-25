# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any


def _sorted_tags(tags: Any) -> Any:
    if tags is None:
        return None
    return sorted(tags)


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
    }
