# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import re
from collections.abc import Callable
from typing import Any

INFRASTRUCTURE_RESOURCE_TYPES = frozenset(('cluster', 'host', 'vm'))
ACTIVITY_RESOURCE_TYPES = frozenset(('event', 'task', 'alert', 'audit'))
METADATA_RESOURCE_TYPES = frozenset(('category',))
RESOURCE_TYPES = INFRASTRUCTURE_RESOURCE_TYPES | ACTIVITY_RESOURCE_TYPES | METADATA_RESOURCE_TYPES
FILTER_TYPES = frozenset(('include', 'exclude'))

ACTIVITY_DEFAULT_PROPERTIES = {
    'event': 'eventType',
    'task': 'status',
    'alert': 'severity',
    'audit': 'auditType',
}

METADATA_DEFAULT_PROPERTIES = {
    'category': 'type',  # Valid values: SYSTEM, INTERNAL, USER
}

# Default property for infrastructure resources (cluster, host, vm)
_INFRASTRUCTURE_DEFAULT_PROPERTY = 'name'


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


def _default_property_for(resource: str) -> str:
    """Return the default filter property for a resource type."""
    if resource in INFRASTRUCTURE_RESOURCE_TYPES:
        return _INFRASTRUCTURE_DEFAULT_PROPERTY
    if resource in ACTIVITY_RESOURCE_TYPES:
        return ACTIVITY_DEFAULT_PROPERTIES.get(resource, '')
    if resource in METADATA_RESOURCE_TYPES:
        return METADATA_DEFAULT_PROPERTIES.get(resource, '')
    return ''


def parse_resource_filters(raw_filters: list[dict[str, Any]], logger: Any) -> list[dict[str, Any]]:
    """Parse and validate resource filters, compiling regex patterns.

    Filters allow selective collection of infrastructure resources (clusters, hosts, VMs),
    activity data (events, tasks, alerts, audits), and metadata (categories).
    Exclude filters take precedence over include filters.

    If no category filters are specified, only USER type categories are collected by default.
    """
    has_category_filter = any(f.get('resource') == 'category' for f in raw_filters or [])

    result = []
    for f in raw_filters or []:
        if not _validate_filter_structure(f):
            logger.error("Invalid filter structure (missing required fields 'resource' or 'patterns'), skipping: %s", f)
            continue

        resource = str(f.get('resource', '')).lower()
        if resource not in RESOURCE_TYPES:
            logger.error(
                "Invalid resource type '%s' (valid types: %s), skipping filter: %s",
                resource,
                ', '.join(sorted(RESOURCE_TYPES)),
                f,
            )
            continue

        property_ = str(f.get('property', '')) or _default_property_for(resource)

        filter_type = str(f.get('type', 'include')).lower()
        if filter_type not in FILTER_TYPES:
            filter_type = 'include'

        patterns = f.get('patterns') or []
        compiled: list[re.Pattern[str]] = []
        for p in patterns:
            if isinstance(p, str):
                try:
                    compiled.append(re.compile(p))
                except re.error as e:
                    logger.error("Invalid regex pattern '%s' in filter: %s", p, e)

        if compiled:
            result.append(
                {
                    'resource': resource,
                    'property': property_,
                    'type': filter_type,
                    'patterns': compiled,
                }
            )

    # Add default category filter if no category filters were specified
    if not has_category_filter:
        result.append(
            {
                'resource': 'category',
                'property': 'type',
                'type': 'include',
                'patterns': [re.compile(r'^USER$')],
            }
        )
        logger.debug("No category filters specified, applying default filter to include only USER type categories")

    return result


def _matches_patterns(value_or_values: str | list[str] | None, filt: dict[str, Any]) -> bool:
    """Check if value (or any value in list) matches any regex pattern in the filter."""
    if value_or_values is None:
        return False

    if isinstance(value_or_values, list):
        values = [str(v) for v in value_or_values if v is not None]
    else:
        values = [str(value_or_values)]

    return any(pat.search(val) for val in values for pat in filt['patterns'])


def _apply_filters(
    resource_type: str,
    filters: list[dict[str, Any]],
    match_fn: Callable[[dict[str, Any]], bool],
    entity_label: str,
    logger: logging.Logger,
) -> bool:
    """Apply include/exclude filter precedence logic (exclude wins)."""
    relevant = [f for f in filters if f['resource'] == resource_type]
    if not relevant:
        return True

    excludes = [f for f in relevant if f['type'] == 'exclude']
    for f in excludes:
        if match_fn(f):
            logger.debug("Skipping %s due to exclude filter on %s: %s", resource_type, f['property'], entity_label)
            return False

    includes = [f for f in relevant if f['type'] == 'include']
    if not includes:
        return True

    if any(match_fn(f) for f in includes):
        return True

    logger.debug("Skipping %s due to include filter on %s: %s", resource_type, includes[0]['property'], entity_label)
    return False


def should_collect_activity(
    item_kind: str,
    item: dict[str, Any],
    filters: list[dict[str, Any]],
    logger: logging.Logger,
) -> bool:
    """Return True if activity item passes filters (exclude takes precedence over include)."""
    return _apply_filters(
        item_kind,
        filters,
        match_fn=lambda f: _matches_patterns(_get_activity_value(item, f['property']), f),
        entity_label=item.get("extId") or item.get("operationExtId") or "",
        logger=logger,
    )


def _get_activity_value(item: dict[str, Any], property_: str) -> str | list[str] | None:
    """Extract property value from activity item, preserving lists."""
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
    logger: logging.Logger,
) -> bool:
    """Return True if infrastructure resource passes filters (exclude takes precedence over include)."""
    return _apply_filters(
        resource_type,
        filters,
        match_fn=lambda f: _matches_patterns(_get_nested_value(entity, f['property']), f),
        entity_label=entity.get("name") or entity.get("extId") or "",
        logger=logger,
    )
