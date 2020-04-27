# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers to parse the `metric_tags` section of a config file.
"""
import re
from typing import Dict, List, NamedTuple, TypedDict

from datadog_checks.base import ConfigurationError

from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver
from .parsed_metrics import ParsedMatchMetricTag, ParsedMetricTag, ParsedSimpleMetricTag

ParseMetricTagsResult = TypedDict(
    'ParseMetricTagsResult', {'oids': List[OID], 'parsed_metric_tags': List[ParsedMetricTag]}
)


def parse_metric_tags(metric_tags, resolver):
    # type: (List[MetricTag], OIDResolver) -> ParseMetricTagsResult
    """
    Parse the `metric_tags` section of a config file, and return OIDs to fetch and metric tags to submit.
    """
    oids = []  # type: List[OID]
    parsed_metric_tags = []  # type: List[ParsedMetricTag]

    for metric_tag in metric_tags:
        if 'symbol' not in metric_tag:
            raise ConfigurationError('A metric tag must specify a symbol: {}'.format(metric_tag))

        result = _parse_metric_tag(metric_tag)

        for name, oid in result.oids_to_resolve.items():
            resolver.register(oid, name)

        oids.append(result.oid)
        parsed_metric_tags.append(result.parsed_metric_tag)

    return {'oids': oids, 'parsed_metric_tags': parsed_metric_tags}


# Helpers below.
# Also some type definitions to make sure we only manipulate known fields with correct types.

MetricTagParseResult = NamedTuple(
    'MetricTagParseResult', [('oid', OID), ('parsed_metric_tag', ParsedMetricTag), ('oids_to_resolve', Dict[str, OID])]
)

MetricTag = TypedDict(
    'MetricTag',
    {
        'symbol': str,
        'MIB': str,
        'OID': str,
        # Simple tag.
        'tag': str,
        # Regex matching.
        'match': str,
        'tags': List[str],
    },
    total=False,
)


def _parse_metric_tag(metric_tag):
    # type: (MetricTag) -> MetricTagParseResult
    oids_to_resolve = {}

    if 'MIB' in metric_tag:
        oid = OID(ObjectIdentity(metric_tag['MIB'], metric_tag['symbol']))
    elif 'OID' in metric_tag:
        oid = OID(metric_tag['OID'])
        oids_to_resolve[metric_tag['symbol']] = oid
    else:
        raise ConfigurationError('A metric tag must specify an OID or a MIB: {}'.format(metric_tag))

    if 'tag' in metric_tag:
        parsed_metric_tag = _parse_simple_metric_tag(metric_tag)
    elif 'match' in metric_tag and 'tags' in metric_tag:
        parsed_metric_tag = _parse_regex_metric_tag(metric_tag)
    else:
        raise ConfigurationError(
            'A metric tag must specify either a tag, '
            'or a mapping of tags and a regular expression: {}'.format(metric_tag)
        )

    return MetricTagParseResult(oid=oid, parsed_metric_tag=parsed_metric_tag, oids_to_resolve=oids_to_resolve)


def _parse_simple_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    return ParsedSimpleMetricTag(name=metric_tag['tag'], symbol=metric_tag['symbol'])


def _parse_regex_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    symbol = metric_tag['symbol']
    match = metric_tag['match']
    tags = metric_tag['tags']

    if not isinstance(tags, dict):
        raise ConfigurationError(
            'Specified tags needs to be a mapping of tag name to regular expression matching: {}'.format(metric_tag)
        )

    try:
        pattern = re.compile(match)
    except re.error as exc:
        raise ConfigurationError(
            'Failed to compile regular expression {!r} on metric tag {!r}: {}'.format(match, symbol, exc)
        )

    return ParsedMatchMetricTag(tags, symbol=symbol, pattern=pattern)
