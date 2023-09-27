# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.metrics import (
    OCTAVIA_LISTENER_COUNT,
    OCTAVIA_LISTENER_METRICS,
    OCTAVIA_LISTENER_METRICS_PREFIX,
    OCTAVIA_LISTENER_STATS_METRICS,
    OCTAVIA_LISTENER_STATS_METRICS_PREFIX,
    OCTAVIA_LISTENER_TAGS,
    OCTAVIA_LOAD_BALANCER_COUNT,
    OCTAVIA_LOAD_BALANCER_METRICS,
    OCTAVIA_LOAD_BALANCER_METRICS_PREFIX,
    OCTAVIA_LOAD_BALANCER_STATS_METRICS,
    OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX,
    OCTAVIA_LOAD_BALANCER_TAGS,
    OCTAVIA_RESPONSE_TIME,
    OCTAVIA_SERVICE_CHECK,
    get_metrics_and_tags,
)


class LoadBalancer(Component):
    component_id = Component.Id.LOAD_BALANCER
    component_types = Component.Types.LOAD_BALANCER
    service_check_id = OCTAVIA_SERVICE_CHECK

    def __init__(self, check):
        super(LoadBalancer, self).__init__(self, check)

    @Component.register_global_metrics(Component.Id.LOAD_BALANCER)
    @Component.http_error(service_check=True)
    def _report_response_time(self, tags):
        self.check.log.debug("reporting `%s` response time", Component.Id.LOAD_BALANCER.value)
        response_time = self.check.api.get_response_time(
            Component.Id.LOAD_BALANCER, Component.Types.LOAD_BALANCER.value
        )
        self.check.log.debug("`%s` response time: %s", Component.Id.LOAD_BALANCER.value, response_time)
        self.check.gauge(OCTAVIA_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(Component.Id.LOAD_BALANCER)
    @Component.http_error()
    def _report_loadbalancers(self, project_id, tags):
        data = self.check.api.get_load_balancer_loadbalancers(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            loadbalancer = get_metrics_and_tags(
                item,
                tags=OCTAVIA_LOAD_BALANCER_TAGS,
                prefix=OCTAVIA_LOAD_BALANCER_METRICS_PREFIX,
                metrics=OCTAVIA_LOAD_BALANCER_METRICS,
            )
            self.check.log.debug("loadbalancer: %s", loadbalancer)
            self.check.gauge(OCTAVIA_LOAD_BALANCER_COUNT, 1, tags=tags + loadbalancer['tags'])
            for metric, value in loadbalancer['metrics'].items():
                self.check.gauge(metric, value, tags=tags + loadbalancer['tags'])
            self._report_loadbalancer_stats(item['id'], tags + loadbalancer['tags'])

    @Component.http_error()
    def _report_loadbalancer_stats(self, loadbalancer_id, tags):
        data = self.check.api.get_load_balancer_loadbalancer_stats(loadbalancer_id)
        self.check.log.debug("data: %s", data)
        loadbalancer_stats = get_metrics_and_tags(
            data,
            tags=OCTAVIA_LOAD_BALANCER_TAGS,
            prefix=OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX,
            metrics=OCTAVIA_LOAD_BALANCER_STATS_METRICS,
        )
        self.check.log.debug("loadbalancer_stats: %s", loadbalancer_stats)
        for metric, value in loadbalancer_stats['metrics'].items():
            self.check.gauge(metric, value, tags=tags + loadbalancer_stats['tags'])

    @Component.register_project_metrics(Component.Id.LOAD_BALANCER)
    @Component.http_error()
    def _report_listeners(self, project_id, tags):
        data = self.check.api.get_load_balancer_listeners(project_id)
        self.check.log.debug("data: %s", data)
        for item in data:
            listener = get_metrics_and_tags(
                item,
                tags=OCTAVIA_LISTENER_TAGS,
                prefix=OCTAVIA_LISTENER_METRICS_PREFIX,
                metrics=OCTAVIA_LISTENER_METRICS,
            )
            self.check.log.debug("listener: %s", listener)
            self.check.gauge(OCTAVIA_LISTENER_COUNT, 1, tags=tags + listener['tags'])
            for metric, value in listener['metrics'].items():
                self.check.gauge(metric, value, tags=tags + listener['tags'])
            self._report_listener_stats(item['id'], tags + listener['tags'])

    @Component.http_error()
    def _report_listener_stats(self, listener_id, tags):
        data = self.check.api.get_load_balancer_listener_stats(listener_id)
        self.check.log.debug("data: %s", data)
        listener_stats = get_metrics_and_tags(
            data,
            tags=OCTAVIA_LISTENER_TAGS,
            prefix=OCTAVIA_LISTENER_STATS_METRICS_PREFIX,
            metrics=OCTAVIA_LISTENER_STATS_METRICS,
        )
        self.check.log.debug("listener_stats: %s", listener_stats)
        for metric, value in listener_stats['metrics'].items():
            self.check.gauge(metric, value, tags=tags + listener_stats['tags'])
