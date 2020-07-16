# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Helpers for deriving metrics from SNMP values.
"""

from typing import Any, Optional

from pyasn1.codec.ber.decoder import decode as pyasn1_decode

from datadog_checks.snmp.utils import sanitize_varbind_value

from .compat import total_time_to_temporal_percent
from .pysnmp_inspect import is_counter, is_gauge, is_opaque
from .types import MetricDefinition


def as_metric_with_inferred_type(value):
    # type: (Any) -> Optional[MetricDefinition]
    if is_counter(value):
        return {'type': 'rate', 'value': int(value)}

    if is_gauge(value):
        return {'type': 'gauge', 'value': int(value)}

    if is_opaque(value):
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


def as_metric_with_forced_type(value, forced_type, options):
    # type: (Any, str, dict) -> Optional[MetricDefinition]
    value = float(sanitize_varbind_value(value))
    if forced_type == 'gauge':
        return {'type': 'gauge', 'value': value}

    if forced_type == 'percent':
        return {'type': 'rate', 'value': total_time_to_temporal_percent(value, scale=1)}

    if forced_type == 'counter':
        return {'type': 'rate', 'value': value}

    if forced_type == 'monotonic_count':
        return {'type': 'monotonic_count', 'value': value}

    if forced_type == 'monotonic_count_and_rate':
        return {'type': 'monotonic_count_and_rate', 'value': value}

    if forced_type == 'flag_stream':
        index = int(options['placement']) - 1
        return {'type': 'gauge', 'value': int(str(value)[index])}

    return None
