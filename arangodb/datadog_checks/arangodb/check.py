# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, construct_metrics_config


class ArangodbCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'arangodb'
    SERVER_MODE_ENDPOINT = '/_admin/server/mode'
    SERVER_ID_ENDPOINT = '/_admin/server/id'

    def __init__(self, name, init_config, instances):

        super(ArangodbCheck, self).__init__(name, init_config, instances)
        self.openmetrics_endpoint = self.instance.get('openmetrics_endpoint')
        self.base_url = urlparse(self.openmetrics_endpoint).scheme + "://" + urlparse(self.openmetrics_endpoint).netloc

        self.base_tags = []
        self.get_mode_tag()
        self.get_id_tag()

    def get_default_config(self):
        default_config = {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }

        if self.base_tags:
            default_config['tags'] = self.base_tags

        return default_config

    def get_mode_tag(self):
        """
        Get the tag for the mode of the server.
        """
        response = self.http.get(self.base_url + self.SERVER_MODE_ENDPOINT)

        if response.json()['code'] == 200:
            self.base_tags.append('mode:{}'.format(response.json()['mode']))
        else:
            self.log.debug("Unable to get server mode, skipping `mode` tag.")

    def get_id_tag(self):
        """
        Get the tag for the mode of the server in a cluster.
        """
        response = self.http.get(self.base_url + self.SERVER_ID_ENDPOINT)

        if response.json()['code'] == 200:
            self.base_tags.append('id:{}'.format(response.json()['id']))
        else:
            self.log.debug("Unable to get server id. Server is not running in cluster mode. Skipping `id` tag.")
