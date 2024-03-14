# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.config import normalize_discover_config_include
from datadog_checks.openstack_controller.metrics import (
    NOVA_FLAVORS_METRICS,
    NOVA_FLAVORS_METRICS_PREFIX,
    NOVA_FLAVORS_TAGS,
    NOVA_HYPERVISOR_COUNT,
    NOVA_HYPERVISOR_METRICS,
    NOVA_HYPERVISOR_METRICS_PREFIX,
    NOVA_HYPERVISOR_TAGS,
    NOVA_HYPERVISOR_UPTIME_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_LIMITS_METRICS_PREFIX,
    NOVA_LIMITS_TAGS,
    NOVA_QUOTA_SET_METRICS,
    NOVA_QUOTA_SET_METRICS_PREFIX,
    NOVA_QUOTA_SET_TAGS,
    NOVA_RESPONSE_TIME,
    NOVA_SERVER_COUNT,
    NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS,
    NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS_PREFIX,
    NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_TAGS,
    NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS,
    NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX,
    NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_TAGS,
    NOVA_SERVER_DIAGNOSTIC_METRICS,
    NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX,
    NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS,
    NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX,
    NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_TAGS,
    NOVA_SERVER_DIAGNOSTIC_TAGS,
    NOVA_SERVER_FLAVOR_METRICS,
    NOVA_SERVER_FLAVOR_METRICS_PREFIX,
    NOVA_SERVER_FLAVOR_TAGS,
    NOVA_SERVER_METRICS,
    NOVA_SERVER_METRICS_PREFIX,
    NOVA_SERVER_TAGS,
    NOVA_SERVICE_CHECK,
    NOVA_SERVICES_COUNT,
    NOVA_SERVICES_METRICS,
    NOVA_SERVICES_METRICS_PREFIX,
    NOVA_SERVICES_TAGS,
    get_metrics_and_tags,
    is_interface_metric,
)


class Compute(Component):
    ID = Component.Id.COMPUTE
    TYPES = Component.Types.COMPUTE
    SERVICE_CHECK = NOVA_SERVICE_CHECK

    def __init__(self, check):
        super(Compute, self).__init__(check)

    @Component.register_global_metrics(ID)
    @Component.http_error(report_service_check=True)
    def _report_response_time(self, global_components_config, tags):
        self.check.log.debug("reporting `%s` response time", Compute.ID.value)
        response_time = self.check.api.get_response_time(Compute.TYPES.value)
        self.check.log.debug("`%s` response time: %s", Compute.ID.value, response_time)
        self.check.gauge(NOVA_RESPONSE_TIME, response_time, tags=tags)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_limits(self, project_id, tags, config):
        report_limits = config.get('limits', True)
        if report_limits:
            item = self.check.api.get_compute_limits(project_id)

            limits = get_metrics_and_tags(
                item,
                tags=NOVA_LIMITS_TAGS,
                prefix=NOVA_LIMITS_METRICS_PREFIX,
                metrics=NOVA_LIMITS_METRICS,
            )
            self.check.log.debug("limits: %s", limits)
            for metric, value in limits['metrics'].items():
                self.check.gauge(metric, value, tags=tags + limits['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_services(self, config, tags):
        report_services = config.get('services', True)
        if report_services:
            data = self.check.api.get_compute_services()
            self.check.log.debug("compute services: %s", data)
            for item in data:
                service = get_metrics_and_tags(
                    item,
                    tags=NOVA_SERVICES_TAGS,
                    prefix=NOVA_SERVICES_METRICS_PREFIX,
                    metrics=NOVA_SERVICES_METRICS,
                    lambda_name=lambda key: 'up' if key == 'state' else key,
                    lambda_value=lambda key, value, item=item: (
                        (item['state'] == 'up' and item['status'] == 'enabled') if key == 'state' else value
                    ),
                )
                self.check.log.debug("service: %s", service)
                self.check.gauge(NOVA_SERVICES_COUNT, 1, tags=tags + service['tags'])
                for metric, value in service['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + service['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_flavors(self, config, tags):
        report_flavors = config.get('flavors', True)
        if report_flavors:
            data = self.check.api.get_compute_flavors()
            self.check.log.debug("flavors: %s", data)
            for item in data:
                flavor = get_metrics_and_tags(
                    item,
                    tags=NOVA_FLAVORS_TAGS,
                    prefix=NOVA_FLAVORS_METRICS_PREFIX,
                    metrics=NOVA_FLAVORS_METRICS,
                )
                self.check.log.debug("flavor: %s", flavor)
                for metric, value in flavor['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + flavor['tags'])

    @Component.register_global_metrics(ID)
    @Component.http_error()
    def _report_hypervisors(self, config, tags):
        report_hypervisors = True
        config_hypervisors = config.get('hypervisors', {})
        if isinstance(config_hypervisors, bool):
            report_hypervisors = config_hypervisors
            config_hypervisors = {}
        if report_hypervisors:
            hypervisors_discovery = None
            config_hypervisors_include = normalize_discover_config_include(config_hypervisors, ["hypervisor_hostname"])
            if config_hypervisors_include:
                hypervisors_discovery = Discovery(
                    lambda: self.check.api.get_compute_hypervisors(),
                    limit=config_hypervisors.get('limit'),
                    include=config_hypervisors_include,
                    exclude=config_hypervisors.get('exclude'),
                    interval=config_hypervisors.get('interval'),
                    key=lambda hypervisor: hypervisor.get('hypervisor_hostname'),
                )
            if hypervisors_discovery:
                discovered_hypervisors = list(hypervisors_discovery.get_items())
            else:
                discovered_hypervisors = [
                    (None, hypervisor.get('hypervisor_hostname'), hypervisor, None)
                    for hypervisor in self.check.api.get_compute_hypervisors()
                ]
            for _pattern, _item_name, item, item_config in discovered_hypervisors:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                hypervisor = get_metrics_and_tags(
                    item,
                    tags=NOVA_HYPERVISOR_TAGS,
                    prefix=NOVA_HYPERVISOR_METRICS_PREFIX,
                    metrics=NOVA_HYPERVISOR_METRICS,
                    lambda_name=lambda key: 'up' if key == 'state' else key,
                    lambda_value=lambda key, value, item=item: (
                        (item['state'] == 'up' and item['status'] == 'enabled') if key == 'state' else value
                    ),
                )
                self.check.log.debug("hypervisor: %s", hypervisor)
                hypervisor_hostname = item['hypervisor_hostname']
                hypervisor_tags = hypervisor['tags']
                self.check.gauge(NOVA_HYPERVISOR_COUNT, 1, tags=tags + hypervisor_tags, hostname=hypervisor_hostname)
                for metric, value in hypervisor['metrics'].items():
                    self.check.gauge(
                        metric,
                        value,
                        tags=tags + hypervisor_tags,
                        hostname=hypervisor_hostname,
                    )
                collect_uptime = item_config.get('uptime', True) if item_config else True
                if collect_uptime:
                    if item['hypervisor_type'] != 'ironic':
                        self._report_hypervisor_uptime(item, tags + hypervisor['tags'])
                    else:
                        self.check.log.debug(
                            "Skipping uptime metrics for bare metal hypervisor `%s`", item['hypervisor_hostname']
                        )
                self.check.external_tags.append((item['hypervisor_hostname'], {'openstack': ['host_type:hypervisor']}))

    @Component.http_error()
    def _report_hypervisor_uptime(self, hypervisor, tags):
        hypervisor_id = hypervisor['id']
        hypervisor_hostname = hypervisor['hypervisor_hostname']
        uptime = hypervisor.get('uptime')

        def _load_averages_from_uptime(uptime):
            load_averages = []
            if uptime:
                """Parse u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n'"""
                uptime = uptime.strip()
                load_averages = uptime[uptime.find('load average:') :].split(':')[1].strip().split(',')
                load_averages = [float(load_avg) for load_avg in load_averages]
            return load_averages

        if uptime is None:
            uptime = self.check.api.get_compute_hypervisor_uptime(hypervisor_id).get("uptime")
        uptime_metrics = {}
        load_averages = _load_averages_from_uptime(uptime)
        if load_averages and len(load_averages) == 3:
            for i, avg in enumerate([1, 5, 15]):
                uptime_metrics[f"load_{avg}"] = load_averages[i]
        uptime_metrics_and_tags = get_metrics_and_tags(
            uptime_metrics,
            tags=NOVA_HYPERVISOR_TAGS,
            prefix=NOVA_HYPERVISOR_METRICS_PREFIX,
            metrics=NOVA_HYPERVISOR_UPTIME_METRICS,
        )
        for metric, value in uptime_metrics_and_tags['metrics'].items():
            self.check.gauge(metric, value, tags=tags + uptime_metrics_and_tags['tags'], hostname=hypervisor_hostname)

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_quota_sets(self, project_id, tags, config):
        report_quota_sets = config.get('quota_sets', True)
        if report_quota_sets:
            item = self.check.api.get_compute_quota_sets(project_id)
            quota_set = get_metrics_and_tags(
                item,
                tags=NOVA_QUOTA_SET_TAGS,
                prefix=NOVA_QUOTA_SET_METRICS_PREFIX,
                metrics=NOVA_QUOTA_SET_METRICS,
            )
            self.check.log.debug("quota_set: %s", quota_set)
            for metric, value in quota_set['metrics'].items():
                self.check.gauge(metric, value, tags=tags + quota_set['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_servers(self, project_id, tags, config):
        report_servers = True
        config_servers = config.get('servers', {})
        if isinstance(config_servers, bool):
            report_servers = config_servers
            config_servers = {}
        if report_servers:
            servers_discovery = None
            if config_servers:
                config_servers_include = normalize_discover_config_include(config_servers, ["name"])
                self.check.log.debug("config_servers_include: %s", config_servers_include)
                if config_servers_include:
                    servers_discovery = Discovery(
                        lambda: self.check.api.get_compute_servers(project_id),
                        limit=config_servers.get('limit'),
                        include=config_servers_include,
                        exclude=config_servers.get('exclude'),
                        interval=config_servers.get('interval'),
                        key=lambda server: server.get('name'),
                    )
            if servers_discovery:
                discovered_servers = list(servers_discovery.get_items())
            else:
                discovered_servers = [
                    (None, server.get('name'), server, None)
                    for server in self.check.api.get_compute_servers(project_id)
                ]
            aggregates = self.check.api.get_compute_aggregates()
            self.check.log.debug("aggregates: %s", aggregates)
            for _pattern, _item_name, item, item_config in discovered_servers:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                server = get_metrics_and_tags(
                    item,
                    tags=NOVA_SERVER_TAGS,
                    prefix=NOVA_SERVER_METRICS_PREFIX,
                    metrics=NOVA_SERVER_METRICS,
                    lambda_name=lambda key, item=item: (
                        'active'
                        if key == 'status' and item['status'] == 'ACTIVE'
                        else 'error' if key == 'status' and item['status'] == 'ERROR' else key
                    ),
                    lambda_value=lambda key, value, item=item: (
                        1 if key == 'status' and (item['status'] == 'ACTIVE' or item['status'] == 'ERROR') else value
                    ),
                )
                self.check.log.debug("server: %s", server)
                self.check.gauge(NOVA_SERVER_COUNT, 1, tags=tags + server['tags'], hostname=item['id'])
                for metric, value in server['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + server['tags'], hostname=item['id'])
                collect_flavors = item_config.get('flavors', True) if item_config else True
                if collect_flavors:
                    self._report_server_flavor(item, tags + server['tags'])
                collect_diagnostics = item_config.get('diagnostics', True) if item_config else True
                if collect_diagnostics:
                    self._report_server_diagnostics(item, tags + server['tags'])
                report_external_tags = item_config.get('external_tags', True) if item_config else True
                if report_external_tags:
                    self._report_external_tags(item, aggregates)

    @Component.http_error()
    def _report_server_flavor(self, server, tags):
        flavor_id = server.get('flavor', {}).get('id')
        flavor_original_name = server.get('flavor', {}).get('original_name')
        flavor_metrics = {}
        if flavor_id and flavor_original_name is None:
            flavor_metrics = self.check.api.get_compute_flavor(flavor_id)
        else:
            flavor_metrics = server.get('flavor')
        self.check.log.debug("flavor_metrics: %s", flavor_metrics)
        flavor_metrics_and_tags = get_metrics_and_tags(
            flavor_metrics,
            tags=NOVA_SERVER_FLAVOR_TAGS,
            prefix=NOVA_SERVER_FLAVOR_METRICS_PREFIX,
            metrics=NOVA_SERVER_FLAVOR_METRICS,
        )
        self.check.log.debug("flavor_metrics_and_tags: %s", flavor_metrics_and_tags)
        for metric, value in flavor_metrics_and_tags['metrics'].items():
            self.check.gauge(metric, value, tags=tags + flavor_metrics_and_tags['tags'], hostname=server['id'])

    @Component.http_error()
    def _report_server_diagnostics(self, server, tags):
        server_id = server['id']
        item_diagnostic = self.check.api.get_compute_server_diagnostics(server_id)
        self.check.log.debug("server_diagnostics: %s", item_diagnostic)
        diagnostic = get_metrics_and_tags(
            item_diagnostic,
            tags=NOVA_SERVER_DIAGNOSTIC_TAGS,
            prefix=NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX,
            metrics=NOVA_SERVER_DIAGNOSTIC_METRICS,
        )
        self.check.log.debug("diagnostic: %s", diagnostic)
        for metric, value in diagnostic['metrics'].items():

            if is_interface_metric(metric):
                metric_pre = re.split("(_rx|_tx)", metric)

                interface = "interface:{}".format(metric_pre[0])
                self.check.gauge(
                    "{}.{}{}".format(
                        NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX, metric_pre[1].replace("_", ""), metric_pre[2]
                    ),
                    value,
                    tags=tags + diagnostic['tags'] + [interface],
                    hostname=server['id'],
                )
            else:
                self.check.gauge(metric, value, tags=tags + diagnostic['tags'], hostname=server['id'])
        for item_disk_details in item_diagnostic.get('disk_details', []):
            disk_detail = get_metrics_and_tags(
                item_disk_details,
                tags=NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_TAGS,
                prefix=NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX,
                metrics=NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS,
            )
            for metric, value in disk_detail['metrics'].items():
                self.check.gauge(
                    metric,
                    value,
                    tags=tags + diagnostic['tags'] + disk_detail['tags'],
                    hostname=server['id'],
                )
        for item_cpu_details in item_diagnostic.get('cpu_details', []):
            cpu_detail = get_metrics_and_tags(
                item_cpu_details,
                tags=NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_TAGS,
                prefix=NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS_PREFIX,
                metrics=NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS,
            )
            for metric, value in cpu_detail['metrics'].items():
                self.check.gauge(
                    metric,
                    value,
                    tags=tags + diagnostic['tags'] + cpu_detail['tags'],
                    hostname=server['id'],
                )
        for item_nic_details in item_diagnostic.get('nic_details', []):
            nic_detail = get_metrics_and_tags(
                item_nic_details,
                tags=NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_TAGS,
                prefix=NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX,
                metrics=NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS,
            )
            for metric, value in nic_detail['metrics'].items():
                self.check.gauge(
                    metric,
                    value,
                    tags=tags + diagnostic['tags'] + nic_detail['tags'],
                    hostname=server['id'],
                )

    def _report_external_tags(self, server, aggregates):
        external_tags = ['host_type:server']
        hypervisor_hostname = server.get('OS-EXT-SRV-ATTR:hypervisor_hostname')
        external_tags.append(f"availability_zone:{server['OS-EXT-AZ:availability_zone']}")
        if hypervisor_hostname:
            for aggregate in aggregates:
                self.check.log.debug("aggregate: %s", aggregate)
                if hypervisor_hostname in aggregate['hosts']:
                    external_tags.append(f"aggregate:{aggregate['name']}")
                    availability_zone_tag = f"availability_zone:{aggregate['availability_zone']}"
                    if availability_zone_tag not in external_tags:
                        external_tags.append(availability_zone_tag)
        self.check.external_tags.append((server['id'], {'openstack': external_tags}))
