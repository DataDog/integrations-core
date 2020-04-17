# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from SNMP values.
"""

from typing import Any, Optional, Set

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .compat import total_time_to_temporal_percent
from .types import MetricDefinition

# SNMP value types that we explicitly support.
SNMP_COUNTER_CLASSES = {
    'Counter32',
    'Counter64',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'ZeroBasedCounter64',
}  # type: Set[str]
SNMP_GAUGE_CLASSES = {
    'Gauge32',
    'Integer',
    'Integer32',
    'Unsigned32',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'CounterBasedGauge64',
}  # type: Set[str]


def as_metric_with_inferred_type(value):
    # type: (Any) -> Optional[MetricDefinition]

    # Ugly hack but couldn't find a cleaner way. Proper way would be to use the ASN.1
    # method `.isSameTypeWith()`, or at least `isinstance()`.
    # But these wrongfully return `True` in some cases, eg:
    # ```python
    # >>> from pysnmp.proto.rfc1902 import Counter64
    # >>> from datadog_checks.snmp.pysnmp_types import CounterBasedGauge64
    # >>> issubclass(CounterBasedGauge64, Counter64)
    # True  # <-- WRONG! (CounterBasedGauge64 values are gauges, not counters.)
    # ````

    pysnmp_class_name = value.__class__.__name__

    if pysnmp_class_name in SNMP_COUNTER_CLASSES:
        return {'type': 'rate', 'value': int(value)}

    if pysnmp_class_name in SNMP_GAUGE_CLASSES:
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
    # type: (Any, str) -> Optional[MetricDefinition]
    if forced_type == 'gauge':
        return {'type': 'gauge', 'value': int(value)}

    if forced_type == 'percent':
        return {'type': 'rate', 'value': total_time_to_temporal_percent(int(value), scale=1)}

    if forced_type == 'counter':
        return {'type': 'rate', 'value': int(value)}

    if forced_type == 'monotonic_count':
        return {'type': 'monotonic_count', 'value': int(value)}

    return None
