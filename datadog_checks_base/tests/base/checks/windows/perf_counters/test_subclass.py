# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, SERVER

try:
    from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheck
    from datadog_checks.base.checks.windows.perf_counters.counter import PerfObject
# non-Windows systems
except Exception:
    PerfCountersBaseCheck = object
    PerfObject = object

pytestmark = [requires_py3, requires_windows]


class CustomCheck(PerfCountersBaseCheck):
    __NAMESPACE__ = 'test'

    def get_perf_object(self, connection, object_name, object_config, use_localized_counters, tags):
        if object_name == 'Foo':
            return CustomPerfObject(self, connection, object_name, object_config, use_localized_counters, tags)
        else:
            return super().get_perf_object(connection, object_name, object_config, use_localized_counters, tags)


class CustomPerfObject(PerfObject):
    def get_custom_transformers(self):
        return {'Bar': self.__get_transformer}

    def __get_transformer(self, check, metric_name, modifiers):
        service_check_method = check.service_check
        down = modifiers['down']

        def service_check(value, tags=None):
            service_check_method(metric_name, ServiceCheck.CRITICAL if value == down else ServiceCheck.OK, tags=tags)

        del check
        del modifiers
        return service_check


def test(aggregator, dd_run_check, mock_performance_objects):
    target = 9000
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [target]})})
    instance = {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'down': target}}]}}}
    check = CustomCheck('test', {}, [instance])
    check.hostname = SERVER
    dd_run_check(check)

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_service_check('test.foo.bar', ServiceCheck.CRITICAL, tags=tags)

    aggregator.assert_all_metrics_covered()
