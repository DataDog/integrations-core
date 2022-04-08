# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urlparse

from requests import HTTPError

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
        self.base_url = "{}://{}".format(
            urlparse(self.openmetrics_endpoint).scheme, urlparse(self.openmetrics_endpoint).netloc
        )

    def refresh_scrapers(self):
        base_tags = []

        server_mode = self.get_server_mode_tag()
        if server_mode:
            base_tags.append(server_mode)

        server_id = self.get_server_id_tag()
        if server_id:
            base_tags.append(server_id)

        self.set_dynamic_tags(*base_tags)

    def get_default_config(self):
        default_config = {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }

        return default_config

    def get_server_mode_tag(self):
        """
        Get the tag for the mode of the server.
        """
        tag_endpoint = self.base_url + self.SERVER_MODE_ENDPOINT

        try:
            response = self.http.get(tag_endpoint)
            response.raise_for_status()

            if response.json()['code'] == 200:
                return 'server_mode:{}'.format(response.json()['mode'])

        except HTTPError:
            self.log.debug("Unable to get server mode, skipping `server_mode` tag.")
        except Exception as e:
            self.log.debug("Unable to query %s, received error: %s", tag_endpoint, e)

        return None

    def get_server_id_tag(self):
        """
        Get the tag for the server id of the server in a cluster.
        """
        tag_endpoint = self.base_url + self.SERVER_ID_ENDPOINT

        try:
            response = self.http.get(tag_endpoint)
            response.raise_for_status()

            if response.json()['code'] == 200:
                return 'server_id:{}'.format(response.json()['id'])

        except HTTPError:
            self.log.debug("Unable to get server id. Server is not running in cluster mode. Skipping `server_id` tag.")
        except Exception as e:
            self.log.debug("Unable to query %s, received error: %s", tag_endpoint, e)

        return None
