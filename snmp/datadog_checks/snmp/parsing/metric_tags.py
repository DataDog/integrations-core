# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
from typing import List, TypedDict

from datadog_checks.base import ConfigurationError

from ..exceptions import UnresolvedOID
from ..models import OID
from ..pysnmp_types import ObjectIdentity
from ..resolver import OIDResolver
from .models import ParsedMatchMetricTag, ParsedMetricTag, ParsedSimpleMetricTag
from .types import GlobalMetricTag

MetricTagsParseResult = TypedDict(
    'MetricTagsParseResult', {'oids': List[OID], 'parsed_metric_tags': List[ParsedMetricTag]}
)


def parse_metric_tags(metric_tags, resolver):
    # type: (List[GlobalMetricTag], OIDResolver) -> MetricTagsParseResult
    oids = []  # type: List[OID]
    parsed_metric_tags = []  # type: List[ParsedMetricTag]

    for metric_tag in metric_tags:
        symbol = metric_tag.get('symbol')

        if symbol is None:
            raise ConfigurationError('A metric tag must specify a symbol: {}'.format(metric_tag))

        parsed_metric_tags.append(_parse_metric_tag(metric_tag, symbol))

        oid = _parse_oid(metric_tag, symbol)

        try:
            parts = oid.as_tuple()
        except UnresolvedOID:
            pass
        else:
            resolver.register(parts, symbol)

        oids.append(oid)

    return {'oids': oids, 'parsed_metric_tags': parsed_metric_tags}


def _parse_metric_tag(metric_tag, symbol):
    # type: (GlobalMetricTag, str) -> ParsedMetricTag
    if 'tag' in metric_tag:
        return ParsedSimpleMetricTag(name=metric_tag['tag'], symbol=symbol)

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

    return ParsedMatchMetricTag(tags, symbol, pattern)


def _parse_oid(metric_tag, symbol):
    # type: (GlobalMetricTag, str) -> OID
    if 'OID' not in metric_tag and 'MIB' not in metric_tag:
        raise ConfigurationError('A metric tag must specify an OID or a MIB: {}'.format(metric_tag))

    if 'MIB' in metric_tag:
        mib = metric_tag['MIB']
        return OID(ObjectIdentity(mib, symbol))

    return OID(metric_tag['OID'])
