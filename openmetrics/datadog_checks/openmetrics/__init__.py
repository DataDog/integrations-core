# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .openmetrics import OpenMetricsCheck

__all__ = [
    '__version__',
    'OpenMetricsCheck'
]
