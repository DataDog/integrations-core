# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2


class OpenMetricsCheck(OpenMetricsBaseCheck):
    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            return OpenMetricsBaseCheckV2(name, init_config, instances)
        else:
            return super(OpenMetricsBaseCheck, cls).__new__(cls)
