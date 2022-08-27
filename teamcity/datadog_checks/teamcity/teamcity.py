# (C) Datadog, Inc. 2014-present
# (C) Paul Kirby <pkirby@matrix-solutions.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from urllib.parse import urlparse

from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2
from datadog_checks.base.config import _is_affirmative

from .config_models import ConfigMixin
from .events import collect_events
from .metrics import METRIC_MAP


class TeamCityCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'teamcity'
    DEFAULT_METRIC_LIMIT = 0

    DEFAULT_METRICS_URL = "/{}/app/metrics"
    EXPERIMENTAL_METRICS_URL = "/{}/app/metrics?experimental=true"

    HTTP_CONFIG_REMAPPER = {
        'ssl_validation': {'name': 'tls_verify'},
        'headers': {'name': 'headers', 'default': {"Accept": "application/json"}},
    }

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if _is_affirmative(instance['use_openmetrics']):
            if PY2:
                raise ConfigurationError(
                    "This version of the integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information or use the older style config."
                )
            # TODO: when we drop Python 2 move this import up top

        return super(TeamCityCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(TeamCityCheck, self).__init__(name, init_config, instances)
        # # Keep track of last build IDs per instance
        self.last_build_ids = {}
        self.name = self.instance.get('name')
        self.server = self.instance.get('server')
        self.host = self.instance.get('host_affected') or self.hostname
        self.build_config = self.instance.get('build_configuration')
        self.is_deployment = _is_affirmative(self.instance.get("is_deployment", False))
        self.basic_auth = self.instance.get('basic_http_authentication', False)
        self.auth_type = 'httpAuth' if self.basic_auth else 'guestAuth'
        self.metrics_endpoint = ''
        self.collect_events = self.instance.get('collect_events', True)
        self.use_openmetrics = self.instance.get('use_openmetrics', False)

        experimental_metrics = self.instance.get('experimental_metrics', True)
        parsed_endpoint = urlparse(self.server)

        self.base_url = "{}://{}".format(parsed_endpoint.scheme, parsed_endpoint.netloc)

        if experimental_metrics:
            self.metrics_endpoint = self.EXPERIMENTAL_METRICS_URL.format(self.auth_type)
        else:
            self.metrics_endpoint = self.DEFAULT_METRICS_URL.format(self.auth_type)

    def check(self, instance):
        if self.collect_events:
            collect_events(self, instance)

        if self.use_openmetrics:
            super().check(instance)

    def configure_scrapers(self):
        config = deepcopy(self.instance)
        config['openmetrics_endpoint'] = "{}{}".format(self.base_url, self.metrics_endpoint)

        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}
