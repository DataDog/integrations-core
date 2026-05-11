# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from dataclasses import dataclass
from typing import Any

FILTERABLE_RESOURCE_TYPES = frozenset(
    {
        'volume',
        'storage_pool',
        'protection_domain',
        'sds',
        'sdc',
        'device',
    }
)


@dataclass(frozen=True)
class ResourceFilter:
    resource: str
    property: str
    include: tuple[re.Pattern[str], ...] = ()
    exclude: tuple[re.Pattern[str], ...] = ()
    collect_statistics: bool = True


def parse_resource_filters(
    raw_filters: list[dict[str, Any]] | None,
    logger: Any,
) -> dict[str, ResourceFilter]:
    """Parse raw filter configs into a dict keyed by resource type."""
    if not raw_filters:
        return {}

    result: dict[str, ResourceFilter] = {}
    for f in raw_filters:
        resource = f.get('resource', '')
        if not isinstance(resource, str) or resource not in FILTERABLE_RESOURCE_TYPES:
            logger.warning('Invalid resource type in resource_filters: %s', resource)
            continue

        prop = f.get('property', '')
        if not isinstance(prop, str) or not prop:
            logger.warning('Missing or invalid property in resource_filters for %s', resource)
            continue

        include = _compile_patterns(f.get('include', []), resource, logger)
        exclude = _compile_patterns(f.get('exclude', []), resource, logger)
        collect_statistics = f.get('collect_statistics', True)

        if not include and not exclude and collect_statistics:
            logger.warning('No valid include or exclude patterns in resource_filters for %s', resource)
            continue

        if resource in result:
            logger.warning('Duplicate resource_filters entry for %s, using the last one', resource)

        result[resource] = ResourceFilter(
            resource=resource,
            property=prop,
            include=tuple(include),
            exclude=tuple(exclude),
            collect_statistics=collect_statistics,
        )

    return result


def should_collect_resource(
    resource_type: str,
    entity: dict[str, Any],
    filters: dict[str, ResourceFilter],
    logger: Any,
) -> bool:
    """Return True if the entity passes the filter for its resource type."""
    rf = filters.get(resource_type)
    if rf is None:
        return True

    value = entity.get(rf.property)
    if value is None:
        logger.debug('Skipping %s: property %s not found', resource_type, rf.property)
        return False

    value_str = str(value)

    for pattern in rf.exclude:
        if pattern.search(value_str):
            logger.debug('Skipping %s %s: matched exclude pattern %s', resource_type, value_str, pattern.pattern)
            return False

    if rf.include and not any(pattern.search(value_str) for pattern in rf.include):
        logger.debug('Skipping %s %s: did not match any include pattern', resource_type, value_str)
        return False

    return True


def should_collect_statistics(
    resource_type: str,
    filters: dict[str, ResourceFilter],
) -> bool:
    """Return True if statistics should be collected for this resource type."""
    rf = filters.get(resource_type)
    if rf is None:
        return True
    return rf.collect_statistics


def _compile_patterns(
    raw_patterns: list[str] | None,
    resource: str,
    logger: Any,
) -> list[re.Pattern[str]]:
    """Compile a list of regex pattern strings."""
    compiled = []
    for p in raw_patterns or []:
        if not isinstance(p, str):
            continue
        try:
            compiled.append(re.compile(p))
        except re.error as e:
            logger.warning('Invalid regex pattern in resource_filters for %s: %s (%s)', resource, p, e)
    return compiled
