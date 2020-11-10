# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests import HTTPError

from datadog_checks.base import AgentCheck

from .api import HarborAPI
from .common import HEALTHY, VERSION_1_5, VERSION_1_8

CAN_CONNECT = 'harbor.can_connect'
REGISTRY_STATUS = 'harbor.registry.status'
STATUS = 'harbor.status'


class HarborCheck(AgentCheck):
    def _check_health(self, api, base_tags):
        """Submits service checks for Harbor individual components."""
        if api.harbor_version >= VERSION_1_8:
            health = api.health()
            for el in health['components']:
                component_status = AgentCheck.OK if el['status'] == HEALTHY else AgentCheck.CRITICAL
                tags = base_tags + ['component:{}'.format(el['name'])]
                self.service_check(STATUS, component_status, tags=tags)
        elif api.harbor_version >= VERSION_1_5:
            ping = api.ping()
            overall_status = AgentCheck.OK if ping == 'Pong' else AgentCheck.CRITICAL
            self.service_check(STATUS, overall_status, tags=base_tags)
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
                tags = base_tags + ['component:chartmuseum']
                self.service_check(STATUS, chartrepo_status, tags=tags)
        else:
            # Before version 1.5, there is no support for a health check.
            self.service_check(STATUS, AgentCheck.UNKNOWN, tags=base_tags)

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

        for registry in registries:
            registry_name = registry['name'].lower()
            tags = base_tags + ['registry:' + registry_name]
            if registry.get('status'):
                status = AgentCheck.OK if registry['status'] == HEALTHY else AgentCheck.CRITICAL
                self.service_check(REGISTRY_STATUS, status, tags=tags)
            else:
                try:
                    api.registry_health(registry['id'])
                    self.service_check(REGISTRY_STATUS, AgentCheck.OK, tags=tags)
                except HTTPError as e:
                    self.log.debug(e, exc_info=True)
                    self.service_check(REGISTRY_STATUS, AgentCheck.CRITICAL, tags=tags)

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

    def _submit_read_only_status(self, api, base_tags):
        read_only_status = api.read_only_status()
        if read_only_status is not None:
            self.gauge('harbor.registry.read_only', int(read_only_status), tags=base_tags)

    def check(self, _):
        harbor_url = self.instance["url"]
        tags = self.instance.get("tags", [])
        try:
            api = HarborAPI(harbor_url, self.http)
            self._check_health(api, tags)
            self._check_registries_health(api, tags)
            self._submit_project_metrics(api, tags)
            self._submit_disk_metrics(api, tags)
            self._submit_read_only_status(api, tags)
        except Exception:
            self.log.exception("An error occured when collecting Harbor metrics")
            self.service_check(CAN_CONNECT, AgentCheck.CRITICAL)
            raise
        else:
            self.service_check(CAN_CONNECT, AgentCheck.OK)
