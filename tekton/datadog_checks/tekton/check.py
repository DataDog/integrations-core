# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.tekton.config_models import ConfigMixin

from .metrics import METRIC_MAP


class TektonCheck(OpenMetricsBaseCheckV2, ConfigMixin):

    __NAMESPACE__ = 'tekton'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }
