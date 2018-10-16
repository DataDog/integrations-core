# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .checks import AgentCheck
from .checks.openmetrics import OpenMetricsBaseCheck
from .config import is_affirmative
from .errors import ConfigurationError
from .utils.common import ensure_bytes, ensure_unicode

# Windows-only
try:
    from .checks.win import PDHBaseCheck
except ImportError:
    PDHBaseCheck = None

__all__ = [
    '__version__',
    'AgentCheck',
    'OpenMetricsBaseCheck',
    'PDHBaseCheck',
    'ConfigurationError',
    'ensure_bytes',
    'ensure_unicode',
    'is_affirmative',
]
