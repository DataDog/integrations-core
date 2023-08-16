# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
from datadog_checks.base.checks.windows.perf_counters.counter import PerfObject
from datadog_checks.base.checks.windows.perf_counters.transform import NATIVE_TRANSFORMERS

from .metrics import METRICS_CONFIG


class ExchangeCheckV2(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'exchange'

    def get_default_config(self):
        return {'metrics': METRICS_CONFIG}

    def get_perf_object(self, connection, object_name, object_config, use_localized_counters, tags):
        if object_name == 'Processor':
            return CompatibilityPerfObject(
                self,
                connection,
                object_name,
                object_config,
                use_localized_counters,
                tags,
                {'% Processor Time': 'cpu_time', '% User Time': 'cpu_user', '% Privileged Time': 'cpu_privileged'},
            )
        elif object_name == 'MSExchange Active Manager':
            return CompatibilityPerfObject(
                self,
                connection,
                object_name,
                object_config,
                use_localized_counters,
                tags,
                {'Database Mounted': 'database_mounted'},
            )
        elif object_name == 'Web Service':
            return CompatibilityPerfObject(
                self,
                connection,
                object_name,
                object_config,
                use_localized_counters,
                tags,
                {
                    'Current Connections': 'current_connections_total',
                    'Connection Attempts/sec': 'connection_attempts',
                    'Other Request Methods/sec': 'other_attempts',
                },
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
        aggregate_names,
    ):
        super().__init__(check, connection, object_name, object_config, use_localized_counters, tags)

        self._aggregate_names = aggregate_names

    def _configure_counters(self):
        super()._configure_counters()

        for counter in self.counters:
            if counter.name not in self._aggregate_names:
                continue

            counter.aggregate_transformer = NATIVE_TRANSFORMERS[counter.metric_type](
                self.check, f'{self.metric_prefix}.{self._aggregate_names[counter.name]}', {}
            )
