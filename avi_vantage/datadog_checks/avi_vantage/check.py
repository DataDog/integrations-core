# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from copy import deepcopy

from datadog_checks.avi_vantage import metrics
from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.errors import CheckException

from .config_models import ConfigMixin

RESOURCE_METRICS = {
    'virtualservice': metrics.VIRTUAL_SERVICE_METRICS,
    'pool': metrics.POOL_METRICS,
    'controller': metrics.CONTROLLER_METRICS,
    'serviceengine': metrics.SERVICE_ENGINE_METRICS,
}
LABELS_REMAPPER = {'type': 'avi_type', 'tenant': 'avi_tenant'}


class AviVantageCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = "avi_vantage"

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(AviVantageCheck, self).__init__(name, init_config, instances)
        # Required for storing the auth cookie
        self.instance['persist_connections'] = True
        self._base_url = None

    @property
    def base_url(self):
        if not self._base_url:
            self._base_url = self.config.avi_controller_url.rstrip('/')
        return self._base_url

    def configure_scrapers(self):
        scrapers = {}

        for entity in self.config.entities:
            if entity not in RESOURCE_METRICS:
                raise CheckException(
                    f"Entity {entity} is not valid. Must be one of {', '.join(RESOURCE_METRICS.keys())}."
                )
            resource_metrics = RESOURCE_METRICS[entity]
            instance_copy = deepcopy(self.instance)
            endpoint = self.base_url + "/api/analytics/prometheus-metrics/" + entity
            instance_copy['openmetrics_endpoint'] = endpoint
            instance_copy['metrics'] = [resource_metrics]
            instance_copy['rename_labels'] = LABELS_REMAPPER.copy()
            instance_copy['rename_labels']['name'] = entity + "_name"
            if self.config.rename_labels is not None:
                instance_copy['rename_labels'].update(self.config.rename_labels)

            scrapers[endpoint] = self.create_scraper(instance_copy)

        self.scrapers.clear()
        self.scrapers.update(scrapers)

    @contextmanager
    def login(self):
        self.http._session = None
        login_url = self.base_url + "/login"
        logout_url = self.base_url + "/logout"
        try:
            login_resp = self.http.post(
                login_url, data={'username': self.config.username, 'password': self.config.password}
            )
            login_resp.raise_for_status()
        except Exception:
            self.service_check("can_connect", AgentCheck.CRITICAL, tags=self.config.tags)
            raise
        else:
            self.service_check("can_connect", AgentCheck.OK, tags=self.config.tags)

        yield
        csrf_token = self.http.session.cookies.get('csrftoken')
        if csrf_token:
            logout_resp = self.http.post(
                logout_url, extra_headers={'X-CSRFToken': csrf_token, 'Referer': self.base_url}
            )
            logout_resp.raise_for_status()

    @AgentCheck.metadata_entrypoint
    def collect_avi_version(self):
        response = self.http.get(self.base_url + "/api/cluster/version")
        response.raise_for_status()
        version = response.json()['Version']
        self.set_metadata('version', version)

    def create_scraper(self, config):
        scraper = super(AviVantageCheck, self).create_scraper(config)
        scraper.http = self.http
        return scraper

    def check(self, _):
        with self.login():
            try:
                self.collect_avi_version()
            except Exception:
                self.log.debug("Unable to fetch Avi version", exc_info=True)
            super(AviVantageCheck, self).check(None)
