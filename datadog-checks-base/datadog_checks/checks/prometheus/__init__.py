# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from checks import (
        UnknownFormatError,
        PrometheusFormat,
        PrometheusCheck
    )
except ImportError:
    from .prometheus_base import (
        PrometheusFormat,
        UnknownFormatError,
        PrometheusCheck,
    )
    from .base_check import (
        GenericPrometheusCheck
    )

__all__ = [
    'PrometheusFormat',
    'UnknownFormatError',
    'PrometheusCheck',
    'GenericPrometheusCheck'
]
