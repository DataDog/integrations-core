# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.exchange_server import ExchangeCheck
from datadog_checks.exchange_server.metrics import METRICS_CONFIG

from .common import PERFORMANCE_OBJECTS

pytestmark = [requires_py3]


def test(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects(PERFORMANCE_OBJECTS)
    check = ExchangeCheck('exchange_server', {}, [{'host': dd_default_hostname}])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    global_tags = ['server:{}'.format(dd_default_hostname)]
    aggregator.assert_service_check('exchange.windows.perf.health', ServiceCheck.OK, count=1, tags=global_tags)

    for object_name, (instances, _) in PERFORMANCE_OBJECTS.items():
        config = METRICS_CONFIG[object_name]
        counters = config['counters'][0]

        for data in counters.values():
            aggregate_only = False
            if isinstance(data, str):
                metric = 'exchange.{}.{}'.format(config['name'], data)
            else:
                metric = 'exchange.{}.{}'.format(config['name'], data['name'])
                if 'aggregate' in data:
                    aggregate_only = data['aggregate'] == 'only'
                    if aggregate_only:
                        aggregator.assert_metric(
                            'exchange.{}.{}'.format(config['name'], data['name']),
                            metric_type=aggregator.GAUGE,
                            tags=global_tags,
                        )
                    else:
                        aggregator.assert_metric(
                            'exchange.{}.current_connections_total'.format(config['name']), tags=global_tags
                        )

            if not aggregate_only:
                for instance in instances:
                    if instance is None:
                        tags = global_tags
                    else:
                        if '_Total' in instance:
                            continue

                        tags = ['instance:{}'.format(instance)]
                        tags.extend(global_tags)

                    aggregator.assert_metric(metric, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
