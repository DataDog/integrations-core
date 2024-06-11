# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2  # noqa: F401

from .metrics import METRIC_MAP, RENAME_LABELS_MAP


class vLLMCheck(OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric and service check the integration sends
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'vllm'

    def __init__(self, name, init_config, instances):
        super(vLLMCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            "rename_labels": RENAME_LABELS_MAP,
        }
