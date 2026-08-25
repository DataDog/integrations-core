# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.hugging_face_tgi.metrics import METRIC_MAP, RENAME_LABELS_MAP


class HuggingFaceTgiCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'hugging_face_tgi'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):
        super(HuggingFaceTgiCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': RENAME_LABELS_MAP,
        }
