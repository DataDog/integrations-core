# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Type declarations, for type checking purposes only.
"""
from typing import Literal, TypedDict

ForceableMetricType = Literal['gauge', 'percent']
MetricDefinition = TypedDict(
    'MetricDefinition', {'type': Literal['gauge', 'rate', 'counter', 'monotonic_count'], 'value': float}
)
