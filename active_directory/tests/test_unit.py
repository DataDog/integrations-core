# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.active_directory import ActiveDirectoryCheck
from datadog_checks.active_directory.metrics import DEFAULT_COUNTERS
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics

from .common import PERFORMANCE_OBJECTS

pytestmark = [requires_py3]


def test(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = ActiveDirectoryCheck('active_directory', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('active_directory.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    for counter_data in DEFAULT_COUNTERS:
        aggregator.assert_metric(counter_data[3], 9000, count=1, tags=global_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
