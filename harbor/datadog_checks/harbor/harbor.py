# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.harbor.common import HarborAPI


class HarborCheck(AgentCheck):
    def __init__(self, *args, **kwargs):
        super(HarborCheck, self).__init__(*args, **kwargs)
        del self.http.options['auth']
        self.http.persist_connections = True

    def _check_health(self, api, base_tags):
        if api.harbor_version >= [1, 8, 0]:
            health = api.health()
            overall_status = AgentCheck.OK if health['status'] == 'healthy' else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            for el in health['components']:
                component_status = AgentCheck.OK if el['status'] == 'healthy' else AgentCheck.CRITICAL
                self.service_check('harbor.component.{}.status'.format(el['name']), component_status, tags=base_tags)
        elif api.harbor_version >= [1, 5, 0]:
            ping = api.ping()
            overall_status = AgentCheck.OK if ping == 'Pong' else AgentCheck.CRITICAL
            self.service_check('harbor.status', overall_status, tags=base_tags)
            if api.with_chartrepo:
                try:
                    chartrepo_health = api.chartrepo_health()['healthy']
                except HTTPError as e:
                    if e.response.status_code == 403:
                        self.log.warning(
                            "Provided user in harbor integration config is not an admin user. Ignoring chartrepo health"
                        )
                        return
                    raise e
                chartrepo_status = AgentCheck.OK if chartrepo_health else AgentCheck.CRITICAL
                self.service_check('harbor.component.chartmuseum.status', chartrepo_status, tags=base_tags)
        else:
            # Before version 1.5, there is no support for a health check. Service is marked as healthy by default.
            # If API was not reachable, code would have failed before.
            self.service_check('harbor.status', AgentCheck.OK, tags=base_tags)

    def _check_registries_health(self, api, base_tags):
        try:
            registries = api.registries()
        except HTTPError as e:
            if e.response.status_code == 403:
                # Forbidden, user is not admin
                self.log.warning(
                    "Provided user in harbor integration config is not an admin user. Ignoring registries health checks"
                )
                return
            raise e

        tags = list(base_tags)
        tags.append('')
        for registry in registries:
            name = registry['name']
            tags[-1] = 'registry:{}'.format(name.lower())
            if registry.get('status'):
                status = AgentCheck.OK if registry['status'] == 'healthy' else AgentCheck.CRITICAL
                self.service_check('harbor.registry.status', status, tags=tags)
            else:
                try:
                    api.registry_health(registry['id'])
                    self.service_check('harbor.registry.status', AgentCheck.OK, tags=tags)
                except HTTPError:
                    self.service_check('harbor.registry.status', AgentCheck.CRITICAL, tags=tags)

    def _submit_project_metrics(self, api, base_tags):
        projects = api.projects()
        for project in projects:
            tags = list(base_tags)
            if "metadata" in project and "public" in project['metadata']:
                is_public = project['metadata']['public']
                tags.append("public:{}".format(is_public))
            owner_name = project.get('owner_name')
            if owner_name:
                tags.append("owner_name:{}".format(owner_name.lower()))

            self.count('harbor.projects.count', 1, tags=tags)
        self.log.debug("Found {count} Harbor projects", {'count': len(projects)})

    def _submit_disk_metrics(self, api, base_tags):
        try:
            volume_info = api.volume_info()
        except HTTPError as e:
            if e.response.status_code == 403:
                # Forbidden, user is not admin
                self.log.warning(
                    "Provided user in harbor integration config is not an admin user. Ignoring volume metrics"
                )
                return
            raise e
        disk_free = volume_info['storage']['free']
        disk_total = volume_info['storage']['total']
        self.gauge('harbor.disk.free', disk_free, tags=base_tags)
        self.gauge('harbor.disk.total', disk_total, tags=base_tags)

    def check(self, instance):
        harbor_url = instance["url"]
        tags = instance.get("tags", [])
        try:
            api = HarborAPI(harbor_url, self.http)
            api.authenticate(instance["username"], instance['password'])
            self._check_health(api, tags)
        except Exception:
            self.log.error("Harbor API is not reachable")
            self.service_check('harbor.status', AgentCheck.CRITICAL)
            raise
        self._check_registries_health(api, tags)
        self._submit_project_metrics(api, tags)
        self._submit_disk_metrics(api, tags)
