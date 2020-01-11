# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheck

from .metrics import INSTANCE_METRICS, MANAGER_METRICS


class ScyllaCheck(OpenMetricsBaseCheck):
    """
    Collect Scylla metrics from Prometheus endpoint
    """

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):

        for instance in instances:
            if 'instance_endpoint' in instance:
                endpoint = instance.get('instance_endpoint')

                instance.update(
                    {
                        'prometheus_url': endpoint,
                        'namespace': 'scylla',
                        'metrics': [INSTANCE_METRICS],
                        'prometheus_timeout': instance.get('timeout', 10),
                    }
                )

            if 'manager_endpoint' in instance:
                endpoint = instance.get('manager_endpoint')

                instance.update(
                    {
                        'prometheus_url': endpoint,
                        'namespace': 'scylla.manager',
                        'metrics': [MANAGER_METRICS],
                        'prometheus_timeout': instance.get('timeout', 10),
                    }
                )

        super(ScyllaCheck, self).__init__(name, init_config, instances=instances)
