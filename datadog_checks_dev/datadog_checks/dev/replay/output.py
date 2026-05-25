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


def _serialize_metadata(datadog_agent) -> list[dict[str, Any]]:
    return [
        {'check_id': check_id, 'name': name, 'value': _jsonify(value)}
        for (check_id, name), value in sorted(datadog_agent._metadata.items())
    ]


def _serialize_external_tags(datadog_agent) -> list[dict[str, Any]]:
    external_tags = []
    for hostname, source_map in datadog_agent._external_tags:
        external_tags.append(
            {
                'hostname': _jsonify(hostname),
                'source_map': {
                    str(source): sorted(_jsonify(tags) or []) for source, tags in sorted(source_map.items())
                },
            }
        )
    return sorted(external_tags, key=lambda item: str(item['hostname']))


def _serialize_persistent_cache(datadog_agent) -> list[dict[str, Any]]:
    return [{'key': key, 'value': _jsonify(value)} for key, value in sorted(datadog_agent._cache.items())]


def _serialize_agent_logs(datadog_agent) -> list[dict[str, Any]]:
    logs = []
    for check_id in sorted(datadog_agent._sent_logs):
        for index, log in enumerate(datadog_agent._sent_logs[check_id]):
            logs.append({'check_id': check_id, 'index': index, 'log': _jsonify(log)})
    return logs


def _serialize_telemetry(datadog_agent) -> list[dict[str, Any]]:
    telemetry = []
    for (check_name, metric_name, metric_type), values in sorted(datadog_agent._sent_telemetry.items()):
        for value in values:
            telemetry.append(
                {
                    'check_name': check_name,
                    'metric_name': metric_name,
                    'metric_type': metric_type,
                    'value': _jsonify(value),
                }
            )
    return telemetry


def reset_serialized_output(aggregator, datadog_agent=None) -> None:
    """Clear output collectors while preserving check and Agent persistent state."""
    aggregator.reset()
    if datadog_agent is None:
        return
    datadog_agent._sent_logs.clear()
    datadog_agent._metadata.clear()
    datadog_agent._external_tags.clear()
    datadog_agent._sent_telemetry.clear()


def serialize_aggregator(aggregator, datadog_agent=None) -> dict[str, Any]:
    """Serialize pytest stub output into a stable JSON-compatible shape."""
    output = {
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
        'metadata': [],
        'external_tags': [],
        'persistent_cache': [],
        'agent_logs': [],
        'telemetry': [],
    }
    if datadog_agent is not None:
        output['metadata'] = _serialize_metadata(datadog_agent)
        output['external_tags'] = _serialize_external_tags(datadog_agent)
        output['persistent_cache'] = _serialize_persistent_cache(datadog_agent)
        output['agent_logs'] = _serialize_agent_logs(datadog_agent)
        output['telemetry'] = _serialize_telemetry(datadog_agent)
    return output
