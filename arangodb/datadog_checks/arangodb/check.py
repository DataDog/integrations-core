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
        server_tags = {'mode': self.SERVER_MODE_ENDPOINT, 'id': self.SERVER_ID_ENDPOINT}

        for tag_name, endpoint in server_tags.items():
            tag = self.get_server_tag(tag_name, endpoint)
            if tag:
                base_tags.append(tag)

        self.set_dynamic_tags(*base_tags)

    def get_default_config(self):
        default_config = {
            'openmetrics_endpoint': self.openmetrics_endpoint,
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }

        return default_config

    def get_server_tag(self, tag_name, endpoint):
        """
        Get the tag for the the server.
        """
        tag_endpoint = self.base_url + endpoint

        try:
            response = self.http.get(tag_endpoint)
            response.raise_for_status()

            return 'server_{}:{}'.format(tag_name, response.json()[tag_name])

        except HTTPError:
            self.log.debug("Unable to get server %s, skipping `server_%s` tag.", tag_name, tag_name)
        except Exception as e:
            self.log.debug(
                "Unable to query `%s` to collect `server_%s` tag, received error: %s", tag_endpoint, tag_name, e
            )

        return None
