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
    from .mixins import PrometheusFormat, UnknownFormatError
    from .prometheus_base import PrometheusCheck
    from .base_check import GenericPrometheusCheck

from .base_check import PrometheusScraper

__all__ = [
    'PrometheusFormat',
    'UnknownFormatError',
    'PrometheusCheck',
    'GenericPrometheusCheck',
    'PrometheusScraper',
]
