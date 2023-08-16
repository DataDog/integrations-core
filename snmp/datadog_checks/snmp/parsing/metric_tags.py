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
from ..resolver import OIDResolver  # noqa: F401
from .parsed_metrics import ParsedMatchMetricTag, ParsedMetricTag, ParsedSimpleMetricTag

SymbolTag = NamedTuple('SymbolTag', [('parsed_metric_tag', ParsedMetricTag), ('symbol', str)])

ParsedSymbolTagsResult = TypedDict('ParsedSymbolTagsResult', {'oids': List[OID], 'parsed_symbol_tags': List[SymbolTag]})


def parse_symbol_metric_tags(metric_tags, resolver):
    # type: (List[MetricTag], OIDResolver) -> ParsedSymbolTagsResult
    """
    Parse the symbol based `metric_tags` section of a config file, and return OIDs to fetch and metric tags to submit.
    """
    oids = []  # type: List[OID]
    parsed_symbol_tags = []  # type: List[SymbolTag]

    for metric_tag in metric_tags:
        if 'symbol' not in metric_tag:
            raise ConfigurationError('A metric tag must specify a symbol: {}'.format(metric_tag))

        result = _parse_symbol_metric_tag(metric_tag)

        for name, oid in result.oids_to_resolve.items():
            resolver.register(oid, name)

        oids.append(result.oid)
        parsed_symbol_tags.append(result.symbol_tag)

    return {'oids': oids, 'parsed_symbol_tags': parsed_symbol_tags}


# Helpers below.
# Also some type definitions to make sure we only manipulate known fields with correct types.

MetricTagParseResult = NamedTuple(
    'MetricTagParseResult', [('oid', OID), ('symbol_tag', SymbolTag), ('oids_to_resolve', Dict[str, OID])]
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


def _parse_symbol_metric_tag(metric_tag):
    # type: (MetricTag) -> MetricTagParseResult
    oids_to_resolve = {}

    if 'MIB' in metric_tag:
        oid = OID(ObjectIdentity(metric_tag['MIB'], metric_tag['symbol']))
    elif 'OID' in metric_tag:
        oid = OID(metric_tag['OID'])
        oids_to_resolve[metric_tag['symbol']] = oid
    else:
        raise ConfigurationError('A metric tag must specify an OID or a MIB: {}'.format(metric_tag))

    symbol_tag = SymbolTag(parsed_metric_tag=parse_metric_tag(metric_tag), symbol=metric_tag['symbol'])
    return MetricTagParseResult(oid=oid, symbol_tag=symbol_tag, oids_to_resolve=oids_to_resolve)


def parse_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    if 'tag' in metric_tag:
        parsed_metric_tag = _parse_simple_metric_tag(metric_tag)
    elif 'match' in metric_tag and 'tags' in metric_tag:
        parsed_metric_tag = _parse_regex_metric_tag(metric_tag)
    else:
        raise ConfigurationError(
            'A metric tag must specify either a tag, '
            'or a mapping of tags and a regular expression: {}'.format(metric_tag)
        )
    return parsed_metric_tag


def _parse_simple_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    return ParsedSimpleMetricTag(name=metric_tag['tag'])


def _parse_regex_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    match = metric_tag['match']
    tags = metric_tag['tags']

    if not isinstance(tags, dict):
        raise ConfigurationError(
            'Specified tags needs to be a mapping of tag name to regular expression matching: {}'.format(metric_tag)
        )

    try:
        pattern = re.compile(match)
    except re.error as exc:
        raise ConfigurationError('Failed to compile regular expression {!r}: {}'.format(match, exc))

    return ParsedMatchMetricTag(tags, pattern=pattern)
