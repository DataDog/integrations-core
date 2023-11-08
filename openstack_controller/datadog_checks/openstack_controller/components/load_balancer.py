# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.openstack_controller.components.component import Component
from datadog_checks.openstack_controller.config import normalize_discover_config_include
from datadog_checks.openstack_controller.metrics import (
    OCTAVIA_AMPHORA_COUNT,
    OCTAVIA_AMPHORA_METRICS,
    OCTAVIA_AMPHORA_METRICS_PREFIX,
    OCTAVIA_AMPHORA_STATS_METRICS,
    OCTAVIA_AMPHORA_STATS_METRICS_PREFIX,
    OCTAVIA_AMPHORA_STATS_TAGS,
    OCTAVIA_AMPHORA_TAGS,
    OCTAVIA_HEALTHMONITOR_COUNT,
    OCTAVIA_HEALTHMONITOR_METRICS,
    OCTAVIA_HEALTHMONITOR_METRICS_PREFIX,
    OCTAVIA_HEALTHMONITOR_TAGS,
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
    OCTAVIA_POOL_COUNT,
    OCTAVIA_POOL_MEMBERS_COUNT,
    OCTAVIA_POOL_MEMBERS_METRICS,
    OCTAVIA_POOL_MEMBERS_METRICS_PREFIX,
    OCTAVIA_POOL_MEMBERS_TAGS,
    OCTAVIA_POOL_METRICS,
    OCTAVIA_POOL_METRICS_PREFIX,
    OCTAVIA_POOL_TAGS,
    OCTAVIA_QUOTA_COUNT,
    OCTAVIA_QUOTA_METRICS,
    OCTAVIA_QUOTA_METRICS_PREFIX,
    OCTAVIA_QUOTA_TAGS,
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
    def _report_loadbalancers(self, project_id, tags, config):
        report_loadbalancers = True
        config_loadbalancers = config.get('loadbalancers', {})
        if isinstance(config_loadbalancers, bool):
            report_loadbalancers = config_loadbalancers
            config_loadbalancers = {}
        if report_loadbalancers:
            loadbalancers_discovery = None
            if config_loadbalancers:
                config_loadbalancers_include = normalize_discover_config_include(config_loadbalancers, ["name"])
                if config_loadbalancers_include:
                    loadbalancers_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_loadbalancers(project_id),
                        limit=config_loadbalancers.get('limit'),
                        include=config_loadbalancers_include,
                        exclude=config_loadbalancers.get('exclude'),
                        interval=config_loadbalancers.get('interval'),
                        key=lambda loadbalancer: loadbalancer.get('name'),
                    )
            if loadbalancers_discovery:
                discovered_loadbalancers = list(loadbalancers_discovery.get_items())
            else:
                discovered_loadbalancers = [
                    (None, loadbalancer.get('name'), loadbalancer, None)
                    for loadbalancer in self.check.api.get_load_balancer_loadbalancers(project_id)
                ]
            for _pattern, _item_name, item, item_config in discovered_loadbalancers:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
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
                report_stats = item_config.get('stats', True) if item_config else True
                if report_stats:
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

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_listeners(self, project_id, tags, config):
        report_listeners = True
        config_listeners = config.get('listeners', {})
        if isinstance(config_listeners, bool):
            report_listeners = config_listeners
            config_listeners = {}
        if report_listeners:
            listeners_discovery = None
            if config_listeners:
                config_listeners_include = normalize_discover_config_include(config_listeners, ["name"])
                if config_listeners_include:
                    listeners_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_listeners(project_id),
                        limit=config_listeners.get('limit'),
                        include=config_listeners_include,
                        exclude=config_listeners.get('exclude'),
                        interval=config_listeners.get('interval'),
                        key=lambda listener: listener.get('name'),
                    )
            if listeners_discovery:
                discovered_listeners = list(listeners_discovery.get_items())
            else:
                discovered_listeners = [
                    (None, listener.get('name'), listener, None)
                    for listener in self.check.api.get_load_balancer_listeners(project_id)
                ]
            for _pattern, _item_name, item, item_config in discovered_listeners:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
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
                report_stats = item_config.get('stats', True) if item_config else True
                if report_stats:
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

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_pools(self, project_id, tags, config):
        report_pools = True
        config_pools = config.get('pools', {})
        if isinstance(config_pools, bool):
            report_pools = config_pools
            config_pools = {}
        if report_pools:
            pools_discovery = None
            if config_pools:
                config_pools_include = normalize_discover_config_include(config_pools, ["name"])
                if config_pools_include:
                    pools_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_pools(project_id),
                        limit=config_pools.get('limit'),
                        include=config_pools_include,
                        exclude=config_pools.get('exclude'),
                        interval=config_pools.get('interval'),
                        key=lambda pool: pool.get('name'),
                    )
            if pools_discovery:
                discovered_pools = list(pools_discovery.get_items())
            else:
                discovered_pools = [
                    (None, pool.get('name'), pool, None) for pool in self.check.api.get_load_balancer_pools(project_id)
                ]
            for _pattern, _item_name, item, item_config in discovered_pools:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                pool = get_metrics_and_tags(
                    item,
                    tags=OCTAVIA_POOL_TAGS,
                    prefix=OCTAVIA_POOL_METRICS_PREFIX,
                    metrics=OCTAVIA_POOL_METRICS,
                )
                self.check.log.debug("pool: %s", pool)
                self.check.gauge(OCTAVIA_POOL_COUNT, 1, tags=tags + pool['tags'])
                for metric, value in pool['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + pool['tags'])
                report_members = item_config.get('members', True) if item_config else True
                if report_members:
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
    def _report_healthmonitors(self, project_id, tags, config):
        report_healthmonitors = True
        config_healthmonitors = config.get('healthmonitors', {})
        if isinstance(config_healthmonitors, bool):
            report_healthmonitors = config_healthmonitors
            config_healthmonitors = {}
        if report_healthmonitors:
            healthmonitors_discovery = None
            if config_healthmonitors:
                config_healthmonitors_include = normalize_discover_config_include(config_healthmonitors, ["name"])
                if config_healthmonitors_include:
                    healthmonitors_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_healthmonitors(project_id),
                        limit=config_healthmonitors.get('limit'),
                        include=config_healthmonitors_include,
                        exclude=config_healthmonitors.get('exclude'),
                        interval=config_healthmonitors.get('interval'),
                        key=lambda healthmonitor: healthmonitor.get('name'),
                    )
            if healthmonitors_discovery:
                discovered_healthmonitors = list(healthmonitors_discovery.get_items())
            else:
                discovered_healthmonitors = [
                    (None, healthmonitor.get('name'), healthmonitor, None)
                    for healthmonitor in self.check.api.get_load_balancer_healthmonitors(project_id)
                ]
            for _pattern, _item_name, item, item_config in discovered_healthmonitors:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                healthmonitor = get_metrics_and_tags(
                    item,
                    tags=OCTAVIA_HEALTHMONITOR_TAGS,
                    prefix=OCTAVIA_HEALTHMONITOR_METRICS_PREFIX,
                    metrics=OCTAVIA_HEALTHMONITOR_METRICS,
                )
                self.check.log.debug("healthmonitor: %s", healthmonitor)
                self.check.gauge(OCTAVIA_HEALTHMONITOR_COUNT, 1, tags=tags + healthmonitor['tags'])
                for metric, value in healthmonitor['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + healthmonitor['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_quotas(self, project_id, tags, config):
        report_quotas = True
        config_quotas = config.get('quotas', {})
        if isinstance(config_quotas, bool):
            report_quotas = config_quotas
            config_quotas = {}
        if report_quotas:
            quotas_discovery = None
            if config_quotas:
                config_quotas_include = normalize_discover_config_include(config_quotas, ["name"])
                if config_quotas_include:
                    quotas_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_quotas(project_id),
                        limit=config_quotas.get('limit'),
                        include=config_quotas_include,
                        exclude=config_quotas.get('exclude'),
                        interval=config_quotas.get('interval'),
                        key=lambda quota: quota.get('name'),
                    )
            if quotas_discovery:
                discovered_quotas = list(quotas_discovery.get_items())
            else:
                discovered_quotas = [
                    (None, quota.get('name'), quota, None)
                    for quota in self.check.api.get_load_balancer_quotas(project_id)
                ]
            for _pattern, _item_name, item, item_config in discovered_quotas:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                quota = get_metrics_and_tags(
                    item,
                    tags=OCTAVIA_QUOTA_TAGS,
                    prefix=OCTAVIA_QUOTA_METRICS_PREFIX,
                    metrics=OCTAVIA_QUOTA_METRICS,
                    lambda_value=lambda key, value, item=item: -1 if value is None else value,
                )
                self.check.log.debug("quota: %s", quota)
                self.check.gauge(OCTAVIA_QUOTA_COUNT, 1, tags=tags + quota['tags'])
                for metric, value in quota['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + quota['tags'])

    @Component.register_project_metrics(ID)
    @Component.http_error()
    def _report_amphorae(self, project_id, tags, config):
        report_amphorae = True
        config_amphorae = config.get('amphorae', {})
        if isinstance(config_amphorae, bool):
            report_amphorae = config_amphorae
            config_amphorae = {}
        if report_amphorae:
            amphorae_discovery = None
            if config_amphorae:
                config_amphorae_include = normalize_discover_config_include(config_amphorae, ["id"])
                if config_amphorae_include:
                    amphorae_discovery = Discovery(
                        lambda: self.check.api.get_load_balancer_amphorae(project_id),
                        limit=config_amphorae.get('limit'),
                        include=config_amphorae_include,
                        exclude=config_amphorae.get('exclude'),
                        interval=config_amphorae.get('interval'),
                        key=lambda amphora: amphora.get('id'),
                    )
            if amphorae_discovery:
                discovered_amphorae = list(amphorae_discovery.get_items())
            else:
                discovered_amphorae = [
                    (None, amphora.get('id'), amphora, None)
                    for amphora in self.check.api.get_load_balancer_amphorae(project_id)
                ]
            for _pattern, _item_id, item, item_config in discovered_amphorae:
                self.check.log.debug("item: %s", item)
                self.check.log.debug("item_config: %s", item_config)
                amphora = get_metrics_and_tags(
                    item,
                    tags=OCTAVIA_AMPHORA_TAGS,
                    prefix=OCTAVIA_AMPHORA_METRICS_PREFIX,
                    metrics=OCTAVIA_AMPHORA_METRICS,
                    lambda_value=lambda key, value, item=item: -1 if value is None else value,
                )
                self.check.log.debug("amphora: %s", amphora)
                self.check.gauge(OCTAVIA_AMPHORA_COUNT, 1, tags=tags + amphora['tags'])
                for metric, value in amphora['metrics'].items():
                    self.check.gauge(metric, value, tags=tags + amphora['tags'])
                report_stats = item_config.get('stats', True) if item_config else True
                if report_stats:
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
