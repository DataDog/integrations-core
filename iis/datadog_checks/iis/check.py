# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
from datadog_checks.base.checks.windows.perf_counters.counter import PerfObject
from datadog_checks.base.constants import ServiceCheck

from .metrics import METRICS_CONFIG


class IISCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'iis'

    def get_default_config(self):
        metrics_config = {}
        for object_name, config in METRICS_CONFIG.items():
            new_config = config.copy()

            include = []
            if object_name == 'APP_POOL_WAS':
                new_config['tag_name'] = 'app_pool'
                include.extend(self.instance.get('app_pools', []))
            elif object_name == 'Web Service':
                new_config['tag_name'] = 'site'
                include.extend(self.instance.get('sites', []))

            if include:
                new_config['include'] = [f'^{instance}$' for instance in include]

            metrics_config[object_name] = new_config

        return {'server_tag': 'iis_host', 'metrics': metrics_config}

    def get_perf_object(self, connection, object_name, object_config, use_localized_counters, tags):
        if object_name == 'APP_POOL_WAS':
            return CompatibilityPerfObject(
                self,
                connection,
                object_name,
                object_config,
                use_localized_counters,
                tags,
                'Current Application Pool Uptime',
                'app_pool',
                self.instance.get('app_pools', []),
            )
        elif object_name == 'Web Service':
            return CompatibilityPerfObject(
                self,
                connection,
                object_name,
                object_config,
                use_localized_counters,
                tags,
                'Service Uptime',
                'site',
                self.instance.get('sites', []),
            )
        else:
            return super().get_perf_object(connection, object_name, object_config, use_localized_counters, tags)


class CompatibilityPerfObject(PerfObject):
    def __init__(
        self,
        check,
        connection,
        object_name,
        object_config,
        use_localized_counters,
        tags,
        uptime_counter,
        instance_type,
        instances_included,
    ):
        super().__init__(check, connection, object_name, object_config, use_localized_counters, tags)

        self.uptime_counter = uptime_counter
        self.instance_type = instance_type
        self.instance_service_check_name = f'{self.instance_type}_up'
        self.instances_included = set(instances_included)

        # Resets during refreshes
        self.instances_unseen = set()

    def refresh(self):
        self.instances_unseen.clear()
        self.instances_unseen.update(self.instances_included)

        for instance in sorted(self.instances_unseen):
            self.logger.debug('Expecting %ss: %s', self.instance_type, instance)

        super().refresh()

        for instance in sorted(self.instances_unseen):
            tags = [f'{self.instance_type}:{instance}']
            tags.extend(self.tags)
            self.logger.warning('Did not get any data for expected %s: %s', self.instance_type, instance)
            self.check.service_check(self.instance_service_check_name, ServiceCheck.CRITICAL, tags=tags)

    def _instance_excluded(self, instance):
        self.instances_unseen.discard(instance)
        return super()._instance_excluded(instance)

    def get_custom_transformers(self):
        return {self.uptime_counter: self.__get_uptime_transformer}

    def __get_uptime_transformer(self, check, metric_name, modifiers):
        gauge_method = check.gauge
        service_check_method = check.service_check

        def submit_uptime(value, tags=None):
            gauge_method(metric_name, value, tags=tags)
            service_check_method(
                self.instance_service_check_name, ServiceCheck.CRITICAL if value == 0 else ServiceCheck.OK, tags=tags
            )

        del check
        del modifiers
        return submit_uptime
