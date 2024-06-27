# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from six.moves.urllib.parse import quote_plus

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRICS, RENAME_LABELS_MAP


class FlyIoCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'fly_io'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.org_slug = self.instance.get('org_slug')
        default_match_string = '{__name__=~".+"}'
        self.match_string = self.instance.get('match_string', default_match_string)
        encoded_match_string = quote_plus(self.match_string)
        default_endpoint = f"https://api.fly.io/prometheus/{self.org_slug}/federate?match[]={encoded_match_string}"
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint', default_endpoint)

        # bypass required openmetrics_endpoint
        self.instance['openmetrics_endpoint'] = self.openmetrics_endpoint

    def get_default_config(self):
        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': [METRICS],
            'rename_labels': RENAME_LABELS_MAP,
            'hostname_label': 'instance',
        }
