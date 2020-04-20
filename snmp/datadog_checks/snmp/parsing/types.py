# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Types used for representing metrics to parse.
"""

from typing import Dict, List, TypedDict, Union

# Common types.
Symbol = TypedDict('Symbol', {'OID': str, 'name': str})


# Metric tags.

IndexMetricTag = TypedDict('IndexMetricTag', {'index': int, 'mapping': Dict[int, str], 'tag': str}, total=False)

ColumnMetricTag = TypedDict('ColumnMetricTag', {'MIB': str, 'column': Symbol, 'table': str, 'tag': str}, total=False)

MetricTag = Union[IndexMetricTag, ColumnMetricTag]

GlobalMetricTag = TypedDict(
    'GlobalMetricTag',
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


# Metrics.

SymbolMetric = TypedDict(
    'SymbolMetric',
    {'MIB': str, 'symbol': Union[str, Symbol], 'forced_type': str, 'metric_tags': List[str]},
    total=False,
)

TableMetric = TypedDict(
    'TableMetric',
    {
        'MIB': str,
        'table': Union[str, Symbol],
        'symbols': List[Symbol],
        'forced_type': str,
        'metric_tags': List[MetricTag],
    },
    total=False,
)

MIBMetric = Union[SymbolMetric, TableMetric]

OIDMetric = TypedDict(
    'OIDMetric', {'MIB': str, 'name': str, 'OID': str, 'metric_tags': List[str], 'forced_type': str}, total=False,
)

Metric = Union[MIBMetric, OIDMetric]
