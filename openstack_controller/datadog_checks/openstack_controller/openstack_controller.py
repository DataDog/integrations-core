# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


from typing import Any, Dict, List, Type  # noqa: F401

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.openstack_controller.api.factory import make_api
from datadog_checks.openstack_controller.components.bare_metal import BareMetal
from datadog_checks.openstack_controller.components.block_storage import BlockStorage
from datadog_checks.openstack_controller.components.compute import Compute
from datadog_checks.openstack_controller.components.identity import Identity
from datadog_checks.openstack_controller.components.load_balancer import LoadBalancer
from datadog_checks.openstack_controller.components.network import Network
from datadog_checks.openstack_controller.config import OpenstackConfig, normalize_discover_config_include

from .config_models import ConfigMixin


class OpenStackControllerCheck(AgentCheck, ConfigMixin):
    def __new__(cls, name, init_config, instances):
        # type: (Type[OpenStackControllerCheck], str, Dict[str, Any], List[Dict[str, Any]]) -> OpenStackControllerCheck
        """For backward compatibility reasons, there are two side-by-side implementations of OpenStackControllerCheck.
        Instantiating this class will return an instance of the legacy integration for existing users and
        an instance of the new implementation for new users."""
        if is_affirmative(instances[0].get('use_legacy_check_version', True)):
            from datadog_checks.openstack_controller.legacy.openstack_controller_legacy import (
                OpenStackControllerLegacyCheck,
            )

            return OpenStackControllerLegacyCheck(name, init_config, instances)  # type: ignore
        return super(OpenStackControllerCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(OpenStackControllerCheck, self).__init__(name, init_config, instances)
        self.check_initializations.append(self.init)

    def init(self):
        self.openstack_config = OpenstackConfig(self.log, self.instance)
        self.api = make_api(self.openstack_config, self.log, self.http)
        self.identity = Identity(self)
        self.components = [
            self.identity,
            Compute(self),
            Network(self),
            BlockStorage(self),
            BareMetal(self),
            LoadBalancer(self),
        ]
        config_projects_include = normalize_discover_config_include(
            self.config.projects if self.config.projects else {'include': list(self.config.whitelist_project_names)}
        )
        if config_projects_include:
            self.projects_discovery = Discovery(
                lambda: self.identity.get_auth_projects(),
                limit=self.config.projects.limit if self.config.projects else None,
                include=config_projects_include,
                exclude=self.config.projects.exclude if self.config.projects else self.config.blacklist_project_names,
                interval=self.config.projects.interval if self.config.projects else None,
                key=lambda project: project.get('name'),
            )
        else:
            self.projects_discovery = None

    def check(self, _instance):
        self.log.info("running check")
        tags = ['keystone_server:{}'.format(self.api.auth_url())] + self.instance.get('tags', [])
        self.gauge("openstack.controller", 1, tags=tags)
        if self.identity.authorize_user():
            self.log.info("User successfully authorized")
            self._start_report()
            self._report_metrics(tags)
            self._finish_report(tags)
        else:
            self.log.error("Error while authorizing user")

    def _start_report(self):
        for component in self.components:
            component.start_report()

    def _report_metrics(self, tags):
        self.log.info("reporting metrics")
        if self.identity.authorize_system():
            self._report_global_metrics(tags)
        if self.projects_discovery:
            discovered_projects = list(self.projects_discovery.get_items())
        else:
            discovered_projects = [
                (None, project.get('name'), project, None) for project in self.identity.get_auth_projects()
            ]
        for _pattern, _project_name, project, _project_config in discovered_projects:
            if self.identity.authorize_project(project['id']):
                self._report_global_metrics(tags)
                project_tags = tags + [
                    f"domain_id:{project['domain_id']}",
                    f"project_id:{project['id']}",
                    f"project_name:{project['name']}",
                ]
                self._report_project_metrics(project['id'], project_tags)

    def _finish_report(self, tags):
        for component in self.components:
            component.finish_report(tags)

    def _report_global_metrics(self, tags):
        self.log.info("reporting global metrics")
        for component in self.components:
            component.report_global_metrics(tags)

    def _report_project_metrics(self, project_id, tags):
        self.log.info("reporting project `%s` metrics", project_id)
        for component in self.components:
            component.report_project_metrics(project_id, tags)
