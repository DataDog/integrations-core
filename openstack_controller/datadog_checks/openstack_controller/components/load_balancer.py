# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    OCTAVIA_AMPHORA_STATS_METRICS,
    OCTAVIA_AMPHORA_STATS_METRICS_PREFIX,
    OCTAVIA_AMPHORA_STATS_TAGS,
    OCTAVIA_AMPHORAE_COUNT,
    OCTAVIA_AMPHORAE_METRICS,
    OCTAVIA_AMPHORAE_METRICS_PREFIX,
    OCTAVIA_AMPHORAE_TAGS,
    OCTAVIA_HEALTHMONITORS_COUNT,
    OCTAVIA_HEALTHMONITORS_METRICS,
    OCTAVIA_HEALTHMONITORS_METRICS_PREFIX,
    OCTAVIA_HEALTHMONITORS_TAGS,
    OCTAVIA_LISTENER_STATS_METRICS,
    OCTAVIA_LISTENER_STATS_METRICS_PREFIX,
    OCTAVIA_LISTENERS_COUNT,
    OCTAVIA_LISTENERS_METRICS,
    OCTAVIA_LISTENERS_METRICS_PREFIX,
    OCTAVIA_LISTENERS_TAGS,
    OCTAVIA_LOAD_BALANCER_STATS_METRICS,
    OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX,
    OCTAVIA_LOAD_BALANCERS_COUNT,
    OCTAVIA_LOAD_BALANCERS_METRICS,
    OCTAVIA_LOAD_BALANCERS_METRICS_PREFIX,
    OCTAVIA_LOAD_BALANCERS_TAGS,
    OCTAVIA_POOL_MEMBERS_COUNT,
    OCTAVIA_POOL_MEMBERS_METRICS,
    OCTAVIA_POOL_MEMBERS_METRICS_PREFIX,
    OCTAVIA_POOL_MEMBERS_TAGS,
    OCTAVIA_POOLS_COUNT,
    OCTAVIA_POOLS_METRICS,
    OCTAVIA_POOLS_METRICS_PREFIX,
    OCTAVIA_POOLS_TAGS,
    OCTAVIA_QUOTAS_COUNT,
    OCTAVIA_QUOTAS_METRICS,
    OCTAVIA_QUOTAS_METRICS_PREFIX,
    OCTAVIA_QUOTAS_TAGS,
    OCTAVIA_RESPONSE_TIME,
    OCTAVIA_SERVICE_CHECK,
    get_metrics_and_tags,
)


class LoadBalancer(Component):
    ID = Component.Id.LOAD_BALANCER
    TYPES = Component.Types.LOAD_BALANCER
    SERVICE_CHECK = OCTAVIA_SERVICE_CHECK

    def __init__(self, check):
        super(LoadBalancer, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", LoadBalancer.ID.value)
        response_time = self.check.api.get_response_time(LoadBalancer.TYPES.value)
        self.check.log.debug("`%s` response time: %s", LoadBalancer.ID.value, response_time)
        self.check.gauge(OCTAVIA_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_loadbalancers(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_loadbalancers(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            loadbalancer = get_metrics_and_tags(
                item,
                tags=OCTAVIA_LOAD_BALANCERS_TAGS,
                prefix=OCTAVIA_LOAD_BALANCERS_METRICS_PREFIX,
                metrics=OCTAVIA_LOAD_BALANCERS_METRICS,
            )
            self.check.log.debug("loadbalancer: %s", loadbalancer)
            self.check.gauge(OCTAVIA_LOAD_BALANCERS_COUNT, 1, tags=tags + loadbalancer['tags'])
            for metric, value in loadbalancer['metrics'].items():
                self.check.gauge(metric, value, tags=tags + loadbalancer['tags'])
            self._report_loadbalancer_stats(item['id'], tags + loadbalancer['tags'])

    @Component.http_error()
    def _report_loadbalancer_stats(self, loadbalancer_id, tags):
        data = self.check.api.get_load_balancer_loadbalancer_stats(loadbalancer_id)
        self.check.log.debug("data: %s", data)
        loadbalancer_stats = get_metrics_and_tags(
            data,
            tags=OCTAVIA_LOAD_BALANCERS_TAGS,
            prefix=OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX,
            metrics=OCTAVIA_LOAD_BALANCER_STATS_METRICS,
        )
        self.check.log.debug("loadbalancer_stats: %s", loadbalancer_stats)
        for metric, value in loadbalancer_stats['metrics'].items():
            self.check.gauge(metric, value, tags=tags + loadbalancer_stats['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_listeners(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_listeners(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            listener = get_metrics_and_tags(
                item,
                tags=OCTAVIA_LISTENERS_TAGS,
                prefix=OCTAVIA_LISTENERS_METRICS_PREFIX,
                metrics=OCTAVIA_LISTENERS_METRICS,
            )
            self.check.log.debug("listener: %s", listener)
            self.check.gauge(OCTAVIA_LISTENERS_COUNT, 1, tags=tags + listener['tags'])
            for metric, value in listener['metrics'].items():
                self.check.gauge(metric, value, tags=tags + listener['tags'])
            self._report_listener_stats(item['id'], tags + listener['tags'])

    @Component.http_error()
    def _report_listener_stats(self, listener_id, tags):
        data = self.check.api.get_load_balancer_listener_stats(listener_id)
        self.check.log.debug("data: %s", data)
        listener_stats = get_metrics_and_tags(
            data,
            tags=OCTAVIA_LISTENERS_TAGS,
            prefix=OCTAVIA_LISTENER_STATS_METRICS_PREFIX,
            metrics=OCTAVIA_LISTENER_STATS_METRICS,
        )
        self.check.log.debug("listener_stats: %s", listener_stats)
        for metric, value in listener_stats['metrics'].items():
            self.check.gauge(metric, value, tags=tags + listener_stats['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_pools(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_pools(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            pool = get_metrics_and_tags(
                item,
                tags=OCTAVIA_POOLS_TAGS,
                prefix=OCTAVIA_POOLS_METRICS_PREFIX,
                metrics=OCTAVIA_POOLS_METRICS,
            )
            self.check.log.debug("pool: %s", pool)
            self.check.gauge(OCTAVIA_POOLS_COUNT, 1, tags=tags + pool['tags'])
            for metric, value in pool['metrics'].items():
                self.check.gauge(metric, value, tags=tags + pool['tags'])
            self._report_pool_members(item['id'], project_id, tags)

    @Component.http_error()
    def _report_pool_members(self, pool_id, project_id, tags):
        data = self.check.api.get_load_balancer_pool_members(pool_id, project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            pool = get_metrics_and_tags(
                item,
                tags=OCTAVIA_POOL_MEMBERS_TAGS,
                prefix=OCTAVIA_POOL_MEMBERS_METRICS_PREFIX,
                metrics=OCTAVIA_POOL_MEMBERS_METRICS,
            )
            self.check.log.debug("pool: %s", pool)
            self.check.gauge(OCTAVIA_POOL_MEMBERS_COUNT, 1, tags=tags + pool['tags'])
            for metric, value in pool['metrics'].items():
                self.check.gauge(metric, value, tags=tags + pool['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_healthmonitors(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_healthmonitors(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            healthmonitor = get_metrics_and_tags(
                item,
                tags=OCTAVIA_HEALTHMONITORS_TAGS,
                prefix=OCTAVIA_HEALTHMONITORS_METRICS_PREFIX,
                metrics=OCTAVIA_HEALTHMONITORS_METRICS,
            )
            self.check.log.debug("healthmonitor: %s", healthmonitor)
            self.check.gauge(OCTAVIA_HEALTHMONITORS_COUNT, 1, tags=tags + healthmonitor['tags'])
            for metric, value in healthmonitor['metrics'].items():
                self.check.gauge(metric, value, tags=tags + healthmonitor['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_quotas(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_quotas(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            quota = get_metrics_and_tags(
                item,
                tags=OCTAVIA_QUOTAS_TAGS,
                prefix=OCTAVIA_QUOTAS_METRICS_PREFIX,
                metrics=OCTAVIA_QUOTAS_METRICS,
                lambda_value=lambda key, value, item=item: -1 if value is None else value,
            )
            self.check.log.debug("quota: %s", quota)
            self.check.gauge(OCTAVIA_QUOTAS_COUNT, 1, tags=tags + quota['tags'])
            for metric, value in quota['metrics'].items():
                self.check.gauge(metric, value, tags=tags + quota['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_amphorae(self, project_id, tags, component_config):
        data = self.check.api.get_load_balancer_amphorae(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            amphora = get_metrics_and_tags(
                item,
                tags=OCTAVIA_AMPHORAE_TAGS,
                prefix=OCTAVIA_AMPHORAE_METRICS_PREFIX,
                metrics=OCTAVIA_AMPHORAE_METRICS,
                lambda_value=lambda key, value, item=item: -1 if value is None else value,
            )
            self.check.log.debug("amphora: %s", amphora)
            self.check.gauge(OCTAVIA_AMPHORAE_COUNT, 1, tags=tags + amphora['tags'])
            for metric, value in amphora['metrics'].items():
                self.check.gauge(metric, value, tags=tags + amphora['tags'])
            self._report_amphora_stats(item['id'], tags + amphora['tags'])

    @Component.http_error()
    def _report_amphora_stats(self, amphora_id, tags):
        data = self.check.api.get_load_balancer_amphora_stats(amphora_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            amphora_stat = get_metrics_and_tags(
                item,
                tags=OCTAVIA_AMPHORA_STATS_TAGS,
                prefix=OCTAVIA_AMPHORA_STATS_METRICS_PREFIX,
                metrics=OCTAVIA_AMPHORA_STATS_METRICS,
            )
            self.check.log.debug("amphora_stat: %s", amphora_stat)
            for metric, value in amphora_stat['metrics'].items():
                self.check.gauge(metric, value, tags=tags + amphora_stat['tags'])
