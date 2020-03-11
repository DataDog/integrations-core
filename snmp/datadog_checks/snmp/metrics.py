# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from raw values.
"""

from typing import Optional

from .compat import total_time_to_temporal_percent
from .models import Value
from .types import SNMP_COUNTERS, SNMP_GAUGES, ForceableMetricType, MetricDefinition


def as_metric_with_inferred_type(value):
    # type: (Value) -> Optional[MetricDefinition]
    snmp_type = value.known_snmp_type

    if snmp_type in SNMP_COUNTERS:
        return {'type': 'rate', 'value': int(value)}

    if snmp_type in SNMP_GAUGES:
        return {'type': 'gauge', 'value': int(value)}

    # Fallback.
    try:
        number = float(value)
    except ValueError:
        return None
    else:
        return {'type': 'gauge', 'value': number}


def as_metric_with_forced_type(value, typ):
    # type: (Value, ForceableMetricType) -> Optional[MetricDefinition]
    if typ == 'gauge':
        return {'type': 'gauge', 'value': int(value)}

    if typ == 'percent':
        return {'type': 'rate', 'value': total_time_to_temporal_percent(int(value), scale=1)}

    if typ == 'counter':
        return {'type': 'rate', 'value': int(value)}

    if typ == 'monotonic_count':
        return {'type': 'monotonic_count', 'value': int(value)}

    return None
