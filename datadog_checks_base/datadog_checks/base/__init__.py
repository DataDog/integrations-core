# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .__about__ import __version__
from .checks import AgentCheck
from .checks.openmetrics import OpenMetricsBaseCheck
from .config import is_affirmative
from .errors import ConfigurationError
from .utils.common import ensure_bytes, ensure_unicode, to_native_string, to_string

# Python 3+
try:
    from .checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
except ImportError:
    OpenMetricsBaseCheckV2 = None

# Windows-only
try:
    from .checks.win import PDHBaseCheck
except ImportError:
    PDHBaseCheck = None

# Windows-only and Python 3+
try:
    from .checks.windows.perf_counters import PerfCountersBaseCheck
except Exception:
    PerfCountersBaseCheck = None

# Kubernetes dep will not always be installed
try:
    from .checks.kube_leader import KubeLeaderElectionBaseCheck
except ImportError:
    KubeLeaderElectionBaseCheck = None

__all__ = [
    '__version__',
    'AgentCheck',
    'KubeLeaderElectionBaseCheck',
    'OpenMetricsBaseCheck',
    'OpenMetricsBaseCheckV2',
    'PDHBaseCheck',
    'PerfCountersBaseCheck',
    'ConfigurationError',
    'ensure_bytes',
    'ensure_unicode',
    'is_affirmative',
    'to_native_string',
    'to_string',  # For backwards compat (was renamed to `to_native_string`).
]
