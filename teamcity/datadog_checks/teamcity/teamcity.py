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
from .events import TeamCityEvents
from .metrics import METRIC_MAP
from .common import LAST_BUILD_URL


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
        self.instance = instances[0]
        self.instance_name = self.instance.get('name')
        self.last_build_ids = {}
        self.server = self.instance.get('server')
        self.host = self.instance.get('host_affected') or self.hostname
        self.basic_auth = self.instance.get('basic_http_authentication', False)
        self.auth_type = 'httpAuth' if self.basic_auth else 'guestAuth'
        self.build_config = self.instance.get('build_configuration')
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

        if self.collect_events:
            self.teamcity_events = TeamCityEvents(self.instance, self.base_url, self.host, self.auth_type)

    def check(self, instance):
        if self.use_openmetrics:
            super().check(instance)

        if self.collect_events:
            self._initialize_if_required()
            self.teamcity_events.collect_events(self, self.last_build_ids)

    def configure_scrapers(self):
        config = deepcopy(self.instance)
        config['openmetrics_endpoint'] = "{}{}".format(self.base_url, self.metrics_endpoint)

        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def _initialize_if_required(self):
        if self.instance_name in self.last_build_ids:
            return

        self.log.debug("Initializing %s", self.instance_name)
        last_build_url = LAST_BUILD_URL.format(
            server=self.base_url, auth_type=self.auth_type, build_conf=self.build_config
        )

        try:
            resp = self.http.get(last_build_url)
            resp.raise_for_status()
            last_build_id = resp.json().get("build")[0].get("id")

        except requests.exceptions.HTTPError:
            if resp.status_code == 401:
                self.log.error("Access denied. You must enable guest authentication")
            self.log.error(
                "Failed to retrieve last build ID with code %s for instance '%s'", resp.status_code, self.instance_name
            )
            raise
        except Exception:
            self.log.exception("Unhandled exception to get last build ID for instance '%s'", self.instance_name)
            raise
        self.log.debug("Last build id for instance %s is %s.", self.instance_name, last_build_id)
        self.last_build_ids[self.instance_name] = last_build_id
