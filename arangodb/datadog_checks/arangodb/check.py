# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from urllib.parse import urlparse

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, construct_metrics_config


class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'arangodb'
    SERVER_MODE_ENDPOINT = '/_admin/server/mode'

    def __init__(self, name, init_config, instances):
        import pdb
        pdb.set_trace()

        super(ArangodbCheck, self).__init__(name, init_config, instances)
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        self.base_url = urlparse(self.openmetrics_endpoint).scheme + "://" + urlparse(self.openmetrics_endpoint).netloc

        self.base_tags = []
        self.base_tags = self.get_mode_tag()
        # http://localhost:8529/_admin/metrics/v2
        # TODO: Get tag from non-Prometheus port

    def get_default_config(self):
        return {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': construct_metrics_config(METRIC_MAP, {}),
            'tags': ['test:1']
        }

    def get_mode_tag(self):
        '''
        Get the tag for the mode of the server.
        '''

        response = self.http.get(self.base_url + self.SERVER_MODE_ENDPOINT)
        response.raise_for_response()
        return response.json()
