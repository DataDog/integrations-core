# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from raw values.
"""

from typing import Any, Optional

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from .compat import total_time_to_temporal_percent
from .pysnmp_types import PYSNMP_CLASS_NAME_TO_SNMP_TYPE
from .types import SNMP_COUNTERS, SNMP_GAUGES, ForceableMetricType, MetricDefinition, SNMPType


def _get_known_snmp_type(value):
    # type: (Any) -> Optional[SNMPType]
    pysnmp_class_name = value.__class__.__name__
    try:
        return PYSNMP_CLASS_NAME_TO_SNMP_TYPE[pysnmp_class_name]
    except KeyError:
        # Unrecognized PySNMP type. Fine -- but let's discard that piece of information to not be
        # tempted to rely on this information downstream.
        return None


def as_metric_with_inferred_type(value):
    # type: (Any) -> Optional[MetricDefinition]
    snmp_type = _get_known_snmp_type(value)

    if snmp_type in SNMP_COUNTERS:
        return {'type': 'rate', 'value': int(value)}

    if snmp_type in SNMP_GAUGES:
        return {'type': 'gauge', 'value': int(value)}

    opaque = 'opaque'  # type: SNMPType  # Use type hint to make sure this literal is correct.
    if snmp_type == opaque:
        # Try support for float opaque values.
        try:
            decoded, _ = pyasn1_decode(bytes(value))
            value = float(decoded)
        except Exception:
            pass
        else:
            return {'type': 'gauge', 'value': value}

    if snmp_type is not None:
        # Make sure we don't implicitly rely on the fallback too much.
        message = (
            'Value {!r} was recognized as SNMP type {!r} but not handled explicitly. Consider inferring it explicitly.'
        ).format(value, snmp_type)
        raise RuntimeError(message)

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
