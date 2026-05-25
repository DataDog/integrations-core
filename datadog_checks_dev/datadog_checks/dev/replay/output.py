# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _jsonify(value: Any) -> Any:
    if hasattr(value, '_asdict'):
        return {k: _jsonify(v) for k, v in value._asdict().items()}
    if isinstance(value, Mapping):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def serialize_aggregator(aggregator) -> dict[str, Any]:
    """Serialize the pytest stub aggregator into a stable JSON-compatible shape."""
    return {
        'metrics': [
            _jsonify(metric)
            for metric_name in sorted(aggregator._metrics)
            for metric in aggregator._metrics[metric_name]
        ],
        'service_checks': [
            _jsonify(service_check)
            for check_name in sorted(aggregator._service_checks)
            for service_check in aggregator._service_checks[check_name]
        ],
        'events': _jsonify(aggregator.events),
        'event_platform_events': {
            event_type: [_jsonify(event) for event in events]
            for event_type, events in sorted(aggregator._event_platform_events.items())
        },
    }
