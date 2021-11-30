# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import PerfCountersBaseCheck
from datadog_checks.base.utils.tracing import traced_class

from .config_models import ConfigMixin


class WindowsPerformanceCountersCheck(PerfCountersBaseCheck, ConfigMixin):
    pass
