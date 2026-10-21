# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck, OpenMetricsBaseCheckV2


class OpenMetricsCheckV2(OpenMetricsBaseCheckV2):
    AGNOSTIC_HTTP_CLIENT = True


class OpenMetricsCheck(OpenMetricsBaseCheck):
    AGNOSTIC_HTTP_CLIENT = True

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if 'openmetrics_endpoint' in instance:
            return OpenMetricsCheckV2(name, init_config, instances)
        else:
            return super(OpenMetricsBaseCheck, cls).__new__(cls)
