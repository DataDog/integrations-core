# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.dotnetclr import DotnetclrCheck
from datadog_checks.dotnetclr.metrics import METRICS_CONFIG

from .common import PERFORMANCE_OBJECTS

pytestmark = [requires_py3]


def test(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = DotnetclrCheck('dotnetclr', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('dotnetclr.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    for object_name, (instances, _) in PERFORMANCE_OBJECTS.items():
        config = METRICS_CONFIG[object_name]
        counters = config['counters'][0]

        for data in counters.values():
            if isinstance(data, str):
                metric = 'dotnetclr.{}.{}'.format(config['name'], data)
            else:
                metric = 'dotnetclr.{}'.format(data.get('metric_name'))

            for instance in instances:
                if instance is None:
                    tags = global_tags
                else:
                    tags = ['instance:{}'.format(instance)]
                    tags.extend(global_tags)

                aggregator.assert_metric(metric, 9000, count=1, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
