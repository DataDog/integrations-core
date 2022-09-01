# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative

from .metrics import METRIC_MAP


class TeamCityCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teamcity'
    DEFAULT_METRIC_LIMIT = 0

    DEFAULT_METRICS_URL = "/{}/app/metrics"
    EXPERIMENTAL_METRICS_URL = "/{}/app/metrics?experimental=true"

    def __init__(self, name, init_config, instances):
        super(TeamCityCheckV2, self).__init__(name, init_config, instances)
        self.basic_http_auth = is_affirmative(self.instance.get('basic_http_authentication'))
        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        parsed_endpoint = urlparse(self.instance.get('server'))
        self.server_url = "{}://{}".format(parsed_endpoint.scheme, parsed_endpoint.netloc)
        self.metrics_endpoint = ''

        experimental_metrics = is_affirmative(self.instance.get('experimental_metrics', True))

        if experimental_metrics:
            self.metrics_endpoint = self.EXPERIMENTAL_METRICS_URL.format(self.auth_type)
        else:
            self.metrics_endpoint = self.DEFAULT_METRICS_URL.format(self.auth_type)

    def configure_scrapers(self):
        config = deepcopy(self.instance)
        config['openmetrics_endpoint'] = "{}{}".format(self.server_url, self.metrics_endpoint)

        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}
