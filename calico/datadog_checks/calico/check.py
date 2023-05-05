# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRIC_MAP


class CalicoCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):

        super(CalicoCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {'namespace': 'calico', 'metrics': [METRIC_MAP]}
