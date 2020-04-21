# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers to parse the `metric_tags` section of a config file.
"""
import re
from typing import List, TypedDict

from datadog_checks.base import ConfigurationError

from ..exceptions import UnresolvedOID
from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver
from .parsed_metrics import ParsedMatchMetricTag, ParsedMetricTag, ParsedSimpleMetricTag

MetricTagsParseResult = TypedDict(
    'MetricTagsParseResult', {'oids': List[OID], 'parsed_metric_tags': List[ParsedMetricTag]}
)


def parse_metric_tags(metric_tags, resolver):
    # type: (List[MetricTag], OIDResolver) -> MetricTagsParseResult
    """
    Parse the `metric_tags` section of a config file, and return OIDs to fetch and metric tags to submit.
    """
    oids = []  # type: List[OID]
    parsed_metric_tags = []  # type: List[ParsedMetricTag]

    for metric_tag in metric_tags:
        if 'symbol' not in metric_tag:
            raise ConfigurationError('A metric tag must specify a symbol: {}'.format(metric_tag))

        oid = parse_oid(metric_tag)
        oids.append(oid)

        try:
            parts = oid.as_tuple()
        except UnresolvedOID:
            pass
        else:
            resolver.register(parts, metric_tag['symbol'])

        parsed_metric_tag = parse_metric_tag(metric_tag)
        parsed_metric_tags.append(parsed_metric_tag)

    return {'oids': oids, 'parsed_metric_tags': parsed_metric_tags}


# Helpers.


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


def parse_oid(metric_tag):
    # type: (MetricTag) -> OID
    if 'MIB' in metric_tag:
        return OID(ObjectIdentity(metric_tag['MIB'], metric_tag['symbol']))

    if 'OID' in metric_tag:
        return OID(metric_tag['OID'])

    raise ConfigurationError('A metric tag must specify an OID or a MIB: {}'.format(metric_tag))


def parse_metric_tag(metric_tag):
    # type: (MetricTag) -> ParsedMetricTag
    if 'tag' in metric_tag:
        return ParsedSimpleMetricTag(name=metric_tag['tag'], symbol=metric_tag['symbol'])

    if 'tags' not in metric_tag or 'match' not in metric_tag:
        raise ConfigurationError(
            'A metric tag must specify either a tag, '
            'or a mapping of tags and a regular expression: {}'.format(metric_tag)
        )

    match = metric_tag['match']
    tags = metric_tag['tags']

    if not isinstance(tags, dict):
        raise ConfigurationError(
            'Specified tags needs to be a mapping of tag name to regular ' 'expression matching: {}'.format(metric_tag)
        )

    try:
        pattern = re.compile(match)
    except re.error as e:
        raise ConfigurationError('Failed compile regular expression {}: {}'.format(match, e))

    return ParsedMatchMetricTag(tags, symbol=metric_tag['symbol'], pattern=pattern)
