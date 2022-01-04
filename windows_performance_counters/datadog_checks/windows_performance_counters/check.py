# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import PerfCountersBaseCheck

from .config_models import ConfigMixin


class WindowsPerformanceCountersCheck(PerfCountersBaseCheck, ConfigMixin):
    pass
