# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2  # noqa: F401


class VeleroCheck(OpenMetricsBaseCheckV2):

    __NAMESPACE__ = 'velero'

    def __init__(self, name, init_config, instances):
        super(VeleroCheck, self).__init__(name, init_config, instances)
