# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.argo_workflows.metrics import METRIC_MAP
from datadog_checks.base import OpenMetricsBaseCheckV2


class ArgoWorkflowsCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "argo_workflows"
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
            "rename_labels": {"version": "go_version"},
        }
