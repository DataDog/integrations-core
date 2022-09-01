# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import API_SERVER_METRICS, APPLICATION_CONTROLLER_METRICS, REPO_SERVER_METRICS

class ArgocdCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'argocd'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(ArgocdCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        self.scraper_configs = []
        app_controller_endpoint = self.instance.get("app_controller_endpoint")
        api_server_endpoint = self.instance.get("api_server_endpoint")
        repo_server_endpoint = self.instance.get("repo_server_endpoint")
        if not app_controller_endpoint and not repo_server_endpoint and not api_server_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following:"
                "`app_controller_endpoint`, `repo_server_endpoint` or `api_server_endpoint`."
            )

        if app_controller_endpoint:
            self.scraper_configs.append(self._generate_config(app_controller_endpoint, APPLICATION_CONTROLLER_METRICS))
        if api_server_endpoint:
            self.scraper_configs.append(self._generate_config(api_server_endpoint, API_SERVER_METRICS))
        if repo_server_endpoint:
            self.scraper_configs.append(self._generate_config(repo_server_endpoint, REPO_SERVER_METRICS))

    def _generate_config(self, endpoint, metrics):
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
        }
        config.update(self.instance)
        return config

