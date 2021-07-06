# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from contextlib import contextmanager
from copy import deepcopy

from datadog_checks.avi_vantage import metrics
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.errors import CheckException

from .config_models import ConfigMixin

RESOURCE_METRICS = {
    'virtualservice': metrics.VIRTUAL_SERVICE_METRICS,
    'pool': metrics.POOL_METRICS,
    'controller': metrics.CONTROLLER_METRICS,
    'serviceengine': metrics.SERVICE_ENGINE_METRICS,
}


class AviVantageCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = "avi_vantage"

    def __init__(self, name, init_config, instances):
        super(AviVantageCheck, self).__init__(name, init_config, instances)
        # Required for storing the auth cookie
        self.instance['persist_connections'] = True

        self.collect_events = False
        self.last_event_time = None

    def get_resource_filters_for_entity(self, entity):
        return

    def configure_scrapers(self):
        scrapers = {}

        base_url = self.config.avi_controller_url.rstrip('/') + "/api/analytics/prometheus-metrics/"
        for entity in self.config.entities:
            if entity not in RESOURCE_METRICS:
                raise CheckException(
                    f"Entity {entity} is not valid. Must be one of {', '.join(RESOURCE_METRICS.keys())}."
                )
            resource_metrics = RESOURCE_METRICS[entity]
            instance_copy = deepcopy(self.instance)
            endpoint = base_url + entity
            instance_copy['openmetrics_endpoint'] = endpoint
            instance_copy['metrics'] = [resource_metrics]

            scrapers[endpoint] = self.create_scraper(instance_copy)

        self.scrapers.clear()
        self.scrapers.update(scrapers)

    @contextmanager
    def login(self):
        base_url = self.config.avi_controller_url.rstrip('/')
        login_url = base_url + "/login"
        logout_url = base_url + "/logout"
        login_resp = self.http.post(
            login_url, data={'username': self.config.username, 'password': self.config.password}
        )
        login_resp.raise_for_status()
        yield
        csrf_token = self.http.session.cookies.get('csrftoken')
        if csrf_token:
            logout_resp = self.http.post(logout_url, extra_headers={'X-CSRFToken': csrf_token, 'Referer': base_url})
            logout_resp.raise_for_status()

    def create_scraper(self, config):
        scraper = super(AviVantageCheck, self).create_scraper(config)
        scraper.http = self.http
        return scraper

    def _collect_events(self):
        pass
        # events_url = self.base_url + "/api/analytics/logs"
        # if not self.last_event_time:
        #     params = {'type': 2, 'page_size': 1, 'duration': 3600}
        # else:
        #     start_time = self.last_event_time + timedelta(microseconds=1)
        #     params = {'type': 2, 'page_size': 1000, 'start': start_time.replace(tzinfo=None).isoformat()}
        #
        # events_resp = self.http.get(events_url, params=params)

    def check(self, _):
        with self.login():
            super(AviVantageCheck, self).check(None)
            if self.collect_events:
                self._collect_events()
