# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests import HTTPError

from datadog_checks.base import AgentCheck

from .api import HarborAPI
from .common import HEALTHY, VERSION_1_5, VERSION_1_8


class HarborCheck(AgentCheck):
    def __init__(self, *args, **kwargs):
        super(HarborCheck, self).__init__(*args, **kwargs)

        # Prevent the use of Basic Auth using `username` and `password` from the config file.
        del self.http.options['auth']

        # Keep a single session in order to submit the session id cookie for each request.
        self.http.persist_connections = True

    def _check_health(self, api, base_tags):
        """Submits service checks for Harbor individual components."""
        if api.harbor_version >= VERSION_1_8:
            health = api.health()
            overall_status = AgentCheck.OK if health['status'] == HEALTHY else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            for el in health['components']:
                component_status = AgentCheck.OK if el['status'] == HEALTHY else AgentCheck.CRITICAL
                self.service_check('harbor.component.{}.status'.format(el['name']), component_status, tags=base_tags)
        elif api.harbor_version >= VERSION_1_5:
            ping = api.ping()
            overall_status = AgentCheck.OK if ping == 'Pong' else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            if api.with_chartrepo:
                try:
                    chartrepo_health = api.chartrepo_health()[HEALTHY]
                except HTTPError as e:
                    if e.response.status_code == 403:
                        self.log.info(
                            "Provided user in harbor integration config is not an admin user. Ignoring chartrepo health"
                        )
                        self.log.debug(e, exc_info=True)
                        return
                    raise e
                chartrepo_status = AgentCheck.OK if chartrepo_health else AgentCheck.CRITICAL
                self.service_check('harbor.component.chartmuseum.status', chartrepo_status, tags=base_tags)
        else:
            # Before version 1.5, there is no support for a health check. In that case the integration submits OK if the
            # API is reachable and critical otherwise. Because at that point authentication has already been made,
            # Harbor is considered healthy.
            self.service_check('harbor.status', AgentCheck.OK, tags=base_tags)

    def _check_registries_health(self, api, base_tags):
        """A registry here is an external docker registry (DockerHub, ECR, another Harbor...) that this current
        instance of Harbor is using for replication purposes. The health of those services can be monitored within
        Harbor API."""
        try:
            registries = api.registries()
            self.log.debug("Found %d registries", len(registries))
        except HTTPError as e:
            if e.response.status_code == 403:
                # Forbidden, user is not admin
                self.log.info(
                    "Provided user in harbor integration config is not an admin user. Ignoring registries health checks"
                )
                self.log.debug(e, exc_info=True)
                return
            raise e

        tags = list(base_tags)
        # One more item for the registry tag
        tags.append('')
        for registry in registries:
            name = registry['name']
            tags[-1] = 'registry:{}'.format(name.lower())
            if registry.get('status'):
                status = AgentCheck.OK if registry['status'] == HEALTHY else AgentCheck.CRITICAL
                self.service_check('harbor.registry.status', status, tags=tags)
            else:
                try:
                    api.registry_health(registry['id'])
                    self.service_check('harbor.registry.status', AgentCheck.OK, tags=tags)
                except HTTPError as e:
                    self.log.debug(e, exc_info=True)
                    self.service_check('harbor.registry.status', AgentCheck.CRITICAL, tags=tags)

    def _submit_project_metrics(self, api, base_tags):
        projects = api.projects()
        self.gauge('harbor.projects.count', len(projects), tags=base_tags)
        self.log.debug("Found %d Harbor projects", len(projects))

    def _submit_disk_metrics(self, api, base_tags):
        try:
            volume_info = api.volume_info()
        except HTTPError as e:
            if e.response.status_code == 403:
                # Forbidden, user is not admin
                self.log.warning(
                    "Provided user in harbor integration config is not an admin user. Ignoring volume metrics"
                )
                self.log.debug(e, exc_info=True)
                return
            raise e
        disk_free = volume_info['storage']['free']
        disk_total = volume_info['storage']['total']
        self.gauge('harbor.disk.free', disk_free, tags=base_tags)
        self.gauge('harbor.disk.total', disk_total, tags=base_tags)

    def check(self, instance):
        harbor_url = instance["url"]
        username = instance["username"]
        password = instance['password']
        tags = instance.get("tags", [])
        try:
            api = HarborAPI(harbor_url, self.http)
            api.authenticate(username, password)
            self._check_health(api, tags)
        except Exception:
            self.log.exception("Harbor API is not reachable")
            self.service_check('harbor.status', AgentCheck.CRITICAL)
            raise
        self._check_registries_health(api, tags)
        self._submit_project_metrics(api, tags)
        self._submit_disk_metrics(api, tags)
