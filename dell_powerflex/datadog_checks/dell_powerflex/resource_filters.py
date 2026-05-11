# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .constants import (
    DEVICE_RESOURCE_TYPE,
    PROTECTION_DOMAIN_RESOURCE_TYPE,
    SDC_RESOURCE_TYPE,
    SDS_RESOURCE_TYPE,
    STORAGE_POOL_RESOURCE_TYPE,
    VOLUME_RESOURCE_TYPE,
)

FILTERABLE_RESOURCE_TYPES = frozenset(
    {
        VOLUME_RESOURCE_TYPE,
        STORAGE_POOL_RESOURCE_TYPE,
        PROTECTION_DOMAIN_RESOURCE_TYPE,
        SDS_RESOURCE_TYPE,
        SDC_RESOURCE_TYPE,
        DEVICE_RESOURCE_TYPE,
    }
)

FILTER_TYPES = frozenset({'include', 'exclude'})


@dataclass(frozen=True)
class ResourceFilter:
    resource: str
    property_name: str
    patterns: tuple[re.Pattern[str], ...] = ()
    filter_type: str = 'include'
    collect_statistics: bool = True


def parse_resource_filters(
    raw_filters: Sequence[Mapping[str, Any]] | None,
    logger: logging.Logger,
) -> list[ResourceFilter]:
    """Parse raw filter configs into a list of validated filters."""
    if not raw_filters:
        return []

    result: list[ResourceFilter] = []
    for f in raw_filters:
        resource = f.get('resource', '')
        if not isinstance(resource, str) or resource not in FILTERABLE_RESOURCE_TYPES:
            logger.warning('Invalid resource type in resource_filters: %s', resource)
            continue

        prop = f.get('property', '')
        if not isinstance(prop, str) or not prop:
            logger.warning('Missing or invalid property in resource_filters for %s', resource)
            continue

        filter_type = str(f.get('type', 'include')).lower()
        if filter_type not in FILTER_TYPES:
            logger.warning('Invalid filter type in resource_filters for %s: %s', resource, filter_type)
            filter_type = 'include'

        compiled = _compile_patterns(f.get('patterns', []), resource, logger)
        collect_statistics = f.get('collect_statistics', True)

        if not compiled and collect_statistics:
            logger.warning('No valid patterns in resource_filters for %s', resource)
            continue

        result.append(
            ResourceFilter(
                resource=resource,
                property_name=prop,
                patterns=tuple(compiled),
                filter_type=filter_type,
                collect_statistics=collect_statistics,
            )
        )

    return result


def should_collect_resource(
    resource_type: str,
    entity: dict[str, Any],
    filters: list[ResourceFilter],
    logger: logging.Logger,
) -> bool:
    """Return True if the entity passes all filters for its resource type.

    Exclude filters take precedence over include filters.
    """
    relevant = [rf for rf in filters if rf.resource == resource_type]
    if not relevant:
        return True

    excludes = [rf for rf in relevant if rf.filter_type == 'exclude']
    for rf in excludes:
        value = entity.get(rf.property_name)
        if value is None:
            continue
        value_str = str(value)
        if any(pattern.search(value_str) for pattern in rf.patterns):
            logger.debug('Skipping %s %s: matched exclude pattern on %s', resource_type, value_str, rf.property_name)
            return False

    includes = [rf for rf in relevant if rf.filter_type == 'include']
    if not includes:
        return True

    for rf in includes:
        value = entity.get(rf.property_name)
        if value is None:
            logger.debug('Skipping %s: property %s not found', resource_type, rf.property_name)
            return False
        value_str = str(value)
        if not any(pattern.search(value_str) for pattern in rf.patterns):
            logger.debug('Skipping %s %s: did not match any include pattern', resource_type, value_str)
            return False

    return True


STATISTICS_DISABLED_BY_DEFAULT = frozenset({DEVICE_RESOURCE_TYPE})


def should_collect_statistics(
    resource_type: str,
    filters: list[ResourceFilter],
) -> bool:
    """Return True if statistics should be collected for this resource type."""
    relevant = [rf for rf in filters if rf.resource == resource_type]
    if not relevant:
        return resource_type not in STATISTICS_DISABLED_BY_DEFAULT
    return all(rf.collect_statistics for rf in relevant)


def _compile_patterns(
    raw_patterns: list[str] | None,
    resource: str,
    logger: logging.Logger,
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
