# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from typing import Any

INFRASTRUCTURE_RESOURCE_TYPES = frozenset(('cluster', 'host', 'vm'))
ACTIVITY_RESOURCE_TYPES = frozenset(('event', 'task', 'alert', 'audit'))
RESOURCE_TYPES = INFRASTRUCTURE_RESOURCE_TYPES | ACTIVITY_RESOURCE_TYPES
FILTER_TYPES = frozenset(('include', 'exclude'))


def parse_resource_filters(raw_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for f in raw_filters or []:
        if not isinstance(f, dict) or 'resource' not in f or 'patterns' not in f:
            continue
        resource = str(f.get('resource', '')).lower()
        if resource not in RESOURCE_TYPES:
            continue
        property_ = str(f.get('property', ''))

        if resource in INFRASTRUCTURE_RESOURCE_TYPES:
            if not property_:
                property_ = 'name'
        elif resource in ACTIVITY_RESOURCE_TYPES:
            if not property_:
                if resource == 'event':
                    property_ = 'eventType'
                elif resource == 'task':
                    property_ = 'status'
                elif resource == 'alert':
                    property_ = 'severity'
                elif resource == 'audit':
                    property_ = 'auditType'

        filter_type = str(f.get('type', 'include')).lower()
        if filter_type not in FILTER_TYPES:
            filter_type = 'include'
        patterns = f.get('patterns') or []
        if not isinstance(patterns, list):
            continue
        compiled = []
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
    """Check if entity matches the filter pattern.

    Supports OData-style nested property access using "/" separator.
    Returns False if property path doesn't exist.
    """
    property_ = filt['property']

    if '/' in property_:
        keys = property_.split('/')
        value = entity
        for key in keys:
            if not isinstance(value, dict):
                return False
            if key not in value:
                return False
            value = value[key]
        val = str(value) if value is not None else ''
    else:
        value = entity.get(property_)
        if value is None:
            return False
        val = str(value)

    for pat in filt['patterns']:
        if pat.search(val):
            return True
    return False


def _matches_activity_filter(value_or_values: str | list[str] | None, filt: dict[str, Any]) -> bool:
    """Check if value(s) match any pattern in the filter."""
    if value_or_values is None:
        return False
    if isinstance(value_or_values, list):
        values = [str(v) for v in value_or_values if v is not None]
    else:
        values = [str(value_or_values)] if value_or_values is not None else []
    for val in values:
        for pat in filt['patterns']:
            if pat.search(val):
                return True
    return False


def should_collect_activity(item_kind: str, item: dict[str, Any], filters: list[dict[str, Any]]) -> bool:
    """Return True if the activity item passes activity-specific filters."""
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
    """Extract the value for activity filter matching from an item.

    Supports OData-style nested property access using "/" separator.
    Returns None if property path doesn't exist.
    """
    if '/' in property_:
        keys = property_.split('/')
        value = item
        for key in keys:
            if not isinstance(value, dict):
                return None
            if key not in value:
                return None
            value = value[key]
        if isinstance(value, list):
            return value
        return str(value) if value is not None else ''

    if property_ not in item:
        return None
    value = item[property_]
    if value is None:
        return ''
    if isinstance(value, list):
        return value
    return str(value)


def should_collect_resource(
    resource_type: str,
    entity: dict[str, Any],
    filters: list[dict[str, Any]],
) -> bool:
    """Return True if the infrastructure resource passes filters."""
    relevant = [f for f in filters if f['resource'] == resource_type]
    excludes = [f for f in relevant if f['type'] == 'exclude']
    includes = [f for f in relevant if f['type'] == 'include']
    for f in excludes:
        if _matches_filter(entity, f):
            return False
    if not includes:
        return True
    for f in includes:
        if _matches_filter(entity, f):
            return True
    return False
