# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

try:
    # Agent5 compatibility layer
    from checks import (
        UnknownFormatError,
        PrometheusFormat,
    )
except ImportError:
    from .mixins import PrometheusFormat, UnknownFormatError
    from .base_check import GenericPrometheusCheck

__all__ = [
    'PrometheusFormat',
    'UnknownFormatError',
    'GenericPrometheusCheck',
]
