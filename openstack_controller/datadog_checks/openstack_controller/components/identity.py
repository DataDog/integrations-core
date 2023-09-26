# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    KEYSTONE_DOMAINS_COUNT,
    KEYSTONE_DOMAINS_METRICS,
    KEYSTONE_DOMAINS_METRICS_PREFIX,
    KEYSTONE_DOMAINS_TAGS,
    KEYSTONE_GROUPS_COUNT,
    KEYSTONE_GROUPS_METRICS,
    KEYSTONE_GROUPS_METRICS_PREFIX,
    KEYSTONE_GROUPS_TAGS,
    KEYSTONE_GROUPS_USERS,
    KEYSTONE_LIMITS_METRICS,
    KEYSTONE_LIMITS_METRICS_PREFIX,
    KEYSTONE_LIMITS_TAGS,
    KEYSTONE_PROJECTS_COUNT,
    KEYSTONE_PROJECTS_METRICS,
    KEYSTONE_PROJECTS_METRICS_PREFIX,
    KEYSTONE_PROJECTS_TAGS,
    KEYSTONE_REGIONS_COUNT,
    KEYSTONE_REGIONS_METRICS,
    KEYSTONE_REGIONS_METRICS_PREFIX,
    KEYSTONE_REGIONS_TAGS,
    KEYSTONE_REGISTERED_LIMITS_METRICS,
    KEYSTONE_REGISTERED_LIMITS_METRICS_PREFIX,
    KEYSTONE_REGISTERED_LIMITS_TAGS,
    KEYSTONE_RESPONSE_TIME,
    KEYSTONE_SERVICE_CHECK,
    KEYSTONE_SERVICES_COUNT,
    KEYSTONE_SERVICES_METRICS,
    KEYSTONE_SERVICES_METRICS_PREFIX,
    KEYSTONE_SERVICES_TAGS,
    KEYSTONE_USERS_COUNT,
    KEYSTONE_USERS_METRICS,
    KEYSTONE_USERS_METRICS_PREFIX,
    KEYSTONE_USERS_TAGS,
    get_metrics_and_tags,
)


class Identity(Component):
    component_type = Component.Type.IDENTITY
    service_check_id = KEYSTONE_SERVICE_CHECK

    def __init__(self, check):
        super(Identity, self).__init__(self, check)

    # @Component.http_error()
    def authorize(self):
        self.check.api.authorize()

    @Component.http_error()
    def get_auth_projects(self):
        return self.check.api.get_auth_projects()

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error(service_check=True)
    def _report_response_time(self, tags):
        self.check.log.debug("reporting `%s` response time", Component.Type.IDENTITY.value)
        response_time = self.check.api.get_response_time(Component.Type.IDENTITY)
        self.check.log.debug("`%s` response time: %s", Component.Type.IDENTITY.value, response_time)
        self.check.gauge(KEYSTONE_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_regions(self, tags):
        data = self.check.api.get_identity_regions()
        self.check.log.debug("data: %s", data)
        for item in data:
            self.check.log.debug("item: %s", item)
            region = get_metrics_and_tags(
                item,
                tags=KEYSTONE_REGIONS_TAGS,
                prefix=KEYSTONE_REGIONS_METRICS_PREFIX,
                metrics=KEYSTONE_REGIONS_METRICS,
            )
            self.check.log.debug("region: %s", region)
            self.check.gauge(KEYSTONE_REGIONS_COUNT, 1, tags=tags + region['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_domains(self, tags):
        data = self.check.api.get_identity_domains()
        self.check.log.debug("data: %s", data)
        for item in data:
            self.check.log.debug("item: %s", item)
            domain = get_metrics_and_tags(
                item,
                tags=KEYSTONE_DOMAINS_TAGS,
                prefix=KEYSTONE_DOMAINS_METRICS_PREFIX,
                metrics=KEYSTONE_DOMAINS_METRICS,
            )
            self.check.log.debug("domain: %s", domain)
            self.check.gauge(KEYSTONE_DOMAINS_COUNT, 1, tags=tags + domain['tags'])
            for metric, value in domain['metrics'].items():
                self.check.gauge(metric, value, tags=tags + domain['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_projects(self, tags):
        data = self.check.api.get_identity_projects()
        for item in data:
            project = get_metrics_and_tags(
                item,
                tags=KEYSTONE_PROJECTS_TAGS,
                prefix=KEYSTONE_PROJECTS_METRICS_PREFIX,
                metrics=KEYSTONE_PROJECTS_METRICS,
            )
            self.check.log.debug("project: %s", project)
            self.check.gauge(KEYSTONE_PROJECTS_COUNT, 1, tags=tags + project['tags'])
            for metric, value in project['metrics'].items():
                self.check.gauge(metric, value, tags=tags + project['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_users(self, tags):
        data = self.check.api.get_identity_users()
        for item in data:
            user = get_metrics_and_tags(
                item,
                tags=KEYSTONE_USERS_TAGS,
                prefix=KEYSTONE_USERS_METRICS_PREFIX,
                metrics=KEYSTONE_USERS_METRICS,
            )
            self.check.log.debug("user: %s", user)
            self.check.gauge(KEYSTONE_USERS_COUNT, 1, tags=tags + user['tags'])
            for metric, value in user['metrics'].items():
                self.check.gauge(metric, value, tags=tags + user['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_groups(self, tags):
        data = self.check.api.get_identity_groups()
        for item in data:
            group = get_metrics_and_tags(
                item,
                tags=KEYSTONE_GROUPS_TAGS,
                prefix=KEYSTONE_GROUPS_METRICS_PREFIX,
                metrics=KEYSTONE_GROUPS_METRICS,
            )
            self.check.log.debug("group: %s", group)
            self.check.gauge(KEYSTONE_GROUPS_COUNT, 1, tags=tags + group['tags'])
            self._report_group_users(item['id'], tags + group['tags'])

    @Component.http_error()
    def _report_group_users(self, group_id, tags):
        users = self.check.api.get_identity_group_users(group_id)
        self.check.log.debug("users: %s", users)
        self.check.gauge(KEYSTONE_GROUPS_USERS, len(users), tags=tags)

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_services(self, tags):
        data = self.check.api.get_identity_services()
        for item in data:
            service = get_metrics_and_tags(
                item,
                tags=KEYSTONE_SERVICES_TAGS,
                prefix=KEYSTONE_SERVICES_METRICS_PREFIX,
                metrics=KEYSTONE_SERVICES_METRICS,
            )
            self.check.log.debug("service: %s", service)
            self.check.gauge(KEYSTONE_SERVICES_COUNT, 1, tags=tags + service['tags'])
            for metric, value in service['metrics'].items():
                self.check.gauge(metric, value, tags=tags + service['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_registered_limits(self, tags):
        data = self.check.api.get_identity_registered_limits()
        for item in data:
            registered_limit = get_metrics_and_tags(
                item,
                tags=KEYSTONE_REGISTERED_LIMITS_TAGS,
                prefix=KEYSTONE_REGISTERED_LIMITS_METRICS_PREFIX,
                metrics=KEYSTONE_REGISTERED_LIMITS_METRICS,
                lambda_name=lambda key: 'limit' if key == 'default_limit' else key,
            )
            self.check.log.debug("registered_limit: %s", registered_limit)
            for metric, value in registered_limit['metrics'].items():
                self.check.gauge(metric, value, tags=tags + registered_limit['tags'])

    @Component.register_global_metrics(Component.Type.IDENTITY)
    @Component.http_error()
    def _report_limits(self, tags):
        data = self.check.api.get_identity_limits()
        for item in data:
            limit = get_metrics_and_tags(
                item,
                tags=KEYSTONE_LIMITS_TAGS,
                prefix=KEYSTONE_LIMITS_METRICS_PREFIX,
                metrics=KEYSTONE_LIMITS_METRICS,
                lambda_name=lambda key: 'limit' if key == 'resource_limit' else key,
            )
            self.check.log.debug("limit: %s", limit)
            for metric, value in limit['metrics'].items():
                self.check.gauge(metric, value, tags=tags + limit['tags'])
