# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Type declarations, for type checking purposes only.
"""
from typing import Literal, NamedTuple, Tuple, TypedDict

MetricDefinition = TypedDict(
    'MetricDefinition',
    {'type': Literal['gauge', 'rate', 'counter', 'monotonic_count', 'monotonic_count_and_rate'], 'value': float},
)

MIBSymbol = NamedTuple('MIBSymbol', [('mib', str), ('symbol', str), ('prefix', Tuple[str, ...])])

OIDMatch = NamedTuple('OIDMatch', [('name', str), ('indexes', Tuple[str, ...])])
