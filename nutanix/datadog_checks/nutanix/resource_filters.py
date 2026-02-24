# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from typing import Any

INFRASTRUCTURE_RESOURCE_TYPES = frozenset(('cluster', 'host', 'vm'))
ACTIVITY_RESOURCE_TYPES = frozenset(('event', 'task', 'alert', 'audit'))
RESOURCE_TYPES = INFRASTRUCTURE_RESOURCE_TYPES | ACTIVITY_RESOURCE_TYPES
FILTER_TYPES = frozenset(('include', 'exclude'))

ACTIVITY_DEFAULT_PROPERTIES = {
    'event': 'eventType',
    'task': 'status',
    'alert': 'severity',
    'audit': 'auditType',
}


def _get_nested_value(obj: dict[str, Any], property_path: str) -> Any | None:
    """Navigate nested properties using "/" separator, returns None if path doesn't exist."""
    if '/' not in property_path:
        return obj.get(property_path)

    keys = property_path.split('/')
    value = obj
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _validate_filter_structure(f: dict[str, Any]) -> bool:
    """Check if filter has required 'resource' and 'patterns' fields."""
    return isinstance(f, dict) and 'resource' in f and 'patterns' in f and isinstance(f.get('patterns'), list)


def parse_resource_filters(raw_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse and validate resource filters, compiling regex patterns."""
    result = []
    for f in raw_filters or []:
        if not _validate_filter_structure(f):
            continue

        resource = str(f.get('resource', '')).lower()
        if resource not in RESOURCE_TYPES:
            continue

        property_ = str(f.get('property', ''))
        if not property_:
            if resource in INFRASTRUCTURE_RESOURCE_TYPES:
                property_ = 'name'
            elif resource in ACTIVITY_RESOURCE_TYPES:
                property_ = ACTIVITY_DEFAULT_PROPERTIES.get(resource, '')

        filter_type = str(f.get('type', 'include')).lower()
        if filter_type not in FILTER_TYPES:
            filter_type = 'include'

        patterns = f.get('patterns') or []
        compiled: list[re.Pattern[str]] = []
        for p in patterns:
            if isinstance(p, str):
                try:
                    compiled.append(re.compile(p))
                except re.error:
                    pass

        if compiled:
            result.append(
                {
                    'resource': resource,
                    'property': property_,
                    'type': filter_type,
                    'patterns': compiled,
                }
            )
    return result


def _matches_filter(entity: dict[str, Any], filt: dict[str, Any]) -> bool:
    """Check if entity matches any regex pattern in the filter."""
    property_ = filt['property']
    value = _get_nested_value(entity, property_)

    if value is None:
        return False

    val = str(value)
    for pat in filt['patterns']:
        if pat.search(val):
            return True
    return False


def _matches_activity_filter(value_or_values: str | list[str] | None, filt: dict[str, Any]) -> bool:
    """Check if value or any value in list matches any regex pattern in the filter."""
    if value_or_values is None:
        return False

    if isinstance(value_or_values, list):
        values = [str(v) for v in value_or_values if v is not None]
    else:
        values = [str(value_or_values)]

    for val in values:
        for pat in filt['patterns']:
            if pat.search(val):
                return True
    return False


def should_collect_activity(item_kind: str, item: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
    """Return True if activity item passes filters (exclude takes precedence over include)."""
    relevant = [f for f in filters if f['resource'] == item_kind]
    if not relevant:
        return True

    excludes = [f for f in relevant if f['type'] == 'exclude']
    includes = [f for f in relevant if f['type'] == 'include']

    for f in excludes:
        val = _get_activity_value(item, f['property'])
        if _matches_activity_filter(val, f):
            return False

    if not includes:
        return True

    for f in includes:
        val = _get_activity_value(item, f['property'])
        if _matches_activity_filter(val, f):
            return True
    return False


def _get_activity_value(item: dict[str, Any], property_: str) -> str | list[str] | None:
    """Extract property value from activity item, preserving lists and converting others to strings."""
    value = _get_nested_value(item, property_)

    if value is None:
        return None
    if isinstance(value, list):
        return value
    return str(value)


def should_collect_resource(
    resource_type: str,
    entity: dict[str, Any],
    filters: list[dict[str, Any]],
) -> bool:
    """Return True if infrastructure resource passes filters (exclude takes precedence over include)."""
    relevant = [f for f in filters if f['resource'] == resource_type]
    if not relevant:
        return True

    excludes = [f for f in relevant if f['type'] == 'exclude']
    for f in excludes:
        if _matches_filter(entity, f):
            return False

    includes = [f for f in relevant if f['type'] == 'include']
    if not includes:
        return True

    return any(_matches_filter(entity, f) for f in includes)
