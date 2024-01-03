# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    KEYSTONE_DOMAIN_COUNT,
    KEYSTONE_DOMAIN_METRICS,
    KEYSTONE_DOMAIN_METRICS_PREFIX,
    KEYSTONE_DOMAIN_TAGS,
    KEYSTONE_GROUP_COUNT,
    KEYSTONE_GROUP_METRICS,
    KEYSTONE_GROUP_METRICS_PREFIX,
    KEYSTONE_GROUP_TAGS,
    KEYSTONE_GROUP_USERS,
    KEYSTONE_LIMIT_METRICS,
    KEYSTONE_LIMIT_METRICS_PREFIX,
    KEYSTONE_LIMIT_TAGS,
    KEYSTONE_PROJECT_COUNT,
    KEYSTONE_PROJECT_METRICS,
    KEYSTONE_PROJECT_METRICS_PREFIX,
    KEYSTONE_PROJECT_TAGS,
    KEYSTONE_REGION_COUNT,
    KEYSTONE_REGION_METRICS,
    KEYSTONE_REGION_METRICS_PREFIX,
    KEYSTONE_REGION_TAGS,
    KEYSTONE_REGISTERED_LIMIT_METRICS,
    KEYSTONE_REGISTERED_LIMIT_METRICS_PREFIX,
    KEYSTONE_REGISTERED_LIMIT_TAGS,
    KEYSTONE_RESPONSE_TIME,
    KEYSTONE_SERVICE_CHECK,
    KEYSTONE_SERVICE_COUNT,
    KEYSTONE_SERVICE_METRICS,
    KEYSTONE_SERVICE_METRICS_PREFIX,
    KEYSTONE_SERVICE_TAGS,
    KEYSTONE_USER_COUNT,
    KEYSTONE_USER_METRICS,
    KEYSTONE_USER_METRICS_PREFIX,
    KEYSTONE_USER_TAGS,
    get_metrics_and_tags,
)


class Identity(Component):
    ID = Component.Id.IDENTITY
    TYPES = Component.Types.IDENTITY
    SERVICE_CHECK = KEYSTONE_SERVICE_CHECK

    def __init__(self, check):
        super(Identity, self).__init__(check)

    @Component.http_error()
    def authorize_user(self):
        self.check.api.authorize_user()

    @Component.http_error()
    def authorize_system(self):
        self.check.api.authorize_system()

    @Component.http_error()
    def authorize_project(self, project_id):
        self.check.api.authorize_project(project_id)

    @Component.http_error()
    def get_auth_projects(self):
        return self.check.api.get_auth_projects()

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Identity.ID.value)
        response_time = self.check.api.get_response_time(Identity.TYPES.value)
        self.check.log.debug("`%s` response time: %s", Identity.ID.value, response_time)
        self.check.gauge(KEYSTONE_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_regions(self, config, tags):
        report_regions = config.get('regions', True)
        if report_regions:
            data = self.check.api.get_identity_regions()
            self.check.log.debug("regions: %s", data)
            for item in data:
                region = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_REGION_TAGS,
                    prefix=KEYSTONE_REGION_METRICS_PREFIX,
                    metrics=KEYSTONE_REGION_METRICS,
                )
                self.check.log.debug("region: %s", region)
                self.check.gauge(KEYSTONE_REGION_COUNT, 1, tags=tags + region['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_domains(self, config, tags):
        report_domains = config.get('domains', True)
        if report_domains:
            data = self.check.api.get_identity_domains()
            self.check.log.debug("domains: %s", data)
            for item in data:
                domain = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_DOMAIN_TAGS,
                    prefix=KEYSTONE_DOMAIN_METRICS_PREFIX,
                    metrics=KEYSTONE_DOMAIN_METRICS,
                )
                self.check.log.debug("domain: %s", domain)
                self.check.gauge(KEYSTONE_DOMAIN_COUNT, 1, tags=tags + domain['tags'])
                for metric, value in domain['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + domain['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_projects(self, config, tags):
        report_projects = config.get('projects', True)
        if report_projects:
            data = self.check.api.get_identity_projects()
            self.check.log.debug("projects: %s", data)
            for item in data:
                project = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_PROJECT_TAGS,
                    prefix=KEYSTONE_PROJECT_METRICS_PREFIX,
                    metrics=KEYSTONE_PROJECT_METRICS,
                )
                self.check.log.debug("project: %s", project)
                self.check.gauge(KEYSTONE_PROJECT_COUNT, 1, tags=tags + project['tags'])
                for metric, value in project['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + project['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_users(self, config, tags):
        report_users = config.get('users', True)
        if report_users:
            data = self.check.api.get_identity_users()
            self.check.log.debug("users: %s", data)
            for item in data:
                user = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_USER_TAGS,
                    prefix=KEYSTONE_USER_METRICS_PREFIX,
                    metrics=KEYSTONE_USER_METRICS,
                )
                self.check.log.debug("user: %s", user)
                self.check.gauge(KEYSTONE_USER_COUNT, 1, tags=tags + user['tags'])
                for metric, value in user['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + user['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_groups(self, config, tags):
        report_groups = config.get('groups', True)
        if report_groups:
            data = self.check.api.get_identity_groups()
            self.check.log.debug("groups: %s", data)
            for item in data:
                group = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_GROUP_TAGS,
                    prefix=KEYSTONE_GROUP_METRICS_PREFIX,
                    metrics=KEYSTONE_GROUP_METRICS,
                )
                self.check.log.debug("group: %s", group)
                self.check.gauge(KEYSTONE_GROUP_COUNT, 1, tags=tags + group['tags'])
                self._report_group_users(item['id'], tags + group['tags'])

    @Component.http_error()
    def _report_group_users(self, group_id, tags):
        users = self.check.api.get_identity_group_users(group_id)
        self.check.log.debug("users: %s", users)
        self.check.gauge(KEYSTONE_GROUP_USERS, len(users), tags=tags)

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_services(self, config, tags):
        report_services = config.get('services', True)
        if report_services:
            data = self.check.api.get_identity_services()
            self.check.log.debug("identity services: %s", data)
            for item in data:
                service = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_SERVICE_TAGS,
                    prefix=KEYSTONE_SERVICE_METRICS_PREFIX,
                    metrics=KEYSTONE_SERVICE_METRICS,
                )
                self.check.log.debug("service: %s", service)
                self.check.gauge(KEYSTONE_SERVICE_COUNT, 1, tags=tags + service['tags'])
                for metric, value in service['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + service['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_registered_limits(self, config, tags):
        report_limits = config.get('limits', True)
        if report_limits:
            data = self.check.api.get_identity_registered_limits()
            self.check.log.debug("registered limits: %s", data)
            for item in data:
                registered_limit = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_REGISTERED_LIMIT_TAGS,
                    prefix=KEYSTONE_REGISTERED_LIMIT_METRICS_PREFIX,
                    metrics=KEYSTONE_REGISTERED_LIMIT_METRICS,
                    lambda_name=lambda key: 'limit' if key == 'default_limit' else key,
                )
                self.check.log.debug("registered limit: %s", registered_limit)
                for metric, value in registered_limit['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + registered_limit['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_limits(self, config, tags):
        report_limits = config.get('limits', True)
        if report_limits:
            data = self.check.api.get_identity_limits()
            self.check.log.debug("limits: %s", data)
            for item in data:
                limit = get_metrics_and_tags(
                    item,
                    tags=KEYSTONE_LIMIT_TAGS,
                    prefix=KEYSTONE_LIMIT_METRICS_PREFIX,
                    metrics=KEYSTONE_LIMIT_METRICS,
                    lambda_name=lambda key: 'limit' if key == 'resource_limit' else key,
                )
                self.check.log.debug("limit: %s", limit)
                for metric, value in limit['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + limit['tags'])
