# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from SNMP values.
"""

from typing import Any, Optional

from .compat import total_time_to_temporal_percent
from .models import Value
from .types import ForceableMetricType, MetricDefinition


def as_metric_with_inferred_type(value):
    # type: (Value) -> Optional[MetricDefinition]
    if value.is_counter():
        return {'type': 'rate', 'value': int(value)}

    if value.is_gauge():
        return {'type': 'gauge', 'value': int(value)}

    # Fallback for other SNMP types.
    try:
        number = float(value)
    except ValueError:
        return None
    else:
        return {'type': 'gauge', 'value': number}


def as_metric_with_forced_type(value, forced_type):
    # type: (Any, ForceableMetricType) -> Optional[MetricDefinition]
    if forced_type == 'gauge':
        return {'type': 'gauge', 'value': int(value)}

    if forced_type == 'percent':
        return {'type': 'rate', 'value': total_time_to_temporal_percent(int(value), scale=1)}

    if forced_type == 'counter':
        return {'type': 'rate', 'value': int(value)}

    if forced_type == 'monotonic_count':
        return {'type': 'monotonic_count', 'value': int(value)}

    return None
