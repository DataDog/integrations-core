# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Type definitions for items in the `metrics` section of a config file.

Helps us ensure we only manipulate known fields with the correct types.
"""
from typing import Dict, List, TypedDict, Union

# Symbols.

Symbol = TypedDict('Symbol', {'OID': str, 'name': str})


# Table metric tags.

IndexTableMetricTag = TypedDict(
    'IndexTableMetricTag', {'index': int, 'mapping': Dict[int, str], 'tag': str}, total=False
)

ColumnTableMetricTag = TypedDict(
    'ColumnTableMetricTag', {'MIB': str, 'column': Symbol, 'table': str, 'tag': str}, total=False
)

TableMetricTag = Union[IndexTableMetricTag, ColumnTableMetricTag]


# Metrics.

OIDMetric = TypedDict(
    'OIDMetric', {'name': str, 'OID': str, 'metric_tags': List[str], 'forced_type': str}, total=False,
)

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
        'metric_tags': List["TableMetricTag"],
    },
    total=False,
)

Metric = Union[OIDMetric, SymbolMetric, TableMetric]
