# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from SNMP values.
"""

from typing import Any, Optional

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .compat import total_time_to_temporal_percent
from .pysnmp_types import PYSNMP_COUNTER_CLASSES, PYSNMP_GAUGE_CLASSES, Opaque
from .types import ForceableMetricType, MetricDefinition


def as_metric_with_inferred_type(value):
    # type: (Any) -> Optional[MetricDefinition]

    # Ugly hack but couldn't find a cleaner way.
    # Proper way would be to use the ASN1 method isSameTypeWith but it wrongfully returns True in the
    # case of CounterBasedGauge64 and Counter64 for example.
    pysnmp_class_name = value.__class__.__name__

    if pysnmp_class_name in PYSNMP_COUNTER_CLASSES:
        return {'type': 'rate', 'value': int(value)}

    if pysnmp_class_name in PYSNMP_GAUGE_CLASSES:
        return {'type': 'gauge', 'value': int(value)}

    if pysnmp_class_name == 'Opaque':
        # Arbitrary ASN.1 syntax encoded as an octet string. Let's try to decode it as a float.
        # See: http://snmplabs.com/pysnmp/docs/api-reference.html#opaque-type
        try:
            decoded, _ = pyasn1_decode(bytes(value))
            value = float(decoded)
        except Exception:
            pass
        else:
            return {'type': 'gauge', 'value': value}

    # Fallback for unknown SNMP types.
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
