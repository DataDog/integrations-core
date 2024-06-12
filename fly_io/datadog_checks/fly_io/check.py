# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRICS, RENAME_LABELS_MAP


class FlyIoCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'fly_io'

    def get_default_config(self):
        return {'metrics': [METRICS], 'rename_labels': RENAME_LABELS_MAP, 'hostname_label': 'instance'}
