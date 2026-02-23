# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from typing import Any

INFRASTRUCTURE_RESOURCE_TYPES = frozenset(('cluster', 'host', 'vm'))
INFRASTRUCTURE_PROPERTY_TYPES = frozenset(('name', 'id'))
ACTIVITY_RESOURCE_TYPES = frozenset(('event', 'task', 'alert'))
# For alerts: 'alerttype' matches API field alertType. 'type' accepted as backward-compat alias.
ACTIVITY_PROPERTY_MAP = {
    'event': frozenset(('type', 'classification')),
    'task': frozenset(('status',)),
    'alert': frozenset(('severity', 'alerttype', 'type')),
}
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
        property_ = str(f.get('property', '')).lower()
        if resource in INFRASTRUCTURE_RESOURCE_TYPES:
            if property_ not in INFRASTRUCTURE_PROPERTY_TYPES:
                property_ = 'name'
        elif resource in ACTIVITY_RESOURCE_TYPES:
            allowed = ACTIVITY_PROPERTY_MAP[resource]
            if property_ not in allowed and property_:
                # Keep inexistent property as-is: _get_activity_value returns '' so no match
                pass
            elif not property_ or property_ not in allowed:
                property_ = next(iter(allowed))
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


def _matches_filter(entity_id: str | None, entity_name: str | None, filt: dict[str, Any]) -> bool:
    if filt['property'] == 'id':
        val = entity_id or ''
    else:
        val = entity_name or ''
    for pat in filt['patterns']:
        if pat.search(val):
            return True
    return False


def _matches_activity_filter(value_or_values: str | list[str], filt: dict[str, Any]) -> bool:
    """Check if value(s) match any pattern in the filter."""
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
    """Return True if the activity item passes activity-specific filters (event/task/alert)."""
    relevant = [f for f in filters if f['resource'] == item_kind]
    if not relevant:
        return True
    excludes = [f for f in relevant if f['type'] == 'exclude']
    includes = [f for f in relevant if f['type'] == 'include']
    for f in excludes:
        val = _get_activity_value(item, item_kind, f['property'])
        if _matches_activity_filter(val, f):
            return False
    if not includes:
        return True
    allowed_props = ACTIVITY_PROPERTY_MAP.get(item_kind, frozenset())
    for f in includes:
        if f['property'] not in allowed_props:
            # Inexistent property cannot match; do not collect
            return False
        val = _get_activity_value(item, item_kind, f['property'])
        if _matches_activity_filter(val, f):
            return True
    return False


def _get_activity_value(item: dict[str, Any], item_kind: str, property_: str) -> str | list[str]:
    """Extract the value for activity filter matching from an item."""
    if item_kind == 'event':
        if property_ == 'type':
            return item.get('eventType') or ''
        if property_ == 'classification':
            return item.get('classifications') or []
    if item_kind == 'task':
        if property_ == 'status':
            return item.get('status') or ''
    if item_kind == 'alert':
        if property_ == 'severity':
            return item.get('severity') or ''
        if property_ in ('alerttype', 'type'):
            return item.get('alertType') or ''
    return ''


def should_collect_resource(
    resource_type: str,
    entity_id: str | None,
    entity_name: str | None,
    filters: list[dict[str, Any]],
) -> bool:
    relevant = [f for f in filters if f['resource'] == resource_type]
    excludes = [f for f in relevant if f['type'] == 'exclude']
    includes = [f for f in relevant if f['type'] == 'include']
    for f in excludes:
        if _matches_filter(entity_id, entity_name, f):
            return False
    if not includes:
        return True
    for f in includes:
        if _matches_filter(entity_id, entity_name, f):
            return True
    return False
