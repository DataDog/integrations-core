# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
from datadog_checks.base.checks.windows.perf_counters.counter import PerfObject
from datadog_checks.base.constants import ServiceCheck

from .metrics import METRICS_CONFIG
from .service_check import app_pool_service_check, site_service_check


class IISCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'iis'

    def get_default_config(self):
        metrics_config = {}
        for object_name, config in METRICS_CONFIG.items():
            new_config = config.copy()

            instance_config = []
            include = []
            exclude = []
            include_fast = []

            if object_name == 'APP_POOL_WAS':
                new_config['tag_name'] = 'app_pool'
                instance_config = self.instance.get('app_pools', [])
            elif object_name == 'Web Service':
                new_config['tag_name'] = 'site'
                instance_config = self.instance.get('sites', [])

            if isinstance(instance_config, list):
                # literal instance which we can use for wildcard filtering
                # app_pool or sites instances a full instance name. IIS cannot create pool or site
                # with wildcard instance
                include_fast = instance_config
            elif isinstance(instance_config, dict):
                include.extend(instance_config.get('include', []))
                exclude.extend(instance_config.get('exclude', []))
                include_fast.extend(instance_config.get('include_fast', []))

            if include:
                new_config['include'] = include
            if exclude:
                new_config['exclude'] = exclude
            if include_fast:
                new_config['include_fast'] = include_fast

            # As we have discovered in 7.43 win32pdh function (win32pdh.GetFormattedCounterArray)
            # has a memory leak. Until it is fixed we are suppressing this single use of the
            # optimization controlled by "duplicate_instances_exist" flag because
            # win32pdh.GetFormattedCounterArray is 5-10 times faster than its python re-implementation
            # (GetFormattedCounterArray). For more details see get_counter_values() comments
            #
            # UNCOMMENT BELOW WHEN win32pdh.GetFormattedCounterArray IS FIXED
            # # No duplicate Sites or Pools can be created
            # new_config['duplicate_instances_exist'] = False

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
                'Current Application Pool State',
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
        service_check_counter,
        instance_type,
        instances_included,
    ):
        super().__init__(check, connection, object_name, object_config, use_localized_counters, tags)

        self.service_check_counter = service_check_counter
        self.instance_type = instance_type
        self.instance_service_check_name = f'{self.instance_type}_up'
        if isinstance(instances_included, dict):
            self.instances_included = set(instances_included.get('include', []))
        else:
            self.instances_included = set(instances_included)

        # Resets during refreshes
        self.instances_unseen = set()

    def collect(self):
        self.instances_unseen.clear()
        self.instances_unseen.update(self.instances_included)

        for instance in sorted(self.instances_unseen):
            self.logger.debug('Expecting %s: %s', self.instance_type, instance)

        super().collect()

        for instance in sorted(self.instances_unseen):
            tags = [f'{self.instance_type}:{instance}']
            tags.extend(self.tags)
            self.logger.warning('Did not get any data for expected %s: %s', self.instance_type, instance)
            self.check.service_check(self.instance_service_check_name, ServiceCheck.CRITICAL, tags=tags)

    def _instance_excluded(self, instance):
        self.instances_unseen.discard(instance)
        return super()._instance_excluded(instance)

    def get_custom_transformers(self):
        return {self.service_check_counter: self.__get_service_check_transformer}

    def __get_service_check_transformer(self, check, metric_name, modifiers):
        gauge_method = check.gauge
        service_check_method = check.service_check

        def submit_uptime(value, tags=None):
            # Submit the counter's value as a metric
            gauge_method(metric_name, value, tags=tags)

            # Submit a service check
            if self.instance_type == 'site':
                status = site_service_check(value)
            elif self.instance_type == 'app_pool':
                status = app_pool_service_check(value)
            service_check_method(self.instance_service_check_name, status, tags=tags)

        del check
        del modifiers
        return submit_uptime
