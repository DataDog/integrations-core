# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRIC_MAP


class TeamCityCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'teamcity'
    METRICS_ENDPOINT = '/app/metrics'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        instance = instances[0]
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        parsed_endpoint = urlparse(self.openmetrics_endpoint)
        self.base_url = "{}://{}".format(parsed_endpoint.scheme, parsed_endpoint.netloc)
        if instance['bearer_token'] or 'headers' not in instance:
            instance['headers'] = {'Authorization': 'Bearer {}'.format(self.instance.get('bearer_token'))}

    def check(self, _):
        super(TeamCityCheckV2, self).check(None)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': "{}{}".format(self.openmetrics_endpoint, self.METRICS_ENDPOINT),
            'metrics': [METRIC_MAP],
        }
