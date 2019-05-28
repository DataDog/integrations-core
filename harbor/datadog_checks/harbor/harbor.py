# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests import ConnectionError, HTTPError, Timeout, RequestException, ConnectTimeout
from requests.exceptions import InvalidURL

from datadog_checks.base import AgentCheck
from .common import *


class HarborCheck(AgentCheck):

    def _check_health(self, api, base_tags):
        if api.harbor_version >= [1, 8, 0]:
            health = api.health()
            overall_status = AgentCheck.OK if health['status'] == 'healthy' else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            for el in health['components']:
                component_status = AgentCheck.OK if el['status'] == 'healthy' else AgentCheck.CRITICAL
                self.service_check('harbor.{}.status'.format(el['name']), component_status, tags=base_tags)
        else:
            ping = api.ping()
            overall_status = AgentCheck.OK if ping == 'Pong' else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            if api.with_chartrepo:
                chartrepo_health = api.chartrepo_health()['healthy']
                chartrepo_status = AgentCheck.OK if chartrepo_health else AgentCheck.CRITICAL
                self.service_check('harbor.chartmuseum.status', chartrepo_status, tags=base_tags)

    def _check_registries_health(self, api, base_tags):
        registries = api.registries()
        for registry in registries:
            name = registry['name']
            status = AgentCheck.OK if registry['status'] == 'healthy' else AgentCheck.CRITICAL
            tags = base_tags + ['name:{}'.format(name)]
            self.service_check('harbor.registry.status', status, tags=tags)

    def _submit_project_metrics(self, api, base_tags):
        projects = api.projects()
        for project in projects:
            tags = list(base_tags)
            if "metadata" in project and "public" in project['metadata']:
                is_public = project['metadata']['public']
                tags.append("public:{}".format(is_public))
            owner_name = project.get('owner_name')
            if owner_name:
                tags.append("owner_name:{}".format(owner_name))

            self.count('harbor.projects.count', 1, tags=tags)
        self.log.debug("Found {count} Harbor projects", {'count': len(projects)})

    def _submit_disk_metrics(self, api, base_tags):
        volume_info = api.volume_info()
        disk_free = volume_info['storage']['free']
        disk_total = volume_info['storage']['total']
        self.gauge('harbor.disk.free', disk_free, base_tags)
        self.gauge('harbor.disk.total', disk_total, base_tags)

    def check(self, instance):
        harbor_url = instance["url"]
        tags = instance.get("tags", [])
        try:
            api = HarborAPI(harbor_url, self.http)
            self._check_health(api, tags)
        except Exception:
            self.log.error("Harbor API not reachable")
            self.service_check('harbor.status', AgentCheck.CRITICAL)
            raise
        api.authenticate(instance["username"], instance['password'])
        self._check_registries_health(api, tags)
        self._submit_project_metrics(api, tags)
        self._submit_disk_metrics(api, tags)
