# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.gitlab.config_models import ConfigMixin

from .metrics import METRICS_MAP


class GitlabCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = CHECK_NAME = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRICS_MAP],
        }
